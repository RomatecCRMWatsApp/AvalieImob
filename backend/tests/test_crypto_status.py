# @module tests.test_crypto_status — diagnóstico da chave que cifra as credenciais BYOK.
#
# Responde, da própria plataforma, o que antes só o log do servidor dizia: a
# CREDENCIAIS_FERNET_KEY está válida ou o sistema caiu no fallback do JWT_SECRET?
import pytest
from cryptography.fernet import Fernet

from services.crypto_service import status


def test_chave_valida_e_pronta_para_producao(monkeypatch):
    monkeypatch.setenv("CREDENCIAIS_FERNET_KEY", Fernet.generate_key().decode())
    s = status()
    assert s["configurada"] and s["valida"]
    assert s["origem"] == "env" and s["pronto_para_producao"] is True
    assert s["ciclo_de_teste"] == "ok"          # cifrou e decifrou de verdade


def test_sem_chave_avisa_o_fallback(monkeypatch):
    monkeypatch.delenv("CREDENCIAIS_FERNET_KEY", raising=False)
    s = status()
    assert s["configurada"] is False
    assert s["origem"] == "jwt_secret" and s["pronto_para_producao"] is False
    assert "JWT_SECRET" in s["mensagem"]


def test_chave_invalida_e_denunciada(monkeypatch):
    monkeypatch.setenv("CREDENCIAIS_FERNET_KEY", "nao-e-uma-chave-fernet")
    s = status()
    assert s["configurada"] is True and s["valida"] is False
    assert s["pronto_para_producao"] is False
    assert "INVÁLIDA" in s["mensagem"]


def test_status_nunca_devolve_a_chave(monkeypatch):
    chave = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENCIAIS_FERNET_KEY", chave)
    assert chave not in str(status())
