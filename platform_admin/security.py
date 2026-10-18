import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


SECRET_PREFIX = "fernet:v1:"


def _fernet():
    configured_key = str(getattr(settings, "CREDENTIAL_ENCRYPTION_KEY", "") or "").strip()
    if configured_key:
        key = configured_key.encode("ascii")
    else:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value):
    if not value:
        return ""
    token = _fernet().encrypt(str(value).encode("utf-8")).decode("ascii")
    return f"{SECRET_PREFIX}{token}"


def decrypt_secret(value):
    if not value:
        return ""
    encoded_value = str(value)
    if not encoded_value.startswith(SECRET_PREFIX):
        raise RuntimeError("Unsupported legacy encrypted credential. Save the credential again.")
    try:
        token = encoded_value[len(SECRET_PREFIX):].encode("ascii")
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("The credential encryption key is invalid or has changed.") from exc
