"""
Crypto utilities for encrypting/decrypting sensitive data (API keys).
Uses Fernet symmetric encryption derived from the app's SECRET_KEY.
"""
import base64
import hashlib
from cryptography.fernet import Fernet
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Derive a stable Fernet key from the app's SECRET_KEY via SHA-256 → base64
_fernet_key = base64.urlsafe_b64encode(
    hashlib.sha256(settings.secret_key.encode()).digest()
)
_fernet = Fernet(_fernet_key)


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key for storage in the database."""
    if not plain_key:
        return ""
    return _fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key from the database."""
    if not encrypted_key:
        return ""
    return _fernet.decrypt(encrypted_key.encode()).decode()


def mask_api_key(key: str) -> str:
    """Mask an API key for display (show first 4 and last 4 chars)."""
    if not key or len(key) < 10:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
