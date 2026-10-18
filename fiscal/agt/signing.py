import base64
import json

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from .errors import AGTConfigurationError


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _b64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def sign_payload(payload, private_key_pem, key_reference=""):
    if not private_key_pem:
        raise AGTConfigurationError("No AGT producer private key is configured.")
    header = {"alg": "RS256", "typ": "JWT"}
    if key_reference:
        header["kid"] = key_reference
    signing_input = b".".join((_b64url(canonical_json(header)), _b64url(canonical_json(payload))))
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return b".".join((signing_input, _b64url(signature))).decode("ascii")


def verify_payload(compact_jws, public_key_pem):
    encoded_header, encoded_payload, encoded_signature = compact_jws.split(".")
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
    key = serialization.load_pem_public_key(public_key_pem)
    key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
    payload = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    return json.loads(payload)
