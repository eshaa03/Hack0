from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import os
from typing import Tuple, Optional

class CryptoManager:
    def __init__(self):
        self.backend = default_backend()

    def generate_rsa_keypair(self) -> Tuple[bytes, bytes]:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=self.backend
        )
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return private_pem, public_pem

    def rsa_encrypt_aes_key(self, aes_key: bytes, public_key_pem: bytes) -> bytes:
        public_key = serialization.load_pem_public_key(public_key_pem, backend=self.backend)
        return public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def rsa_decrypt_aes_key(self, encrypted_aes_key: bytes, private_key_pem: bytes) -> bytes:
        private_key = serialization.load_pem_private_key(private_key_pem, password=None, backend=self.backend)
        return private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def aes_gcm_encrypt(self, plaintext: bytes, aes_key: bytes) -> Tuple[bytes, bytes]:
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext, None)
        return nonce, ct

    def aes_gcm_decrypt(self, nonce: bytes, ciphertext: bytes, aes_key: bytes) -> Optional[bytes]:
        aesgcm = AESGCM(aes_key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except InvalidTag:
            return None

crypto_manager = CryptoManager()
