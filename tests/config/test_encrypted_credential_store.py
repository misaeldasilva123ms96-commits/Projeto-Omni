"""Comprehensive tests for encrypted credential storage (P5D)."""

from __future__ import annotations

import json
import logging
import stat
import subprocess
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from config.encrypted_credential_store import (
    AES256_KEY_LENGTH,
    KEY_ENV_VAR,
    STORE_PATH_ENV_VAR,
    CredentialMetadata,
    CredentialNotFoundError,
    CredentialStore,
    CredentialStoreError,
    EncryptionKeyError,
    ProviderMismatchError,
    StoredCredential,
    TamperDetectedError,
)

VALID_KEY_HEX = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
VALID_KEY = bytes.fromhex(VALID_KEY_HEX)
TEST_USER = "user-abc-123"
TEST_PROVIDER = "openai"
TEST_SECRET = "sk-test-api-key-12345"


class CredentialStoreTest(unittest.TestCase):
    """Test suite for CredentialStore — encryption, persistence, validation."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp(prefix="omni_cred_test_")
        self._store_path = Path(self._tmpdir) / "test_credentials.enc"
        self._saved_env = os.environ.get(KEY_ENV_VAR)
        os.environ[KEY_ENV_VAR] = VALID_KEY_HEX

    def tearDown(self) -> None:
        os.environ.pop(KEY_ENV_VAR, None)
        os.environ.pop(STORE_PATH_ENV_VAR, None)
        if self._saved_env is not None:
            os.environ[KEY_ENV_VAR] = self._saved_env
        for child in Path(self._tmpdir).iterdir():
            child.unlink(missing_ok=True)
        Path(self._tmpdir).rmdir()

    def _make_store(self) -> CredentialStore:
        return CredentialStore(store_path=str(self._store_path))

    # ------------------------------------------------------------------
    # Encrypt / Decrypt success
    # ------------------------------------------------------------------

    def test_save_and_get_decrypted(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        self.assertEqual(saved.user_id, TEST_USER)
        self.assertEqual(saved.provider_id, TEST_PROVIDER)

        decrypted = store.get_decrypted_secret(saved.credential_id)
        self.assertEqual(decrypted, TEST_SECRET)

    def test_encrypted_differs_from_plaintext(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        self.assertNotEqual(saved.encrypted_secret, TEST_SECRET.encode("utf-8"))
        self.assertNotEqual(saved.encrypted_secret.hex(), TEST_SECRET.encode("utf-8").hex())

    def test_nonce_unique_per_credential(self) -> None:
        store = self._make_store()
        c1 = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        c2 = store.save_credential(TEST_USER, "anthropic", "sk-ant-test")
        self.assertNotEqual(c1.nonce, c2.nonce)

    def test_get_credential_without_decrypt(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        result = store.get_credential(saved.credential_id, decrypt=False)
        assert isinstance(result, StoredCredential)
        self.assertEqual(result.credential_id, saved.credential_id)
        self.assertEqual(result.encrypted_secret, saved.encrypted_secret)

    def test_get_credential_with_decrypt(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        result = store.get_credential(saved.credential_id, decrypt=True)
        assert isinstance(result, str)
        self.assertEqual(result, TEST_SECRET)

    # ------------------------------------------------------------------
    # Wrong key failure
    # ------------------------------------------------------------------

    def test_wrong_key_fails_decryption(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        other_hex = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        other_key = bytes.fromhex(other_hex)
        other_store = CredentialStore(store_path=str(self._store_path), encryption_key=other_key)
        with self.assertRaises(TamperDetectedError):
            other_store.get_decrypted_secret(saved.credential_id)

    def test_invalid_key_length_on_construction(self) -> None:
        with self.assertRaises(EncryptionKeyError):
            CredentialStore(
                store_path=str(self._store_path),
                encryption_key=b"short",
            )

    def test_invalid_key_type_on_construction(self) -> None:
        with self.assertRaises(EncryptionKeyError):
            CredentialStore(
                store_path=str(self._store_path),  # type: ignore[arg-type]
                encryption_key="not-bytes",
            )

    def test_missing_key_env_var_raises(self) -> None:
        os.environ.pop(KEY_ENV_VAR, None)
        with self.assertRaises(EncryptionKeyError):
            self._make_store()

    def test_non_hex_key_env_var_raises(self) -> None:
        os.environ[KEY_ENV_VAR] = "not-a-hex-string!!!"
        with self.assertRaises(EncryptionKeyError):
            self._make_store()

    def test_wrong_length_hex_key_raises(self) -> None:
        os.environ[KEY_ENV_VAR] = "abcdef"
        with self.assertRaises(EncryptionKeyError):
            self._make_store()

    # ------------------------------------------------------------------
    # Tampered ciphertext failure
    # ------------------------------------------------------------------

    def test_tampered_ciphertext_fails(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        tampered = bytearray(saved.encrypted_secret)
        tampered[5] ^= 0xFF
        saved.encrypted_secret = bytes(tampered)

        store._save_store()
        store2 = self._make_store()
        with self.assertRaises(TamperDetectedError):
            store2.get_decrypted_secret(saved.credential_id)

    def test_truncated_ciphertext_fails(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        saved.encrypted_secret = saved.encrypted_secret[:4]
        store._save_store()
        store2 = self._make_store()
        with self.assertRaises(TamperDetectedError):
            store2.get_decrypted_secret(saved.credential_id)

    # ------------------------------------------------------------------
    # Tampered auth tag failure
    # ------------------------------------------------------------------

    def test_tampered_auth_tag_fails(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        tag_start = len(saved.encrypted_secret) - 16
        tampered = bytearray(saved.encrypted_secret)
        tampered[tag_start + 5] ^= 0xFF
        saved.encrypted_secret = bytes(tampered)

        store._save_store()
        store2 = self._make_store()
        with self.assertRaises(TamperDetectedError):
            store2.get_decrypted_secret(saved.credential_id)

    # ------------------------------------------------------------------
    # Tampered nonce failure
    # ------------------------------------------------------------------

    def test_tampered_nonce_fails(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        tampered = bytearray(saved.nonce)
        tampered[3] ^= 0xFF
        saved.nonce = bytes(tampered)

        store._save_store()
        store2 = self._make_store()
        with self.assertRaises(TamperDetectedError):
            store2.get_decrypted_secret(saved.credential_id)

    # ------------------------------------------------------------------
    # Missing credential handling
    # ------------------------------------------------------------------

    def test_get_missing_credential_raises(self) -> None:
        store = self._make_store()
        with self.assertRaises(CredentialNotFoundError):
            store.get_decrypted_secret("nonexistent-id")

    def test_delete_missing_credential_raises(self) -> None:
        store = self._make_store()
        with self.assertRaises(CredentialNotFoundError):
            store.delete_credential("nonexistent-id")

    def test_update_missing_credential_raises(self) -> None:
        store = self._make_store()
        with self.assertRaises(CredentialNotFoundError):
            store.update_credential("nonexistent-id", "new-secret")

    # ------------------------------------------------------------------
    # Provider mismatch handling
    # ------------------------------------------------------------------

    def test_verify_provider_mismatch_passes(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, "openai", TEST_SECRET)
        store.verify_provider_mismatch(saved.credential_id, "openai")

    def test_verify_provider_mismatch_raises(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, "openai", TEST_SECRET)
        with self.assertRaises(ProviderMismatchError):
            store.verify_provider_mismatch(saved.credential_id, "anthropic")

    def test_verify_provider_mismatch_missing_credential(self) -> None:
        store = self._make_store()
        with self.assertRaises(CredentialNotFoundError):
            store.verify_provider_mismatch("nonexistent", "openai")

    # ------------------------------------------------------------------
    # Persistence roundtrip
    # ------------------------------------------------------------------

    def test_persistence_roundtrip(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        cid = saved.credential_id

        store2 = self._make_store()
        decrypted = store2.get_decrypted_secret(cid)
        self.assertEqual(decrypted, TEST_SECRET)

    def test_preserves_metadata_across_reload(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        cid = saved.credential_id

        store2 = self._make_store()
        credential = store2.get_credential(cid, decrypt=False)
        assert isinstance(credential, StoredCredential)
        self.assertEqual(credential.user_id, TEST_USER)
        self.assertEqual(credential.provider_id, TEST_PROVIDER)
        self.assertEqual(credential.created_at, saved.created_at)

    def test_file_is_not_plaintext(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        raw = self._store_path.read_text()
        self.assertNotIn(TEST_SECRET, raw)
        self.assertNotIn("sk-test", raw)

    # ------------------------------------------------------------------
    # Update flow
    # ------------------------------------------------------------------

    def test_update_changes_secret(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, "original-secret")
        cid = saved.credential_id

        store.update_credential(cid, "updated-secret")
        decrypted = store.get_decrypted_secret(cid)
        self.assertEqual(decrypted, "updated-secret")

    def test_update_preserves_ids(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        cid = saved.credential_id
        original_created = saved.created_at

        store.update_credential(cid, "new-secret-value")
        credential = store.get_credential(cid, decrypt=False)
        assert isinstance(credential, StoredCredential)
        self.assertEqual(credential.credential_id, cid)
        self.assertEqual(credential.user_id, TEST_USER)
        self.assertEqual(credential.provider_id, TEST_PROVIDER)
        self.assertEqual(credential.created_at, original_created)
        self.assertGreaterEqual(credential.updated_at, original_created)

    def test_update_persists_across_reload(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, "original-secret")
        cid = saved.credential_id
        store.update_credential(cid, "persisted-secret")

        store2 = self._make_store()
        decrypted = store2.get_decrypted_secret(cid)
        self.assertEqual(decrypted, "persisted-secret")

    # ------------------------------------------------------------------
    # Delete flow
    # ------------------------------------------------------------------

    def test_delete_removes_credential(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        cid = saved.credential_id

        store.delete_credential(cid)
        with self.assertRaises(CredentialNotFoundError):
            store.get_decrypted_secret(cid)

    def test_delete_persists_across_reload(self) -> None:
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        cid = saved.credential_id

        store.delete_credential(cid)
        store2 = self._make_store()
        with self.assertRaises(CredentialNotFoundError):
            store2.get_decrypted_secret(cid)

    # ------------------------------------------------------------------
    # Metadata listing
    # ------------------------------------------------------------------

    def test_list_metadata_returns_all(self) -> None:
        store = self._make_store()
        c1 = store.save_credential(TEST_USER, "openai", "sk-key-1")
        c2 = store.save_credential(TEST_USER, "anthropic", "sk-key-2")
        c3 = store.save_credential("other-user", "openai", "sk-key-3")

        all_meta = store.list_credential_metadata()
        self.assertEqual(len(all_meta), 3)

    def test_list_metadata_filters_by_user(self) -> None:
        store = self._make_store()
        c1 = store.save_credential(TEST_USER, "openai", "sk-key-1")
        store.save_credential("other-user", "anthropic", "sk-key-2")

        filtered = store.list_credential_metadata(user_id=TEST_USER)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].user_id, TEST_USER)

    def test_list_metadata_filters_by_provider(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, "openai", "sk-key-1")
        store.save_credential(TEST_USER, "anthropic", "sk-key-2")

        filtered = store.list_credential_metadata(provider_id="openai")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].provider_id, "openai")

    def test_list_metadata_filters_by_both(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, "openai", "sk-key-1")
        store.save_credential(TEST_USER, "anthropic", "sk-key-2")
        store.save_credential("other-user", "openai", "sk-key-3")

        filtered = store.list_credential_metadata(user_id=TEST_USER, provider_id="openai")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].provider_id, "openai")
        self.assertEqual(filtered[0].user_id, TEST_USER)

    def test_list_metadata_never_contains_secrets(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        meta_list = store.list_credential_metadata()
        self.assertEqual(len(meta_list), 1)
        meta = meta_list[0]
        self.assertIsInstance(meta, CredentialMetadata)
        self.assertEqual(meta.credential_id, meta.credential_id)
        self.assertEqual(meta.user_id, TEST_USER)
        self.assertEqual(meta.provider_id, TEST_PROVIDER)
        self.assertFalse(hasattr(meta, "encrypted_secret"))
        self.assertFalse(hasattr(meta, "nonce"))

    def test_list_metadata_empty_when_no_match(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, "openai", "sk-key-1")
        filtered = store.list_credential_metadata(provider_id="nonexistent")
        self.assertEqual(len(filtered), 0)

    # ------------------------------------------------------------------
    # get_credential_by_provider
    # ------------------------------------------------------------------

    def test_get_by_provider_decrypted(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        result = store.get_credential_by_provider(TEST_USER, TEST_PROVIDER, decrypt=True)
        assert isinstance(result, str)
        self.assertEqual(result, TEST_SECRET)

    def test_get_by_provider_not_decrypted(self) -> None:
        store = self._make_store()
        store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)

        result = store.get_credential_by_provider(TEST_USER, TEST_PROVIDER, decrypt=False)
        assert isinstance(result, StoredCredential)
        self.assertEqual(result.provider_id, TEST_PROVIDER)

    def test_get_by_provider_not_found(self) -> None:
        store = self._make_store()
        with self.assertRaises(CredentialNotFoundError):
            store.get_credential_by_provider(TEST_USER, "nonexistent")

    # ------------------------------------------------------------------
    # Corrupted store file handling
    # ------------------------------------------------------------------

    def test_corrupted_store_file_raises(self) -> None:
        self._store_path.write_text("{invalid json", encoding="utf-8")
        with self.assertRaises(CredentialStoreError):
            self._make_store()

    def test_empty_store_file_works(self) -> None:
        self._store_path.write_text('{"version": 1, "credentials": []}', encoding="utf-8")
        store = self._make_store()
        self.assertEqual(len(store.list_credential_metadata()), 0)

    def test_store_path_defaults_to_env(self) -> None:
        custom_path = Path(self._tmpdir) / "custom_store.enc"
        os.environ[STORE_PATH_ENV_VAR] = str(custom_path)
        store = CredentialStore(encryption_key=VALID_KEY)
        store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        self.assertTrue(custom_path.exists())

    # ------------------------------------------------------------------
    # Multiple credentials
    # ------------------------------------------------------------------

    def test_multiple_credentials_independent(self) -> None:
        store = self._make_store()
        s1 = store.save_credential(TEST_USER, "openai", "sk-openai-1")
        s2 = store.save_credential(TEST_USER, "anthropic", "sk-ant-1")
        s3 = store.save_credential("user-2", "openai", "sk-openai-2")

        self.assertEqual(store.get_decrypted_secret(s1.credential_id), "sk-openai-1")
        self.assertEqual(store.get_decrypted_secret(s2.credential_id), "sk-ant-1")
        self.assertEqual(store.get_decrypted_secret(s3.credential_id), "sk-openai-2")

    # ------------------------------------------------------------------
    # Obsolete env var rejection
    # ------------------------------------------------------------------

    def test_obsolete_env_var_is_ignored(self) -> None:
        os.environ.pop(KEY_ENV_VAR, None)
        os.environ["OMINI_CREDENTIAL_STORE_KEY"] = VALID_KEY_HEX
        with self.assertRaises(EncryptionKeyError):
            self._make_store()


# Security remediation v2 regressions (all fixtures are generated in temp dirs).


@pytest.mark.parametrize(
    "field,value",
    [("provider_id", "anthropic"), ("user_id", "user-B"), ("credential_id", "changed-id")],
)
def test_v2_identity_metadata_binding(tmp_path, field, value):
    path = tmp_path / "credentials.enc"
    store = CredentialStore(path, VALID_KEY)
    store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
    data = json.loads(path.read_text())
    data["credentials"][0][field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(TamperDetectedError):
        changed = CredentialStore(path, VALID_KEY)
        changed.get_decrypted_secret(data["credentials"][0]["credential_id"])


def test_duplicate_save_upserts_identity(tmp_path):
    path = tmp_path / "credentials.enc"
    store = CredentialStore(path, VALID_KEY)
    first = store.save_credential(TEST_USER, TEST_PROVIDER, "fake-first")
    before = first.to_dict()
    second = store.save_credential(TEST_USER, TEST_PROVIDER, "fake-second")
    assert len(store.list_credential_metadata()) == 1
    assert second.credential_id == first.credential_id
    assert second.created_at == first.created_at
    assert second.updated_at >= before["updated_at"]
    assert second.nonce.hex() != before["nonce"]
    assert store.get_credential_by_provider(TEST_USER, TEST_PROVIDER, decrypt=True) == "fake-second"
    assert (
        CredentialStore(path, VALID_KEY).get_decrypted_secret(first.credential_id) == "fake-second"
    )


def legacy_fixture(path, count=3):
    records = []
    for number in range(count):
        nonce = os.urandom(12)
        records.append(
            dict(
                credential_id=f"id-{number}",
                user_id=f"user-{number}",
                provider_id="openai",
                created_at=123.0,
                updated_at=456.0,
                nonce=nonce.hex(),
                encrypted_secret=AESGCM(VALID_KEY)
                .encrypt(nonce, f"fake-secret-{number}".encode(), None)
                .hex(),
            )
        )
    data = dict(version=1, credentials=records)
    path.write_text(json.dumps(data))
    return data


def test_legacy_migration_is_complete_and_persistent(tmp_path):
    path = tmp_path / "credentials.enc"
    before = legacy_fixture(path)
    store = CredentialStore(path, VALID_KEY)
    after = json.loads(path.read_text())
    assert after["version"] == 2
    assert len(after["credentials"]) == 3
    for old, new in zip(before["credentials"], after["credentials"]):
        for field in ("credential_id", "user_id", "provider_id", "created_at", "updated_at"):
            assert new[field] == old[field]
        assert new["nonce"] != old["nonce"]
        assert new["encrypted_secret"] != old["encrypted_secret"]
    reloaded = CredentialStore(path, VALID_KEY)
    for number in range(3):
        assert reloaded.get_decrypted_secret(f"id-{number}") == f"fake-secret-{number}"
        assert store.get_decrypted_secret(f"id-{number}") == f"fake-secret-{number}"
    after["credentials"][0]["provider_id"] = "anthropic"
    path.write_text(json.dumps(after))
    with pytest.raises(TamperDetectedError):
        CredentialStore(path, VALID_KEY).get_decrypted_secret("id-0")
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "fault", ["wrong-key", "corrupt-last", "duplicate-pair", "duplicate-id", "malformed-last"]
)
def test_legacy_failure_preserves_original_bytes(tmp_path, fault):
    path = tmp_path / "credentials.enc"
    data = legacy_fixture(path)
    key = VALID_KEY
    last = data["credentials"][-1]
    if fault == "wrong-key":
        key = b"X" * 32
    elif fault == "corrupt-last":
        last["encrypted_secret"] = (
            bytes([bytes.fromhex(last["encrypted_secret"])[0] ^ 1]).hex()
            + last["encrypted_secret"][2:]
        )
    elif fault == "duplicate-pair":
        last["user_id"] = data["credentials"][0]["user_id"]
    elif fault == "duplicate-id":
        last["credential_id"] = data["credentials"][0]["credential_id"]
    else:
        last["nonce"] = "not hex"
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(CredentialStoreError):
        CredentialStore(path, key)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("fault", ["pair", "id"])
def test_v2_duplicates_fail_closed(tmp_path, fault):
    path = tmp_path / "credentials.enc"
    store = CredentialStore(path, VALID_KEY)
    store.save_credential("user-A", "openai", "fake-a")
    store.save_credential("user-B", "openai", "fake-b")
    data = json.loads(path.read_text())
    field = "user_id" if fault == "pair" else "credential_id"
    data["credentials"][1][field] = data["credentials"][0][field]
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(CredentialStoreError, match="Duplicate credential identity"):
        CredentialStore(path, VALID_KEY)
    assert path.read_bytes() == before


@pytest.mark.parametrize("version", [3, 999, "invalid", "2", True, None, 2.0])
def test_unknown_version_rejected(tmp_path, version):
    path = tmp_path / "credentials.enc"
    path.write_text(json.dumps(dict(version=version, credentials=[])))
    before = path.read_bytes()
    with pytest.raises(CredentialStoreError):
        CredentialStore(path, VALID_KEY)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "malformed",
    [
        [],
        None,
        12,
        {},
        {"version": 2},
        {"version": 2, "credentials": {}},
        {"version": 2, "credentials": [None]},
    ],
)
def test_malformed_top_level_safe(tmp_path, malformed):
    path = tmp_path / "credentials.enc"
    path.write_text(json.dumps(malformed))
    with pytest.raises(CredentialStoreError) as error:
        CredentialStore(path, VALID_KEY)
    assert str(path) not in str(error.value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("credential_id", ""),
        ("credential_id", 1),
        ("user_id", None),
        ("provider_id", []),
        ("encrypted_secret", "xyz"),
        ("encrypted_secret", 1),
        ("nonce", "00"),
        ("nonce", "zz" * 12),
        ("created_at", "secret-in-timestamp"),
        ("created_at", True),
        ("updated_at", -1),
        ("updated_at", float("nan")),
        ("updated_at", float("inf")),
    ],
)
def test_malformed_record_is_controlled(tmp_path, field, value):
    path = tmp_path / "credentials.enc"
    data = legacy_fixture(path, 1)
    data["credentials"][0][field] = value
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(CredentialStoreError) as error:
        CredentialStore(path, VALID_KEY)
    assert str(error.value) == "Invalid credential store record"
    assert path.read_bytes() == before


def test_duplicate_json_fields_rejected(tmp_path):
    path = tmp_path / "credentials.enc"
    path.write_text('{"version":1,"version":2,"credentials":[]}')
    with pytest.raises(CredentialStoreError):
        CredentialStore(path, VALID_KEY)


@pytest.mark.parametrize("operation", ["migration", "save", "upsert", "update", "delete"])
@pytest.mark.parametrize("fault", ["replace", "fsync"])
def test_write_failure_preserves_original_and_memory(tmp_path, operation, fault):
    path = tmp_path / "credentials.enc"
    store = None
    if operation == "migration":
        legacy_fixture(path)
    else:
        store = CredentialStore(path, VALID_KEY)
        saved = store.save_credential("user-A", "openai", "original-fake-secret")
    before = path.read_bytes()
    with patch(
        f"config.encrypted_credential_store.os.{fault}",
        side_effect=OSError("sensitive-internal-path"),
    ):
        with pytest.raises(CredentialStoreError) as error:
            if operation == "migration":
                CredentialStore(path, VALID_KEY)
            elif operation == "save":
                store.save_credential("user-B", "openai", "new-fake-secret")
            elif operation == "upsert":
                store.save_credential("user-A", "openai", "new-fake-secret")
            elif operation == "update":
                store.update_credential(saved.credential_id, "new-fake-secret")
            else:
                store.delete_credential(saved.credential_id)
    assert str(error.value) == "Failed to save credential store"
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
    if store:
        assert len(store.list_credential_metadata()) == 1
        assert store.get_decrypted_secret(saved.credential_id) == "original-fake-secret"
        assert (
            CredentialStore(path, VALID_KEY).get_decrypted_secret(saved.credential_id)
            == "original-fake-secret"
        )


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits are not Windows ACLs")
@pytest.mark.parametrize("operation", ["new", "update", "migration", "load"])
def test_posix_file_and_temp_modes(tmp_path, operation):
    path = tmp_path / "credentials.enc"
    if operation == "migration":
        legacy_fixture(path)
    elif operation in ("update", "load"):
        store = CredentialStore(path, VALID_KEY)
        saved = store.save_credential("user-A", "openai", "fake-secret")
    if path.exists():
        path.chmod(0o666)
    original_replace = os.replace
    seen = []

    def inspect_replace(source, destination):
        assert Path(source).parent == path.parent
        assert stat.S_IMODE(Path(source).stat().st_mode) == 0o600
        assert source != path.with_suffix(".tmp")
        seen.append(source)
        original_replace(source, destination)

    previous_umask = os.umask(0)
    try:
        with patch("config.encrypted_credential_store.os.replace", side_effect=inspect_replace):
            if operation in ("migration", "load"):
                CredentialStore(path, VALID_KEY)
            elif operation == "update":
                store.update_credential(saved.credential_id, "fake-updated")
            else:
                CredentialStore(path, VALID_KEY).save_credential("user-A", "openai", "fake-secret")
    finally:
        os.umask(previous_umask)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert bool(seen) == (operation != "load")
    assert list(tmp_path.iterdir()) == [path]


def test_controller_and_adapter_consistency(tmp_path, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    from config.provider_settings_controller import ProviderSettingsController
    from config.provider_credential_adapter import ProviderCredentialAdapter

    monkeypatch.setenv("OMNI_PROVIDER_HEALTH_CACHE_DIR", str(tmp_path / "health"))
    store = CredentialStore(tmp_path / "credentials.enc", VALID_KEY)
    controller = ProviderSettingsController(store)
    controller.save_provider("user-A", "openai", "fake-first")
    original = store.get_credential_by_provider("user-A", "openai")
    controller.save_provider("user-A", "openai", "fake-second")
    assert len(store.list_credential_metadata("user-A", "openai")) == 1
    assert (
        store.get_credential_by_provider("user-A", "openai").credential_id == original.credential_id
    )
    assert ProviderCredentialAdapter(store).load_credential("user-A", "openai") == "fake-second"
    listed = [p for p in controller.list_providers("user-A") if p["provider"] == "openai"]
    assert len(listed) == 1 and listed[0]["configured"]
    controller.update_provider("user-A", "openai", "fake-third")
    assert store.get_credential_by_provider("user-A", "openai", decrypt=True) == "fake-third"
    controller.delete_provider("user-A", "openai")
    assert not store.list_credential_metadata()
    for secret in ("fake-first", "fake-second", "fake-third", VALID_KEY_HEX):
        assert secret not in caplog.text + json.dumps(listed)


def test_gitignore_protects_default_without_blanket_enc_rule(tmp_path):
    # Test Git semantics in an isolated repo, including cross-OS worktree runs.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text((PROJECT_ROOT / ".gitignore").read_text())
    result = subprocess.run(
        ["git", "check-ignore", "-v", "--no-index", "credentials.enc", "nested/credentials.enc"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.count(":credentials.enc") == 2
    unrelated = subprocess.run(
        ["git", "check-ignore", "--no-index", "legitimate.enc"],
        cwd=tmp_path,
        capture_output=True,
    )
    assert unrelated.returncode == 1


def test_v2_domain_binding_and_legacy_downgrade_rejected(tmp_path):
    from cryptography.exceptions import InvalidTag

    path = tmp_path / "credentials.enc"
    saved = CredentialStore(path, VALID_KEY).save_credential("user-A", "openai", "fake-secret")
    aad = json.dumps(
        {
            "domain": "omni-credential-store:v2",
            "credential_id": saved.credential_id,
            "user_id": "user-A",
            "provider_id": "openai",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert AESGCM(VALID_KEY).decrypt(saved.nonce, saved.encrypted_secret, aad) == b"fake-secret"
    with pytest.raises(InvalidTag):
        AESGCM(VALID_KEY).decrypt(saved.nonce, saved.encrypted_secret, None)
    data = json.loads(path.read_text())
    data["version"] = 1
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(TamperDetectedError):
        CredentialStore(path, VALID_KEY)
    assert path.read_bytes() == before


def test_legacy_metadata_history_cannot_be_authenticated_retroactively(tmp_path):
    path = tmp_path / "credentials.enc"
    data = legacy_fixture(path, 1)
    data["credentials"][0]["user_id"] = "legacy-rebound-user"
    path.write_text(json.dumps(data))
    migrated = CredentialStore(path, VALID_KEY)
    assert (
        migrated.get_credential_by_provider("legacy-rebound-user", "openai", decrypt=True)
        == "fake-secret-0"
    )
    data = json.loads(path.read_text())
    data["credentials"][0]["user_id"] = "another-user"
    path.write_text(json.dumps(data))
    with pytest.raises(TamperDetectedError):
        CredentialStore(path, VALID_KEY).get_decrypted_secret("id-0")


def test_timestamps_are_administrative_not_identity_aad(tmp_path):
    path = tmp_path / "credentials.enc"
    saved = CredentialStore(path, VALID_KEY).save_credential("user-A", "openai", "fake-secret")
    data = json.loads(path.read_text())
    data["credentials"][0]["updated_at"] += 1
    path.write_text(json.dumps(data))
    assert (
        CredentialStore(path, VALID_KEY).get_decrypted_secret(saved.credential_id) == "fake-secret"
    )


@pytest.mark.parametrize(
    "field",
    [
        "credential_id",
        "user_id",
        "provider_id",
        "nonce",
        "encrypted_secret",
        "created_at",
        "updated_at",
    ],
)
def test_missing_record_fields_fail_closed(tmp_path, field):
    path = tmp_path / "credentials.enc"
    data = legacy_fixture(path, 1)
    del data["credentials"][0][field]
    path.write_text(json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(CredentialStoreError):
        CredentialStore(path, VALID_KEY)
    assert path.read_bytes() == before


def test_real_settings_cli_uses_v2_without_exposing_stdin_secret(tmp_path):
    path = tmp_path / "credentials.enc"
    cli = PROJECT_ROOT / "backend/python/config/provider_settings_cli.py"
    child_env = {
        **os.environ,
        KEY_ENV_VAR: VALID_KEY_HEX,
        STORE_PATH_ENV_VAR: str(path),
        "OMNI_PROVIDER_HEALTH_CACHE_DIR": str(tmp_path / "health"),
    }
    for secret in ("fake-cli-first", "fake-cli-second"):
        result = subprocess.run(
            [sys.executable, str(cli), "save", "user-A", "openai"],
            input=secret,
            text=True,
            capture_output=True,
            env=child_env,
            check=True,
        )
        assert json.loads(result.stdout)["configured"]
        assert secret not in result.stdout + result.stderr
    store = CredentialStore(path, VALID_KEY)
    assert len(store.list_credential_metadata()) == 1
    assert store.get_credential_by_provider("user-A", "openai", decrypt=True) == "fake-cli-second"
    result = subprocess.run(
        [sys.executable, str(cli), "list", "user-A"],
        text=True,
        capture_output=True,
        env=child_env,
        check=True,
    )
    providers = json.loads(result.stdout)
    assert len([p for p in providers if p["provider"] == "openai" and p["configured"]]) == 1
    assert "fake-cli-" not in result.stdout + result.stderr


if __name__ == "__main__":
    unittest.main()
