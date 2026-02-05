"""Security - Diffie-Hellman key exchange and AES-256-GCM encryption."""

import os
import secrets
from dataclasses import dataclass
from typing import Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


# DH Parameters (RFC 3526 Group 14 - 2048-bit MODP Group)
# Using pre-defined parameters for interoperability
DH_P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16,
)
DH_G = 2

# AES-GCM settings
AES_KEY_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits (standard for GCM)


@dataclass
class KeyPair:
    """Ephemeral DH key pair."""
    private_key: int
    public_key: int


def generate_keypair() -> KeyPair:
    """Generate an ephemeral DH key pair."""
    # Generate random private key (256 bits)
    private_key = secrets.randbelow(DH_P - 2) + 1
    
    # Calculate public key: g^private mod p
    public_key = pow(DH_G, private_key, DH_P)
    
    return KeyPair(private_key=private_key, public_key=public_key)


def compute_shared_secret(my_private_key: int, their_public_key: int) -> bytes:
    """
    Compute the shared secret using DH.
    
    Args:
        my_private_key: Our private key
        their_public_key: Peer's public key
    
    Returns:
        The shared secret as bytes
    """
    # Compute shared secret: their_public^my_private mod p
    shared_int = pow(their_public_key, my_private_key, DH_P)
    
    # Convert to bytes (256 bytes for 2048-bit number)
    return shared_int.to_bytes(256, byteorder="big")


def derive_session_key(shared_secret: bytes, salt: bytes = None) -> bytes:
    """
    Derive an AES-256 session key from the shared secret using HKDF.
    
    Args:
        shared_secret: The raw shared secret from DH
        salt: Optional salt for key derivation
    
    Returns:
        32-byte AES key
    """
    if salt is None:
        salt = b"WarpRadar-v1"
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE,
        salt=salt,
        info=b"session-key",
        backend=default_backend(),
    )
    
    return hkdf.derive(shared_secret)


class SessionCrypto:
    """Manages encryption/decryption for a session."""
    
    def __init__(self, session_key: bytes):
        """
        Initialize with a session key.
        
        Args:
            session_key: 32-byte AES-256 key
        """
        self._aesgcm = AESGCM(session_key)
        self._nonce_counter = 0
    
    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """
        Encrypt data with AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            associated_data: Optional AAD for authentication
        
        Returns:
            nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        # Generate unique nonce using counter + random
        nonce = self._generate_nonce()
        
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
        
        return nonce + ciphertext
    
    def decrypt(self, ciphertext: bytes, associated_data: bytes = None) -> bytes:
        """
        Decrypt data with AES-256-GCM.
        
        Args:
            ciphertext: nonce + encrypted data + tag
            associated_data: Optional AAD for authentication
        
        Returns:
            Decrypted plaintext
        
        Raises:
            InvalidTag: If authentication fails
        """
        if len(ciphertext) < NONCE_SIZE:
            raise ValueError("Ciphertext too short")
        
        nonce = ciphertext[:NONCE_SIZE]
        encrypted = ciphertext[NONCE_SIZE:]
        
        return self._aesgcm.decrypt(nonce, encrypted, associated_data)
    
    def _generate_nonce(self) -> bytes:
        """Generate a unique nonce."""
        # Use counter for first 4 bytes, random for rest
        self._nonce_counter += 1
        counter_bytes = self._nonce_counter.to_bytes(4, byteorder="big")
        random_bytes = os.urandom(NONCE_SIZE - 4)
        return counter_bytes + random_bytes


def public_key_to_bytes(public_key: int) -> bytes:
    """Convert public key integer to bytes for transmission."""
    return public_key.to_bytes(256, byteorder="big")


def bytes_to_public_key(data: bytes) -> int:
    """Convert received bytes back to public key integer."""
    return int.from_bytes(data, byteorder="big")
