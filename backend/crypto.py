from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag
import os
from typing import Tuple, Optional

class CryptoManager:
    def __init__(self):
        self.backend = default_backend()

    def generate_keypair(self, password: Optional[str] = None) -> Tuple[bytes, bytes]:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=1024,
            backend=self.backend
        )
        public_key = private_key.public_key()

        encryption_alg = serialization.BestAvailableEncryption(password.encode()) if password else serialization.NoEncryption()
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_alg
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return private_pem, public_pem

    def encrypt_aes_key(self, aes_key: bytes, public_key_pem: bytes) -> bytes:
        public_key = serialization.load_pem_public_key(public_key_pem, backend=self.backend)
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        return encrypted_key

    def decrypt_aes_key(self, encrypted_key: bytes, private_key_pem: bytes, password: Optional[str] = None) -> bytes:
        pwd_bytes = password.encode() if password else None
        private_key = serialization.load_pem_private_key(private_key_pem, password=pwd_bytes, backend=self.backend)
        
        aes_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        return aes_key

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

    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200000,
            backend=self.backend,
        )
        return kdf.derive(password.encode("utf-8"))

    def encrypt_with_password(self, plaintext: bytes, password: str) -> Tuple[bytes, bytes, bytes]:
        salt = os.urandom(16)
        aes_key = self.derive_key_from_password(password, salt)
        nonce, ciphertext = self.aes_gcm_encrypt(plaintext, aes_key)
        return salt, nonce, ciphertext

    def decrypt_with_password(self, salt: bytes, nonce: bytes, ciphertext: bytes, password: str) -> Optional[bytes]:
        aes_key = self.derive_key_from_password(password, salt)
        return self.aes_gcm_decrypt(nonce, ciphertext, aes_key)

crypto_manager = CryptoManager()
