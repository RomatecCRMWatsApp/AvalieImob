# Testes do crypto_service (BYOK) — round-trip Fernet + falha com chave errada + máscara.
import pytest
from cryptography.fernet import Fernet

from services import crypto_service as CS


def test_encrypt_decrypt_json_roundtrip():
    d = {"token_api": "abc123SECRET", "crypt_key": "xyz789", "uuid_safe": "cofre-1"}
    enc = CS.encrypt_json(d)
    assert isinstance(enc, str)
    assert "abc123SECRET" not in enc          # não vaza em claro
    assert CS.decrypt_json(enc) == d


def test_decrypt_token_invalido_falha():
    with pytest.raises(Exception):
        CS.decrypt_json("isto-nao-e-um-token-fernet")


def test_decrypt_com_chave_errada_falha(monkeypatch):
    monkeypatch.setenv("CREDENCIAIS_FERNET_KEY", Fernet.generate_key().decode())
    enc = CS.encrypt_json({"a": 1})
    monkeypatch.setenv("CREDENCIAIS_FERNET_KEY", Fernet.generate_key().decode())
    with pytest.raises(Exception):
        CS.decrypt_json(enc)


def test_mascarar():
    assert CS.mascarar("abcdef12343f2a").endswith("3f2a")
    assert CS.mascarar("abcdef12343f2a").startswith("•")
    assert CS.mascarar("") == ""
    assert CS.mascarar(None) == ""
    assert CS.mascarar("ab") == "••"          # curto: não expõe nada
