"""Encrypted credential storage — AES-256-GCM authenticated encryption for provider secrets."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
        return cls(
            credential_id=data["credential_id"],
            user_id=data["user_id"],
            provider_id=data["provider_id"],
            encrypted_secret=bytes.fromhex(data["encrypted_secret"]),
            nonce=bytes.fromhex(data["nonce"]),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
        )

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
        credential_id = str(uuid.uuid4())
        now = time.time()
        nonce, encrypted_secret = self._encrypt(secret.encode("utf-8"))

        credential = StoredCredential(
            credential_id=credential_id,
            user_id=user_id,
            provider_id=provider_id,
            encrypted_secret=encrypted_secret,
            nonce=nonce,
            created_at=now,
            updated_at=now,
        )

        self._store[credential_id] = credential
        self._save_store()
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
            plaintext = self._decrypt(credential.nonce, credential.encrypted_secret)
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
        nonce, encrypted_secret = self._encrypt(secret.encode("utf-8"))

        credential.nonce = nonce
        credential.encrypted_secret = encrypted_secret
        credential.updated_at = now

        self._save_store()
        logger.info("Updated credential %s", credential_id)
        return credential

    def delete_credential(self, credential_id: str) -> None:
        if credential_id not in self._store:
            raise CredentialNotFoundError(f"Credential not found: {credential_id}")

        del self._store[credential_id]
        self._save_store()
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

        plaintext = self._decrypt(credential.nonce, credential.encrypted_secret)
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
                f"Encryption key must be hex-encoded "
                f"({AES256_KEY_LENGTH * 2} hex chars)."
            ) from exc

        if len(key) != AES256_KEY_LENGTH:
            raise EncryptionKeyError(
                f"Encryption key must decode to {AES256_KEY_LENGTH} bytes "
                f"(got {len(key)}). The hex string must be "
                f"{AES256_KEY_LENGTH * 2} characters."
            )

        return key

    def _encrypt(self, plaintext: bytes) -> tuple[bytes, bytes]:
        nonce = os.urandom(NONCE_LENGTH)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return nonce, ciphertext

    def _decrypt(self, nonce: bytes, ciphertext: bytes) -> bytes:
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise TamperDetectedError(
                "Decryption failed. The ciphertext or authentication tag "
                "may be corrupted."
            ) from exc

    # ------------------------------------------------------------------
    # Persistence — isolated layer
    # ------------------------------------------------------------------

    def _load_store(self) -> None:
        if not self._store_path.exists():
            self._store = {}
            return

        try:
            raw = self._store_path.read_bytes()
            data: dict[str, Any] = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            raise CredentialStoreError(f"Failed to load credential store: {exc}") from exc

        self._store = {}
        for item in data.get("credentials", []):
            credential = StoredCredential.from_dict(item)
            self._store[credential.credential_id] = credential

        logger.info("Loaded credential store with %d credentials", len(self._store))

    def _save_store(self) -> None:
        data = {
            "version": 1,
            "credentials": [c.to_dict() for c in self._store.values()],
        }
        tmp_path = self._store_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp_path.replace(self._store_path)
        except OSError as exc:
            raise CredentialStoreError(
                f"Failed to save credential store: {exc}"
            ) from exc
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    @property
    def store_path(self) -> Path:
        return self._store_path


def _redact_user(user_id: str) -> str:
    if len(user_id) <= 4:
        return "****"
    return user_id[:2] + "***" + user_id[-1:]
