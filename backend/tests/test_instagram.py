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
