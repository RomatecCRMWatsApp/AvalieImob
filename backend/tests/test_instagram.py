import asyncio
import pytest

from models.instagram_post import InstagramPost, InstagramPostCreate


def test_modelo_defaults():
    p = InstagramPost(user_id="u1")
    assert p.id and isinstance(p.id, str)
    assert p.user_id == "u1"
    assert p.status == "ideia"
    assert p.pilar == "recursos"
    assert p.formato == "post_unico"
    assert p.hashtags == []
    assert p.slides == []
    assert p.criado_em and p.atualizado_em


def test_create_para_dict():
    c = InstagramPostCreate(pilar="quanto_vale", formato="carrossel", titulo="X")
    d = c.dict()
    assert d["pilar"] == "quanto_vale"
    assert d["formato"] == "carrossel"


import services.instagram_ia_service as IA


def test_gerar_conteudo_monta_saida(monkeypatch):
    async def fake_cascata(messages, max_tokens=2000):
        return ('{"titulo":"Quanto vale seu imovel?","legenda":"Descubra agora. Siga @avalieimob",'
                '"hashtags":["#imovel","#avaliacao"],"slides":[],"roteiro":"","cta":"Acesse a calculadora"}')
    monkeypatch.setattr(IA, "_roma_ia_cascata", fake_cascata)
    out = asyncio.run(IA.gerar_conteudo("quanto_vale", "valor de mercado", "post_unico"))
    assert out["titulo"] == "Quanto vale seu imovel?"
    assert out["link"] == "/quanto-vale-meu-imovel"
    assert "@avalieimob" in out["legenda"]
    assert out["pilar"] == "quanto_vale"


def test_gerar_conteudo_pilar_invalido():
    with pytest.raises(Exception):
        asyncio.run(IA.gerar_conteudo("xxx", "a", "post_unico"))


def test_gerar_conteudo_json_ruim_erro(monkeypatch):
    async def fake_cascata(messages, max_tokens=2000):
        return "isso nao e json"
    monkeypatch.setattr(IA, "_roma_ia_cascata", fake_cascata)
    with pytest.raises(Exception):
        asyncio.run(IA.gerar_conteudo("recursos", "a", "post_unico"))
