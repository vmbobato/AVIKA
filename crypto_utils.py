import base64, os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY = base64.b64decode(os.environ["ENC_KEY_B64"])

def encrypt_str(plaintext: str) -> tuple[str, str]:
    """Return (ciphertext_b64, nonce_b64) using AES-GCM."""
    aes = AESGCM(_KEY)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(ct).decode(), base64.b64encode(nonce).decode()

def decrypt_str(cipher_b64: str, nonce_b64: str) -> str:
    aes = AESGCM(_KEY)
    ct = base64.b64decode(cipher_b64)
    nonce = base64.b64decode(nonce_b64)
    return aes.decrypt(nonce, ct, None).decode()
