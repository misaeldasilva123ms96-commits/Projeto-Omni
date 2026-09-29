"""Encrypted credential storage — AES-256-GCM authenticated encryption for provider secrets."""

from __future__ import annotations

import json
import logging
import math
import os
import time
import tempfile
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

__all__ = [
    "CredentialStore",
    "CredentialStoreError",
    "EncryptionKeyError",
    "CredentialNotFoundError",
    "TamperDetectedError",
    "ProviderMismatchError",
    "StoredCredential",
    "CredentialMetadata",
]

logger = logging.getLogger(__name__)

KEY_ENV_VAR = "OMNI_CREDENTIAL_STORE_KEY"
STORE_PATH_ENV_VAR = "OMNI_CREDENTIAL_STORE_PATH"
DEFAULT_STORE_PATH = "credentials.enc"
AES256_KEY_LENGTH = 32
NONCE_LENGTH = 12


class CredentialStoreError(Exception):
    """Base exception for credential store operations."""


class EncryptionKeyError(CredentialStoreError):
    """Raised when the encryption key is missing, invalid, or wrong length."""


class CredentialNotFoundError(CredentialStoreError):
    """Raised when a requested credential does not exist."""


class TamperDetectedError(CredentialStoreError):
    """Raised when ciphertext or authentication tag validation fails."""


class ProviderMismatchError(CredentialStoreError):
    """Raised when a credential's provider does not match the expected provider."""


@dataclass
class StoredCredential:
    """Internal representation of a stored credential with encrypted secret."""

    credential_id: str
    user_id: str
    provider_id: str
    encrypted_secret: bytes
    nonce: bytes
    created_at: float
    updated_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "credential_id": self.credential_id,
            "user_id": self.user_id,
            "provider_id": self.provider_id,
            "encrypted_secret": self.encrypted_secret.hex(),
            "nonce": self.nonce.hex(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredCredential:
        try:
            if not isinstance(data, dict):
                raise ValueError
            for field in ("credential_id", "user_id", "provider_id"):
                if not isinstance(data[field], str) or not data[field]:
                    raise ValueError
            for field in ("created_at", "updated_at"):
                value = data[field]
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError
            for field in ("encrypted_secret", "nonce"):
                value = data[field]
                if not isinstance(value, str) or not value or len(value) % 2:
                    raise ValueError
                if any(char not in "0123456789abcdefABCDEF" for char in value):
                    raise ValueError
            nonce = bytes.fromhex(data["nonce"])
            if len(nonce) != NONCE_LENGTH:
                raise ValueError
            return cls(
                credential_id=data["credential_id"],
                user_id=data["user_id"],
                provider_id=data["provider_id"],
                encrypted_secret=bytes.fromhex(data["encrypted_secret"]),
                nonce=nonce,
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        except (KeyError, ValueError, TypeError, OverflowError):
            raise CredentialStoreError("Invalid credential store record") from None

    def to_metadata(self) -> CredentialMetadata:
        return CredentialMetadata(
            credential_id=self.credential_id,
            user_id=self.user_id,
            provider_id=self.provider_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass
class CredentialMetadata:
    """Public metadata for a stored credential — never contains secret values."""

    credential_id: str
    user_id: str
    provider_id: str
    created_at: float
    updated_at: float


class CredentialStore:
    """
    Provider-agnostic encrypted credential storage using AES-256-GCM.

    Architecture:
    - Encryption logic is isolated in _encrypt / _decrypt methods.
    - Persistence logic is isolated in _load_store / _save_store methods.
    - Key management is isolated in _load_key_from_env / _validate_key.
    - Public API: save, get, update, delete, list metadata.
    """

    def __init__(
        self,
        store_path: str | Path | None = None,
        encryption_key: bytes | None = None,
    ) -> None:
        if encryption_key is not None:
            self._validate_key(encryption_key)
            self._key = encryption_key
        else:
            self._key = self._load_key_from_env()

        self._aesgcm = AESGCM(self._key)

        path_str = os.environ.get(STORE_PATH_ENV_VAR)
        self._store_path = Path(store_path or path_str or DEFAULT_STORE_PATH)

        self._store: dict[str, StoredCredential] = {}
        self._load_store()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_credential(
        self,
        user_id: str,
        provider_id: str,
        secret: str,
    ) -> StoredCredential:
        if (
            not isinstance(user_id, str)
            or not user_id
            or not isinstance(provider_id, str)
            or not provider_id
        ):
            raise CredentialStoreError("Invalid credential identity")
        for existing in self._store.values():
            if (existing.user_id, existing.provider_id) == (user_id, provider_id):
                return self.update_credential(existing.credential_id, secret)
        credential_id = str(uuid.uuid4())
        now = time.time()
        nonce, encrypted_secret = self._encrypt(
            secret.encode("utf-8"), credential_id, user_id, provider_id
        )

        credential = StoredCredential(
            credential_id=credential_id,
            user_id=user_id,
            provider_id=provider_id,
            encrypted_secret=encrypted_secret,
            nonce=nonce,
            created_at=now,
            updated_at=now,
        )

        updated = {**self._store, credential_id: credential}
        self._save_store(updated)
        self._store = updated
        logger.info(
            "Saved credential %s for provider %s (user %s)",
            credential_id,
            provider_id,
            _redact_user(user_id),
        )
        return credential

    def get_credential(
        self,
        credential_id: str,
        decrypt: bool = False,
    ) -> StoredCredential | str:
        credential = self._store.get(credential_id)
        if credential is None:
            raise CredentialNotFoundError(f"Credential not found: {credential_id}")

        if decrypt:
            plaintext = self._decrypt(credential)
            return plaintext.decode("utf-8")

        return credential

    def update_credential(
        self,
        credential_id: str,
        secret: str,
    ) -> StoredCredential:
        credential = self._store.get(credential_id)
        if credential is None:
            raise CredentialNotFoundError(f"Credential not found: {credential_id}")

        now = time.time()
        nonce, encrypted_secret = self._encrypt(
            secret.encode("utf-8"), credential_id, credential.user_id, credential.provider_id
        )
        credential = replace(
            credential,
            nonce=nonce,
            encrypted_secret=encrypted_secret,
            updated_at=max(now, credential.updated_at),
        )
        updated = {**self._store, credential_id: credential}
        self._save_store(updated)
        self._store = updated
        logger.info("Updated credential %s", credential_id)
        return credential

    def delete_credential(self, credential_id: str) -> None:
        if credential_id not in self._store:
            raise CredentialNotFoundError(f"Credential not found: {credential_id}")

        updated = dict(self._store)
        del updated[credential_id]
        self._save_store(updated)
        self._store = updated
        logger.info("Deleted credential %s", credential_id)

    def list_credential_metadata(
        self,
        user_id: str | None = None,
        provider_id: str | None = None,
    ) -> list[CredentialMetadata]:
        results: list[CredentialMetadata] = []
        for credential in self._store.values():
            if user_id is not None and credential.user_id != user_id:
                continue
            if provider_id is not None and credential.provider_id != provider_id:
                continue
            results.append(credential.to_metadata())
        return results

    def get_decrypted_secret(self, credential_id: str) -> str:
        credential = self._store.get(credential_id)
        if credential is None:
            raise CredentialNotFoundError(f"Credential not found: {credential_id}")

        plaintext = self._decrypt(credential)
        return plaintext.decode("utf-8")

    def get_credential_by_provider(
        self,
        user_id: str,
        provider_id: str,
        decrypt: bool = False,
    ) -> StoredCredential | str:
        for credential in self._store.values():
            if credential.user_id == user_id and credential.provider_id == provider_id:
                if decrypt:
                    return self.get_decrypted_secret(credential.credential_id)
                return credential
        raise CredentialNotFoundError(
            f"No credential found for user {_redact_user(user_id)} provider {provider_id}"
        )

    def verify_provider_mismatch(
        self,
        credential_id: str,
        expected_provider_id: str,
    ) -> None:
        credential = self._store.get(credential_id)
        if credential is None:
            raise CredentialNotFoundError(f"Credential not found: {credential_id}")
        if credential.provider_id != expected_provider_id:
            raise ProviderMismatchError(
                f"Credential {credential_id} is for provider "
                f"'{credential.provider_id}', not '{expected_provider_id}'"
            )

    # ------------------------------------------------------------------
    # Encryption — isolated layer
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_key(key: bytes) -> None:
        if not isinstance(key, bytes):
            raise EncryptionKeyError("Encryption key must be bytes")
        if len(key) != AES256_KEY_LENGTH:
            raise EncryptionKeyError(
                f"Encryption key must be {AES256_KEY_LENGTH} bytes (got {len(key)})"
            )

    @staticmethod
    def _load_key_from_env() -> bytes:
        key_str = os.environ.get(KEY_ENV_VAR)
        if not key_str:
            raise EncryptionKeyError(
                f"Encryption key not found. Set {KEY_ENV_VAR} environment variable "
                f"with a {AES256_KEY_LENGTH * 8}-bit hex-encoded key."
            )

        try:
            key = bytes.fromhex(key_str)
        except ValueError as exc:
            raise EncryptionKeyError(
                f"Encryption key must be hex-encoded " f"({AES256_KEY_LENGTH * 2} hex chars)."
            ) from exc

        if len(key) != AES256_KEY_LENGTH:
            raise EncryptionKeyError(
                f"Encryption key must decode to {AES256_KEY_LENGTH} bytes "
                f"(got {len(key)}). The hex string must be "
                f"{AES256_KEY_LENGTH * 2} characters."
            )

        return key

    def _encrypt(
        self, plaintext: bytes, credential_id: str, user_id: str, provider_id: str
    ) -> tuple[bytes, bytes]:
        nonce = os.urandom(NONCE_LENGTH)
        aad = _credential_aad(credential_id, user_id, provider_id)
        return nonce, self._aesgcm.encrypt(nonce, plaintext, aad)

    def _decrypt(self, credential: StoredCredential, *, legacy: bool = False) -> bytes:
        aad = (
            None
            if legacy
            else _credential_aad(
                credential.credential_id, credential.user_id, credential.provider_id
            )
        )
        try:
            plaintext = self._aesgcm.decrypt(credential.nonce, credential.encrypted_secret, aad)
            plaintext.decode("utf-8")
            return plaintext
        except (ValueError, UnicodeError, InvalidTag):
            raise TamperDetectedError("Credential authentication failed") from None

    # Persistence is transactional: publish in-memory state only after replacement.
    def _load_store(self) -> None:
        if not self._store_path.exists():
            self._store = {}
            return
        try:
            data = json.loads(
                self._store_path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_json_object
            )
        except (ValueError, UnicodeError, OSError):
            raise CredentialStoreError("Failed to load credential store") from None
        if not isinstance(data, dict) or type(data.get("version")) is not int:
            raise CredentialStoreError("Invalid credential store format")
        version = data["version"]
        if version not in (1, 2):
            raise CredentialStoreError("Unsupported credential store version")
        if not isinstance(data.get("credentials"), list):
            raise CredentialStoreError("Invalid credential store format")
        loaded = {}
        identities = set()
        for item in data["credentials"]:
            credential = StoredCredential.from_dict(item)
            identity = (credential.user_id, credential.provider_id)
            if credential.credential_id in loaded or identity in identities:
                raise CredentialStoreError("Duplicate credential identity")
            loaded[credential.credential_id] = credential
            identities.add(identity)
        if version == 1:
            # Authenticate EVERY legacy record before generating or writing v2.
            plaintexts = {cid: self._decrypt(c, legacy=True) for cid, c in loaded.items()}
            migrated = {}
            for cid, credential in loaded.items():
                nonce, ciphertext = self._encrypt(
                    plaintexts[cid], cid, credential.user_id, credential.provider_id
                )
                migrated[cid] = replace(credential, nonce=nonce, encrypted_secret=ciphertext)
            self._save_store(migrated)
            loaded = migrated
        elif os.name == "posix":
            try:
                self._store_path.chmod(0o600)
            except OSError:
                raise CredentialStoreError("Unable to protect credential store") from None
        self._store = loaded
        logger.info("Loaded credential store with %d credentials", len(self._store))

    def _save_store(self, credentials: dict[str, StoredCredential] | None = None) -> None:
        records = self._store if credentials is None else credentials
        data = {"version": 2, "credentials": [c.to_dict() for c in records.values()]}
        tmp_path = None
        try:
            # mkstemp creates exclusively with 0600, in the destination filesystem.
            fd, name = tempfile.mkstemp(
                prefix=f".{self._store_path.name}.", suffix=".tmp", dir=self._store_path.parent
            )
            tmp_path = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                if os.name == "posix":
                    os.fchmod(stream.fileno(), 0o600)
                json.dump(data, stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_path, self._store_path)
        except (OSError, ValueError, TypeError):
            raise CredentialStoreError("Failed to save credential store") from None
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    raise CredentialStoreError(
                        "Unable to clean credential store temporary file"
                    ) from None
        if os.name == "posix":
            # Replacement already committed. Some filesystems cannot fsync directories;
            # do not report a rollback or leave memory stale after a successful replace.
            try:
                directory_fd = os.open(self._store_path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                logger.warning("Credential store directory sync unavailable")

    @property
    def store_path(self) -> Path:
        return self._store_path


def _redact_user(user_id: str) -> str:
    if len(user_id) <= 4:
        return "****"
    return user_id[:2] + "***" + user_id[-1:]


def _credential_aad(credential_id: str, user_id: str, provider_id: str) -> bytes:
    return json.dumps(
        {
            "domain": "omni-credential-store:v2",
            "credential_id": credential_id,
            "user_id": user_id,
            "provider_id": provider_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CredentialStoreError("Duplicate credential store field")
        result[key] = value
    return result
