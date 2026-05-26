import os
import tempfile

import pytest

from backend.crypto import crypto_manager

def test_rsa_key_encryption():
    # 1. Generate keypair
    private_pem, public_pem = crypto_manager.generate_keypair()
    assert private_pem is not None
    assert public_pem is not None

    # 2. Test AES encrypt
    plaintext = b"Classified Payload 123"
    aes_key = os.urandom(32)
    nonce, ct = crypto_manager.aes_gcm_encrypt(plaintext, aes_key)
    
    # 3. Encrypt AES key with RSA
    encapsulated_key = crypto_manager.encrypt_aes_key(aes_key, public_pem)
    assert len(encapsulated_key) == 128  # 1024-bit RSA ciphertext length

    # 4. Decrypt AES key
    recovered_aes_key = crypto_manager.decrypt_aes_key(encapsulated_key, private_pem)
    assert recovered_aes_key == aes_key

    # 5. Decrypt plaintext
    recovered_plaintext = crypto_manager.aes_gcm_decrypt(nonce, ct, recovered_aes_key)
    assert recovered_plaintext == plaintext

def test_encrypted_private_key():
    pwd = "super_secure_password"
    private_pem, public_pem = crypto_manager.generate_keypair(password=pwd)
    
    assert b"ENCRYPTED" in private_pem
    
    aes_key = os.urandom(32)
    encapsulated_key = crypto_manager.encrypt_aes_key(aes_key, public_pem)
    
    recovered_aes_key = crypto_manager.decrypt_aes_key(encapsulated_key, private_pem, password=pwd)
    assert recovered_aes_key == aes_key


def test_password_protected_pipeline_survives_image_stego_roundtrip():
    np = pytest.importorskip("numpy")
    Image = pytest.importorskip("PIL.Image")
    stego_manager = __import__("backend.stego", fromlist=["stego_manager"]).stego_manager

    pwd = "correct horse battery staple"
    plaintext = b"Top secret payload:" + (b"\xff" * 64) + os.urandom(128)

    private_pem, public_pem = crypto_manager.generate_keypair(password=pwd)
    aes_key = os.urandom(32)
    nonce, ciphertext = crypto_manager.aes_gcm_encrypt(plaintext, aes_key)
    encapsulated_key = crypto_manager.encrypt_aes_key(aes_key, public_pem)
    payload = encapsulated_key + nonce + ciphertext

    with tempfile.TemporaryDirectory() as tmpdir:
        carrier_path = os.path.join(tmpdir, "carrier.png")
        embedded_path = os.path.join(tmpdir, "embedded.png")
        extracted_path = os.path.join(tmpdir, "extracted.bin")

        carrier = np.zeros((80, 80, 3), dtype=np.uint8)
        Image.fromarray(carrier).save(carrier_path)

        assert stego_manager.embed_image_lsb(carrier_path, payload, embedded_path)
        extracted = stego_manager.extract_image_lsb(embedded_path, extracted_path)
        assert extracted == payload

    recovered_aes_key = crypto_manager.decrypt_aes_key(extracted[:128], private_pem, password=pwd)
    recovered_plaintext = crypto_manager.aes_gcm_decrypt(extracted[128:140], extracted[140:], recovered_aes_key)
    assert recovered_plaintext == plaintext
