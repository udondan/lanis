"""Encryption that Lanis uses for the "Nachrichten" app.

Lanis encrypts messages with a key that the client chooses and sends RSA
encrypted during a handshake. The AES part is compatible with CryptoJS
(``Salted__`` prefix, key derivation with ``EVP_BytesToKey`` and MD5). Lanis
dictates these algorithms, so they cannot be swapped for stronger ones.

Based on
https://stackoverflow.com/questions/36762098/how-to-decrypt-password-from-javascript-cryptojs-aes-encryptpassword-passphras
and https://github.com/koenidv/sph-planner/blob/main/app/src/main/java/de/koenidv/sph/networking/Cryption.kt
"""

import base64
import logging
import re
import secrets
from hashlib import md5
from typing import Optional

from Cryptodome.Cipher import AES, PKCS1_v1_5
from Cryptodome.PublicKey import RSA

from . import _urls
from .exceptions import CryptionError, NotAuthenticatedError
from .session import LanisSession

LOGGER = logging.getLogger(__name__)

_SALTED = b"Salted__"
_BLOCK_SIZE = 16
_KEY_PATTERN = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx-xxxxxx3xx"


def _bytes_to_key(passphrase: bytes, salt: bytes, length: int = 48) -> bytes:
    """Derive key and IV like OpenSSL's ``EVP_BytesToKey`` with MD5 (as CryptoJS does)."""
    if len(salt) != 8:
        raise CryptionError(f"Salt must be 8 bytes, got {len(salt)}.")
    data = passphrase + salt
    # MD5 is required for compatibility with CryptoJS, which Lanis uses.
    block = md5(data, usedforsecurity=False).digest()
    result = block
    while len(result) < length:
        block = md5(block + data, usedforsecurity=False).digest()
        result += block
    return result[:length]


def _pad(data: bytes) -> bytes:
    """Apply PKCS#7 padding."""
    length = _BLOCK_SIZE - len(data) % _BLOCK_SIZE
    return data + bytes([length]) * length


def _unpad(data: bytes) -> bytes:
    """Remove PKCS#7 padding."""
    if not data or not 1 <= data[-1] <= _BLOCK_SIZE:
        raise CryptionError("Invalid padding in decrypted data.")
    return data[: -data[-1]]


def encrypt(plain: str, passphrase: str) -> str:
    """Encrypt ``plain`` with AES-256-CBC, CryptoJS compatible."""
    salt = secrets.token_bytes(8)
    key_iv = _bytes_to_key(passphrase.encode(), salt)
    aes = AES.new(key_iv[:32], AES.MODE_CBC, key_iv[32:])
    encrypted = aes.encrypt(_pad(plain.encode()))
    return base64.b64encode(_SALTED + salt + encrypted).decode()


def decrypt(encrypted: str, passphrase: str) -> str:
    """Decrypt CryptoJS compatible AES-256-CBC data."""
    try:
        raw = base64.b64decode(encrypted.encode())
    except ValueError as err:
        raise CryptionError("Encrypted data is not valid base64.") from err
    if raw[:8] != _SALTED:
        raise CryptionError("Encrypted data has no Salted__ prefix.")
    key_iv = _bytes_to_key(passphrase.encode(), raw[8:16])
    aes = AES.new(key_iv[:32], AES.MODE_CBC, key_iv[32:])
    try:
        return _unpad(aes.decrypt(raw[16:])).decode()
    except (ValueError, UnicodeDecodeError) as err:
        raise CryptionError("Could not decrypt data.") from err


def generate_secret() -> str:
    """Generate the AES passphrase for a handshake.

    Lanis' JavaScript fills a UUID-like pattern with random hex digits and
    encrypts it with itself. This does the same with a secure random source.
    """
    key = re.sub(r"[xy]", lambda _: secrets.choice("0123456789abcdef"), _KEY_PATTERN)
    return encrypt(key, key)


class Cryptor:
    """Holds the passphrase that Lanis and the client agreed on."""

    def __init__(self) -> None:  # noqa: D107
        self._secret: Optional[str] = None

    @property
    def authenticated(self) -> bool:
        """Whether the handshake succeeded."""
        return self._secret is not None

    def handshake(self, session: LanisSession) -> None:
        """Agree on a passphrase with Lanis; raise ``CryptionError`` if that fails."""
        secret = generate_secret()

        response = session.get(_urls.AJAX, params={"f": "rsaPublicKey"})
        try:
            public_key = session.json(response)["publickey"]
            rsa = PKCS1_v1_5.new(RSA.import_key(public_key))
        except (KeyError, TypeError, ValueError) as err:
            raise CryptionError("Lanis did not return a usable public key.") from err

        encrypted_secret = base64.b64encode(rsa.encrypt(secret.encode())).decode()
        response = session.post(
            _urls.AJAX,
            params={"f": "rsaHandshake", "s": str(secrets.randbelow(2001))},
            data={"key": encrypted_secret},
        )
        try:
            challenge = str(session.json(response)["challenge"])
        except (KeyError, TypeError) as err:
            raise CryptionError("Lanis did not return a handshake challenge.") from err

        if decrypt(challenge, secret) != secret:
            raise CryptionError("Lanis answered the handshake with a wrong challenge.")

        self._secret = secret
        LOGGER.debug("Encryption handshake succeeded.")

    def encrypt(self, plain: str) -> str:
        """Encrypt with the agreed passphrase."""
        return encrypt(plain, self._require_secret())

    def decrypt(self, encrypted: str) -> str:
        """Decrypt with the agreed passphrase."""
        return decrypt(encrypted, self._require_secret())

    def _require_secret(self) -> str:
        if self._secret is None:
            raise NotAuthenticatedError("The encryption handshake has not run yet.")
        return self._secret
