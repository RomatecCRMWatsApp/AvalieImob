# @module tests.test_completude_perfil — checklist de configuração do assinante
from services.completude_perfil import calcular, ESSENCIAIS


def _ctx(**kw):
    base = {"perfil": {}, "tem_logo": False, "tem_certificado_icp": False, "integracoes": {}}
    base.update(kw)
    return base


def _por_chave(res):
    return {i["chave"]: i for i in res["itens"]}


def test_perfil_vazio_nao_tem_nada_pronto():
    r = calcular(**_ctx())
    assert r["pct"] == 0
    assert r["pct_essencial"] == 0
    assert set(r["faltando_essencial"]) == set(ESSENCIAIS)


def test_todo_item_explica_o_impacto_no_laudo():
    """Sem o 'por que importa', vira lista burocratica que ninguem preenche."""
    for item in calcular(**_ctx())["itens"]:
        assert item["impacto"], f"item {item['chave']} sem impacto"
        assert item["rota"], f"item {item['chave']} sem destino"
        assert item["grupo"]


def test_registros_contam_como_preenchido():
    r = calcular(**_ctx(perfil={"registros": [{"tipo": "CRECI", "numero": "4705", "uf": "MA"}]}))
    assert _por_chave(r)["registros"]["ok"] is True


def test_registro_sem_numero_nao_conta():
    r = calcular(**_ctx(perfil={"registros": [{"tipo": "CRECI", "numero": ""}]}))
    assert _por_chave(r)["registros"]["ok"] is False


def test_cidade_e_uf_precisam_dos_dois():
    assert _por_chave(calcular(**_ctx(perfil={"cidade": "Açailândia"})))["local"]["ok"] is False
    r = calcular(**_ctx(perfil={"cidade": "Açailândia", "uf": "MA"}))
    assert _por_chave(r)["local"]["ok"] is True


def test_assinatura_grafica_reconhecida():
    r = calcular(**_ctx(perfil={"assinatura_visual_b64": "data:image/png;base64,AAA"}))
    assert _por_chave(r)["assinatura"]["ok"] is True


def test_logo_vem_de_fora_do_perfil():
    assert _por_chave(calcular(**_ctx(tem_logo=True)))["logo"]["ok"] is True


def test_certificado_icp_vem_de_fora_do_perfil():
    assert _por_chave(calcular(**_ctx(tem_certificado_icp=True)))["certificado_icp"]["ok"] is True


def test_zapi_exige_credenciais_e_ativo():
    parcial = {"zapi_instance_id": "x", "zapi_token": "y", "zapi_ativo": False}
    assert _por_chave(calcular(**_ctx(integracoes=parcial)))["zapi"]["ok"] is False
    completo = {**parcial, "zapi_ativo": True}
    assert _por_chave(calcular(**_ctx(integracoes=completo)))["zapi"]["ok"] is True


def test_telegram_exige_token_e_ativo():
    r = calcular(**_ctx(integracoes={"telegram_bot_token": "t", "telegram_ativo": True}))
    assert _por_chave(r)["telegram"]["ok"] is True


def test_essenciais_nao_incluem_integracoes():
    """Z-API e certificado exigem credencial externa — nao podem travar o inicio."""
    assert "zapi" not in ESSENCIAIS
    assert "telegram" not in ESSENCIAIS
    assert "certificado_icp" not in ESSENCIAIS


def test_percentual_essencial_separado_do_total():
    perfil = {
        "nome_completo": "Fulano",
        "registros": [{"tipo": "CRECI", "numero": "1"}],
        "assinatura_visual_b64": "x",
        "telefone": "99999",
        "cidade": "Açailândia", "uf": "MA",
    }
    r = calcular(**_ctx(perfil=perfil))
    assert r["pct_essencial"] == 100, "todos os essenciais preenchidos"
    assert r["pct"] < 100, "ainda faltam complementares"
    assert r["faltando_essencial"] == []


def test_ordem_coloca_essenciais_primeiro():
    itens = calcular(**_ctx())["itens"]
    primeiro_nao_essencial = next(i for i, it in enumerate(itens) if not it["essencial"])
    ultimo_essencial = max(i for i, it in enumerate(itens) if it["essencial"])
    assert ultimo_essencial < primeiro_nao_essencial
