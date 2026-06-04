"""Comprehensive tests for encrypted credential storage (P5D)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend" / "python"))

from config.encrypted_credential_store import (
    AES256_KEY_LENGTH,
    KEY_ENV_VAR,
    KEY_ENV_VAR_LEGACY,
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
        os.environ.pop(KEY_ENV_VAR_LEGACY, None)
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
        self.assertNotEqual(
            saved.encrypted_secret.hex(), TEST_SECRET.encode("utf-8").hex()
        )

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
        other_store = CredentialStore(
            store_path=str(self._store_path), encryption_key=other_key
        )
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

        filtered = store.list_credential_metadata(
            user_id=TEST_USER, provider_id="openai"
        )
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

        self.assertEqual(
            store.get_decrypted_secret(s1.credential_id), "sk-openai-1"
        )
        self.assertEqual(
            store.get_decrypted_secret(s2.credential_id), "sk-ant-1"
        )
        self.assertEqual(
            store.get_decrypted_secret(s3.credential_id), "sk-openai-2"
        )

    # ------------------------------------------------------------------
    # Legacy env var support
    # ------------------------------------------------------------------

    def test_legacy_env_var(self) -> None:
        os.environ.pop(KEY_ENV_VAR, None)
        os.environ["OMINI_CREDENTIAL_STORE_KEY"] = VALID_KEY_HEX
        store = self._make_store()
        saved = store.save_credential(TEST_USER, TEST_PROVIDER, TEST_SECRET)
        self.assertEqual(store.get_decrypted_secret(saved.credential_id), TEST_SECRET)


if __name__ == "__main__":
    unittest.main()
