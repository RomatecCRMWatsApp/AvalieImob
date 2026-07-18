# @module tests.test_pagamento_seguranca — assinatura HMAC do webhook MP + regra de estorno
import hashlib
import hmac

from services.mp_webhook_seguranca import validar_assinatura, montar_manifest
from models.auditoria_acesso import deve_revogar_acesso

SEGREDO = "segredo-de-teste"


def _assina(data_id, request_id, ts, segredo=SEGREDO):
    manifest = montar_manifest(data_id, request_id, ts)
    v1 = hmac.new(segredo.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={v1}"


# ── Assinatura HMAC (x-signature) ───────────────────────────────────────────
def test_manifest_segue_o_template_do_mercado_pago():
    assert montar_manifest("123", "req-1", "1704908010") == \
        "id:123;request-id:req-1;ts:1704908010;"


def test_manifest_omite_partes_ausentes():
    assert montar_manifest("123", None, "999") == "id:123;ts:999;"


def test_id_alfanumerico_vai_em_minusculas():
    """Regra do MP: id alfanumérico entra no manifest em lowercase."""
    assert montar_manifest("ABC123", "r", "1") == "id:abc123;request-id:r;ts:1;"


def test_assinatura_valida_e_aceita():
    cab = _assina("123", "req-1", "1704908010")
    assert validar_assinatura(cab, "req-1", "123", SEGREDO) is True


def test_assinatura_com_segredo_errado_e_rejeitada():
    cab = _assina("123", "req-1", "1704908010", segredo="outro-segredo")
    assert validar_assinatura(cab, "req-1", "123", SEGREDO) is False


def test_payload_adulterado_e_rejeitado():
    """Assina para o pagamento 123 mas tenta usar no 999."""
    cab = _assina("123", "req-1", "1704908010")
    assert validar_assinatura(cab, "req-1", "999", SEGREDO) is False


def test_cabecalho_malformado_e_rejeitado():
    assert validar_assinatura("lixo", "req-1", "123", SEGREDO) is False
    assert validar_assinatura("", "req-1", "123", SEGREDO) is False
    assert validar_assinatura(None, "req-1", "123", SEGREDO) is False


def test_sem_segredo_configurado_nao_valida():
    """Sem segredo no ambiente a checagem é pulada (não quebra produção)."""
    cab = _assina("123", "req-1", "1704908010")
    assert validar_assinatura(cab, "req-1", "123", "") is True


# ── Regra de revogação por estorno ──────────────────────────────────────────
def test_estorno_revoga_acesso():
    assert deve_revogar_acesso("refunded", houve_aprovacao_posterior=False) is True
    assert deve_revogar_acesso("charged_back", houve_aprovacao_posterior=False) is True
    assert deve_revogar_acesso("cancelled", houve_aprovacao_posterior=False) is True


def test_aprovado_nunca_revoga():
    assert deve_revogar_acesso("approved", houve_aprovacao_posterior=False) is False


def test_pendente_nunca_revoga():
    assert deve_revogar_acesso("pending", houve_aprovacao_posterior=False) is False
    assert deve_revogar_acesso("in_process", houve_aprovacao_posterior=False) is False


def test_recusa_nao_revoga_plano_vigente():
    """Cartão recusado num upgrade não pode derrubar quem já pagou."""
    assert deve_revogar_acesso("rejected", houve_aprovacao_posterior=False) is False


def test_estorno_de_pagamento_antigo_nao_derruba_renovacao():
    """REGRA CRÍTICA: se houve pagamento aprovado DEPOIS, o plano se sustenta."""
    assert deve_revogar_acesso("refunded", houve_aprovacao_posterior=True) is False
    assert deve_revogar_acesso("charged_back", houve_aprovacao_posterior=True) is False
