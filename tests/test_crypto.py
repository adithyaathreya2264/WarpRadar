"""Tests for DH key exchange, AES-256-GCM encrypt/decrypt, and HKDF key derivation."""

import os
from warpradar.security.crypto import (
    generate_keypair,
    compute_shared_secret,
    derive_session_key,
    public_key_to_bytes,
    bytes_to_public_key,
    SessionCrypto,
)


class TestKeyExchange:
    """Test Diffie-Hellman key exchange."""

    def test_keypair_generation(self):
        kp = generate_keypair()
        assert kp.private_key is not None
        assert kp.public_key is not None

    def test_shared_secret_agreement(self):
        """Both sides must derive the same shared secret."""
        alice = generate_keypair()
        bob = generate_keypair()
        secret_a = compute_shared_secret(alice.private_key, bob.public_key)
        secret_b = compute_shared_secret(bob.private_key, alice.public_key)
        assert secret_a == secret_b

    def test_public_key_serialization_roundtrip(self):
        kp = generate_keypair()
        raw = public_key_to_bytes(kp.public_key)
        assert len(raw) == 256
        restored = bytes_to_public_key(raw)
        # Verify the restored key produces the same shared secret
        bob = generate_keypair()
        s1 = compute_shared_secret(bob.private_key, kp.public_key)
        s2 = compute_shared_secret(bob.private_key, restored)
        assert s1 == s2


class TestSessionKey:
    """Test HKDF session key derivation."""

    def test_derive_session_key_length(self):
        kp_a = generate_keypair()
        kp_b = generate_keypair()
        shared = compute_shared_secret(kp_a.private_key, kp_b.public_key)
        salt = os.urandom(16)
        key = derive_session_key(shared, salt)
        assert len(key) == 32  # AES-256

    def test_same_inputs_produce_same_key(self):
        kp_a = generate_keypair()
        kp_b = generate_keypair()
        shared = compute_shared_secret(kp_a.private_key, kp_b.public_key)
        salt = os.urandom(16)
        k1 = derive_session_key(shared, salt)
        k2 = derive_session_key(shared, salt)
        assert k1 == k2

    def test_different_salts_produce_different_keys(self):
        kp_a = generate_keypair()
        kp_b = generate_keypair()
        shared = compute_shared_secret(kp_a.private_key, kp_b.public_key)
        k1 = derive_session_key(shared, os.urandom(16))
        k2 = derive_session_key(shared, os.urandom(16))
        assert k1 != k2


class TestAESEncryption:
    """Test AES-256-GCM encrypt/decrypt roundtrip."""

    def _make_crypto(self) -> SessionCrypto:
        key = os.urandom(32)
        return SessionCrypto(key)

    def test_encrypt_decrypt_roundtrip(self):
        crypto = self._make_crypto()
        plaintext = b"Hello, WarpRadar!"
        ciphertext = crypto.encrypt(plaintext)
        assert ciphertext != plaintext
        result = crypto.decrypt(ciphertext)
        assert result == plaintext

    def test_empty_data(self):
        crypto = self._make_crypto()
        ct = crypto.encrypt(b"")
        assert crypto.decrypt(ct) == b""

    def test_large_data(self):
        crypto = self._make_crypto()
        data = os.urandom(1024 * 1024)  # 1 MB
        ct = crypto.encrypt(data)
        assert crypto.decrypt(ct) == data

    def test_different_keys_cannot_decrypt(self):
        c1 = self._make_crypto()
        c2 = self._make_crypto()
        ct = c1.encrypt(b"secret")
        import pytest
        with pytest.raises(Exception):
            c2.decrypt(ct)
