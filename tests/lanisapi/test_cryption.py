"""Tests for the Lanis encryption (AES like CryptoJS, RSA handshake)."""

import base64
import re

import pytest
from Cryptodome.PublicKey import RSA

from lanis_mcp.lanisapi import cryption
from lanis_mcp.lanisapi.cryption import Cryptor, decrypt, encrypt
from lanis_mcp.lanisapi.exceptions import CryptionError, NotAuthenticatedError
from lanis_mcp.lanisapi.session import LanisSession

from .support import AJAX, Router, add_handshake

# Created with: printf 'Hallo Lanis' | openssl enc -aes-256-cbc -md md5
#   -S 0102030405060708 -pass pass:passwort -base64
# OpenSSL leaves out the Salted__ header when -S is given, so it is added here.
OPENSSL_VECTOR = base64.b64encode(
    b"Salted__"
    + bytes.fromhex("0102030405060708")
    + base64.b64decode("HawE8VKBc+/TJlQVKzeG1g==")
).decode()


def test_decrypts_openssl_output():
    assert decrypt(OPENSSL_VECTOR, "passwort") == "Hallo Lanis"


def test_roundtrip_with_unicode():
    encrypted = encrypt("Grüße & Ärger 🙂", "geheim")
    assert base64.b64decode(encrypted).startswith(b"Salted__")
    assert decrypt(encrypted, "geheim") == "Grüße & Ärger 🙂"


def test_encrypt_uses_random_salt():
    assert encrypt("x", "k") != encrypt("x", "k")


def test_wrong_passphrase_fails():
    with pytest.raises(CryptionError):
        decrypt(encrypt("Hallo Lanis, das ist ein Test", "richtig"), "falsch")


def test_rejects_data_without_salted_prefix():
    with pytest.raises(CryptionError, match="Salted__"):
        decrypt(base64.b64encode(b"x" * 32).decode(), "k")


def test_rejects_invalid_base64():
    with pytest.raises(CryptionError, match="base64"):
        decrypt("not base64!", "k")


def test_rejects_wrong_salt_length():
    with pytest.raises(CryptionError, match="Salt"):
        cryption._bytes_to_key(b"k", b"short")


def test_unpad_rejects_empty_data():
    with pytest.raises(CryptionError, match="padding"):
        cryption._unpad(b"")


def test_generate_secret_encrypts_key_with_itself(monkeypatch: pytest.MonkeyPatch):
    seen: list[tuple[str, str]] = []

    def fake_encrypt(plain: str, passphrase: str) -> str:
        seen.append((plain, passphrase))
        return "encrypted"

    monkeypatch.setattr(cryption, "encrypt", fake_encrypt)
    assert cryption.generate_secret() == "encrypted"

    plain, passphrase = seen[0]
    assert plain == passphrase
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}-[0-9a-f]{6}3[0-9a-f]{2}",
        plain,
    )


def test_generate_secret_is_random():
    assert cryption.generate_secret() != cryption.generate_secret()


def test_handshake_agrees_on_secret(rsa_key: RSA.RsaKey):
    router = Router()
    add_handshake(router, rsa_key)
    cryptor = Cryptor()
    cryptor.handshake(LanisSession(transport=router.transport))

    assert cryptor.authenticated
    assert cryptor.decrypt(cryptor.encrypt("Hallo")) == "Hallo"
    handshake_request = router.calls("POST", AJAX)[0]
    assert 0 <= int(handshake_request.url.params["s"]) <= 2000


def test_handshake_with_wrong_challenge_fails(rsa_key: RSA.RsaKey):
    router = Router()
    add_handshake(router, rsa_key, tamper=True)
    cryptor = Cryptor()
    with pytest.raises(CryptionError, match="wrong challenge"):
        cryptor.handshake(LanisSession(transport=router.transport))
    assert not cryptor.authenticated


def test_handshake_without_public_key_fails():
    router = Router()
    router.add("GET", AJAX, {"error": "nope"}, query={"f": "rsaPublicKey"})
    with pytest.raises(CryptionError, match="public key"):
        Cryptor().handshake(LanisSession(transport=router.transport))


def test_handshake_with_broken_public_key_fails():
    router = Router()
    router.add("GET", AJAX, {"publickey": "garbage"}, query={"f": "rsaPublicKey"})
    with pytest.raises(CryptionError, match="public key"):
        Cryptor().handshake(LanisSession(transport=router.transport))


def test_handshake_without_challenge_fails(rsa_key: RSA.RsaKey):
    router = Router()
    add_handshake(router, rsa_key)
    router.add("POST", AJAX, {"error": "nope"}, query={"f": "rsaHandshake"})
    with pytest.raises(CryptionError, match="challenge"):
        Cryptor().handshake(LanisSession(transport=router.transport))


def test_encrypt_and_decrypt_need_handshake():
    with pytest.raises(NotAuthenticatedError):
        Cryptor().encrypt("x")
    with pytest.raises(NotAuthenticatedError):
        Cryptor().decrypt("x")
