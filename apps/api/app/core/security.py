from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel

from apps.api.app.core.config import settings


def generate_rsa_keypair() -> tuple[RSAPrivateKey, RSAPublicKey]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()


def serialize_private_key(key: RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def serialize_public_key(key: RSAPublicKey) -> bytes:
    return key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def deserialize_private_key(data: bytes) -> RSAPrivateKey:
    return serialization.load_pem_private_key(data, password=None)


def deserialize_public_key(data: bytes) -> RSAPublicKey:
    return serialization.load_pem_public_key(data)


def compute_kid(public_key: RSAPublicKey) -> str:
    der_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der_bytes).hexdigest()[:16]


def encrypt_private_key(key_bytes: bytes, encryption_key: str) -> bytes:
    fernet = Fernet(encryption_key.encode())
    return fernet.encrypt(key_bytes)


def decrypt_private_key(encrypted_bytes: bytes, encryption_key: str) -> bytes:
    fernet = Fernet(encryption_key.encode())
    return fernet.decrypt(encrypted_bytes)


def get_encryption_key_from_env(env_key: str | None) -> bytes | None:
    if env_key is None:
        return None
    key = env_key.encode()
    if len(key) < 32:
        salt = b"ai-enterprises-key-derivation"
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
        key = kdf.derive(key)
    return key


class JWK(BaseModel):
    kty: str = "RSA"
    kid: str
    n: str
    e: str = "AQAB"
    alg: str = "RS256"
    use: str = "sig"


class JWKS(BaseModel):
    keys: list[JWK]


def public_key_to_jwk(public_key: RSAPublicKey, kid: str) -> JWK:
    pub_numbers = public_key.public_numbers()
    n_bytes = pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big")
    n_b64 = _base64url_encode(n_bytes)
    return JWK(kty="RSA", kid=kid, n=n_b64, e="AQAB", alg="RS256", use="sig")


def _base64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class CryptoContext:
    def __init__(self) -> None:
        self._private_key: RSAPrivateKey | None = None
        self._public_key: RSAPublicKey | None = None
        self._kid: str | None = None
        self._loaded = False

    def initialize(self) -> None:
        key_dir = Path(settings.JWT_PRIVATE_KEY_PATH).parent
        key_dir.mkdir(parents=True, exist_ok=True)

        priv_path = Path(settings.JWT_PRIVATE_KEY_PATH)
        pub_path = Path(settings.JWT_PUBLIC_KEY_PATH)

        if priv_path.exists() and pub_path.exists():
            priv_data = priv_path.read_bytes()
            enc_key = settings.JWT_PRIVATE_KEY_ENCRYPTION_KEY
            if enc_key:
                priv_data = decrypt_private_key(priv_data, enc_key)
            self._private_key = deserialize_private_key(priv_data)
            self._public_key = deserialize_public_key(pub_path.read_bytes())
        else:
            self._private_key, self._public_key = generate_rsa_keypair()
            priv_data = serialize_private_key(self._private_key)
            enc_key = settings.JWT_PRIVATE_KEY_ENCRYPTION_KEY
            if enc_key:
                priv_data = encrypt_private_key(priv_data, enc_key)
            priv_path.write_bytes(priv_data)
            pub_path.write_bytes(serialize_public_key(self._public_key))

        self._kid = compute_kid(self._public_key)
        self._loaded = True

    @property
    def private_key(self) -> RSAPrivateKey:
        assert self._private_key is not None, "CryptoContext not initialized"
        return self._private_key

    @property
    def public_key(self) -> RSAPublicKey:
        assert self._public_key is not None, "CryptoContext not initialized"
        return self._public_key

    @property
    def kid(self) -> str:
        assert self._kid is not None, "CryptoContext not initialized"
        return self._kid

    def get_jwks(self) -> JWKS:
        jwk = public_key_to_jwk(self.public_key, self.kid)
        return JWKS(keys=[jwk])


crypto = CryptoContext()


def uuid7() -> uuid.UUID:
    timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
    rand_bytes = uuid.uuid4().bytes[2:8]
    uuid_bytes = (
        timestamp.to_bytes(6, "big")
        + bytes([(rand_bytes[0] & 0x0F) | 0x70])
        + rand_bytes[1:3]
        + bytes([(rand_bytes[3] & 0x3F) | 0x80])
        + rand_bytes[4:6]
    )
    return uuid.UUID(bytes=uuid_bytes)