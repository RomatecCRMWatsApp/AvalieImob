# @module tests.test_release_notes — aviso automático "sistema atualizado".
#
# Regra do dono (23/08/2026): o aviso é do USUÁRIO. Item de painel administrativo
# (`publico: "interno"`) fica registrado no arquivo mas NÃO vira aviso.
import asyncio
import io
import json

import pytest

from services import release_notes as RN
from tests.test_trial_acesso import _Coll


class _DB:
    def __init__(self):
        self.novidades = _Coll()
        self.novidades_visualizacoes = _Coll()
        self.users = _Coll()

    def __getitem__(self, nome):
        return getattr(self, nome)


def run(coro):
    return asyncio.run(coro)


def _release(**kw):
    base = {
        "versao": "1.4.1440", "build": 1440, "data": "2026-08-23T20:04:00-03:00",
        "titulo": "", "itens": [
            {"modulo": "Tratamento Científico", "tipo": "novo",
             "texto": "Inferência estatística.", "rota": "/dashboard/inferencia"},
            {"modulo": "Mapa do ONR", "tipo": "correcao", "texto": "Satélite cinza."},
        ]}
    base.update(kw)
    return base


def _arquivo(tmp_path, releases):
    p = tmp_path / "releases.json"
    io.open(p, "w", encoding="utf-8").write(json.dumps({"releases": releases}))
    return p


# ── Filtro de público: o coração da regra ────────────────────────────────────
def test_item_interno_nao_vira_aviso():
    r = _release(itens=[
        {"modulo": "PTAM", "tipo": "melhoria", "texto": "x", "publico": "usuario"},
        {"modulo": "Painel de Cupons", "tipo": "novo", "texto": "y", "publico": "interno"},
    ])
    assert [i["modulo"] for i in RN.itens_do_usuario(r)] == ["PTAM"]


def test_item_sem_publico_e_do_usuario_por_padrao():
    r = _release(itens=[{"modulo": "PTAM", "tipo": "novo", "texto": "x"}])
    assert len(RN.itens_do_usuario(r)) == 1


def test_release_so_com_item_interno_nao_gera_aviso():
    r = _release(itens=[{"modulo": "Prospecção", "tipo": "novo", "texto": "x",
                         "publico": "interno"}])
    assert RN.montar_novidade(r) == {}


def test_item_sem_modulo_e_descartado():
    r = _release(itens=[{"modulo": "", "tipo": "novo", "texto": "x"}])
    assert RN.montar_novidade(r) == {}


# ── Conteúdo do aviso ────────────────────────────────────────────────────────
def test_aviso_traz_versao_data_br_e_ferramentas():
    doc = RN.montar_novidade(_release())
    assert doc["slug"] == "release-1.4.1440"
    assert doc["versao"] == "1.4.1440"
    assert doc["atualizado_em_br"] == "23/08/2026 às 20:04"
    assert "23/08/2026" in doc["resumo"]
    assert [i["modulo"] for i in doc["itens"]] == ["Tratamento Científico", "Mapa do ONR"]


def test_titulo_automatico_conta_as_ferramentas():
    assert RN.montar_novidade(_release())["titulo"] == "2 ferramentas atualizadas"
    um = _release(itens=[{"modulo": "PTAM", "tipo": "novo", "texto": "x"}])
    assert RN.montar_novidade(um)["titulo"] == "1 ferramenta atualizada"


def test_titulo_do_arquivo_prevalece():
    doc = RN.montar_novidade(_release(titulo="Semana da topografia"))
    assert doc["titulo"] == "Semana da topografia"


def test_tag_segue_o_item_mais_forte():
    assert RN.montar_novidade(_release())["tag"] == "novidade"       # novo + correção
    so_fix = _release(itens=[{"modulo": "Mapa", "tipo": "correcao", "texto": "x"}])
    assert RN.montar_novidade(so_fix)["tag"] == "correcao"
    melhoria = _release(itens=[{"modulo": "PTAM", "tipo": "melhoria", "texto": "x"}])
    assert RN.montar_novidade(melhoria)["tag"] == "melhoria"


def test_bloqueia_em_novidade_mas_nao_em_correcao_pequena():
    assert RN.montar_novidade(_release())["bloqueante"] is True
    so_fix = _release(itens=[{"modulo": "Mapa", "tipo": "correcao", "texto": "x"}])
    assert RN.montar_novidade(so_fix)["bloqueante"] is False


def test_cta_aponta_para_a_primeira_ferramenta_com_rota():
    doc = RN.montar_novidade(_release())
    assert doc["cta_rota"] == "/dashboard/inferencia"
    sem_rota = _release(itens=[{"modulo": "Mapa", "tipo": "correcao", "texto": "x"}])
    assert RN.montar_novidade(sem_rota)["cta_rota"] is None


def test_markdown_de_fallback_lista_as_ferramentas():
    md = RN.montar_novidade(_release())["conteudo_md"]
    assert "**Tratamento Científico**" in md and "Correção" in md


# ── Sincronização (o que roda no startup) ────────────────────────────────────
def test_sincronizar_publica_o_aviso(tmp_path):
    db = _DB()
    res = run(RN.sincronizar(db, _arquivo(tmp_path, [_release()])))
    assert res["criadas"] == ["release-1.4.1440"]
    doc = run(db.novidades.find_one({"slug": "release-1.4.1440"}))
    assert doc["publicada"] is True and doc["publicada_em"]
    assert doc["automatica"] is True
    assert len(doc["itens"]) == 2


def test_sincronizar_e_idempotente(tmp_path):
    db = _DB()
    arq = _arquivo(tmp_path, [_release()])
    run(RN.sincronizar(db, arq))
    res = run(RN.sincronizar(db, arq))          # segundo boot do mesmo build
    assert res["criadas"] == []
    assert len(db.novidades.docs) == 1


def test_sincronizar_publica_apenas_a_release_nova(tmp_path):
    db = _DB()
    run(RN.sincronizar(db, _arquivo(tmp_path, [_release()])))
    nova = _release(versao="1.4.1441", data="2026-08-24T09:00:00-03:00")
    res = run(RN.sincronizar(db, _arquivo(tmp_path, [nova, _release()])))
    assert res["criadas"] == ["release-1.4.1441"]
    assert len(db.novidades.docs) == 2


def test_release_interna_nao_cria_nada(tmp_path):
    db = _DB()
    interna = _release(itens=[{"modulo": "Painel de Leads", "tipo": "melhoria",
                               "texto": "x", "publico": "interno"}])
    res = run(RN.sincronizar(db, _arquivo(tmp_path, [interna])))
    assert res["criadas"] == [] and res["sem_itens_de_usuario"] == 1
    assert db.novidades.docs == []


def test_arquivo_ausente_nao_quebra_o_boot(tmp_path):
    db = _DB()
    res = run(RN.sincronizar(db, tmp_path / "nao_existe.json"))
    assert res["criadas"] == []


def test_arquivo_corrompido_nao_quebra_o_boot(tmp_path):
    p = tmp_path / "releases.json"
    io.open(p, "w", encoding="utf-8").write("{ isso não é json ]")
    assert RN.carregar(p) == []


# ── O arquivo REAL do repositório precisa estar íntegro ──────────────────────
def test_arquivo_do_repositorio_e_valido():
    releases = RN.carregar()
    assert releases, "backend/data/releases.json vazio — todo release precisa de nota"
    for r in releases:
        assert r.get("versao"), "release sem versão"
        assert r.get("data"), f"release {r.get('versao')} sem data/hora"
        for item in (r.get("itens") or []):
            assert item.get("modulo"), f"item sem módulo em {r.get('versao')}"
            assert item.get("tipo") in ("novo", "melhoria", "correcao"), \
                f"tipo inválido em {r.get('versao')}: {item.get('tipo')}"
            assert str(item.get("publico") or "usuario") in ("usuario", "interno")
        doc = RN.montar_novidade(r)
        if doc:
            assert doc["atualizado_em_br"], f"data ilegível em {r.get('versao')}"


# ── Ponta a ponta: do arquivo até o que o popup recebe ───────────────────────
def test_usuario_recebe_o_aviso_com_itens_versao_e_horario(tmp_path):
    """O modal lê de listar_pendentes — os campos do layout têm de chegar lá."""
    from services import novidades as NOV
    db = _DB()
    run(RN.sincronizar(db, _arquivo(tmp_path, [_release()])))

    pendentes = run(NOV.listar_pendentes(db, "u1"))
    assert len(pendentes) == 1
    aviso = pendentes[0]
    assert aviso["automatica"] is True
    assert aviso["versao"] == "1.4.1440"
    assert aviso["atualizado_em_br"] == "23/08/2026 às 20:04"
    assert [i["modulo"] for i in aviso["itens"]] == ["Tratamento Científico", "Mapa do ONR"]
    assert aviso["itens"][0]["tipo"] == "novo"
    assert aviso["bloqueante"] is True


def test_quem_dispensou_nao_ve_de_novo(tmp_path):
    from services import novidades as NOV
    db = _DB()
    run(RN.sincronizar(db, _arquivo(tmp_path, [_release()])))
    aviso = run(NOV.listar_pendentes(db, "u1"))[0]
    run(NOV.dispensar(db, "u1", aviso["id"]))
    assert run(NOV.listar_pendentes(db, "u1")) == []
    # ...e um novo boot do MESMO build não ressuscita o aviso
    run(RN.sincronizar(db, _arquivo(tmp_path, [_release()])))
    assert run(NOV.listar_pendentes(db, "u1")) == []


# ── Versão exibida acompanha o badge (o bot do CI bumpa depois do commit) ────
def test_versao_do_aviso_segue_o_build_publicado(monkeypatch, tmp_path):
    vj = tmp_path / "version.json"
    io.open(vj, "w", encoding="utf-8").write('{"build":1441,"version":"v1.4.1441"}')
    monkeypatch.setattr(RN, "_VERSION_JSON", vj)
    doc = RN.montar_novidade(_release())          # declarado 1.4.1440 / build 1440
    assert doc["versao"] == "1.4.1441"            # bate com o badge
    assert doc["slug"] == "release-1.4.1440"      # slug pela declarada: idempotência


def test_nao_carimba_nota_antiga_com_a_versao_de_hoje(monkeypatch, tmp_path):
    vj = tmp_path / "version.json"
    io.open(vj, "w", encoding="utf-8").write('{"build":1500,"version":"v1.4.1500"}')
    monkeypatch.setattr(RN, "_VERSION_JSON", vj)
    antiga = _release(versao="1.4.1400", build=1400)
    assert RN.montar_novidade(antiga)["versao"] == "1.4.1400"


def test_sem_version_json_usa_a_declarada(monkeypatch, tmp_path):
    monkeypatch.setattr(RN, "_VERSION_JSON", tmp_path / "nao_existe.json")
    assert RN.montar_novidade(_release())["versao"] == "1.4.1440"


# ── Correção de conteúdo já publicado (acentuação, versão) ──────────────────
def test_corrige_conteudo_sem_reemitir_o_aviso(tmp_path):
    """Texto errado no arquivo é corrigido no aviso — sem reabrir para quem dispensou."""
    from services import novidades as NOV
    db = _DB()
    errado = _release(itens=[{"modulo": "Mapa do ONR", "tipo": "correcao",
                              "texto": "O satelite nao fica mais cinza."}])
    run(RN.sincronizar(db, _arquivo(tmp_path, [errado])))
    antes = run(db.novidades.find_one({"slug": "release-1.4.1440"}))
    publicada_em = antes["publicada_em"]

    certo = _release(itens=[{"modulo": "Mapa do ONR", "tipo": "correcao",
                             "texto": "O satélite não fica mais cinza."}])
    res = run(RN.sincronizar(db, _arquivo(tmp_path, [certo])))

    assert res["criadas"] == [] and res["atualizadas"] == ["release-1.4.1440"]
    depois = run(db.novidades.find_one({"slug": "release-1.4.1440"}))
    assert depois["itens"][0]["texto"] == "O satélite não fica mais cinza."
    assert depois["publicada_em"] == publicada_em          # não reemite
    assert len(db.novidades.docs) == 1


def test_correcao_de_conteudo_nao_ressuscita_para_quem_dispensou(tmp_path):
    from services import novidades as NOV
    db = _DB()
    run(RN.sincronizar(db, _arquivo(tmp_path, [_release()])))
    aviso = run(NOV.listar_pendentes(db, "u1"))[0]
    run(NOV.dispensar(db, "u1", aviso["id"]))

    corrigido = _release(titulo="Título corrigido")
    run(RN.sincronizar(db, _arquivo(tmp_path, [corrigido])))
    assert run(NOV.listar_pendentes(db, "u1")) == []


def test_sem_mudanca_no_arquivo_nao_atualiza_nada(tmp_path):
    db = _DB()
    arq = _arquivo(tmp_path, [_release()])
    run(RN.sincronizar(db, arq))
    res = run(RN.sincronizar(db, arq))
    assert res["criadas"] == [] and res["atualizadas"] == []


def test_textos_do_repositorio_estao_acentuados():
    """O texto vai direto para a tela do cliente — 'nao', 'voce', 'versao' não passam."""
    import re
    suspeitas = re.compile(
        r"\b(nao|voce|versao|horario|atualizacao|correcao|estatistica|diagnostico|"
        r"satelite|cientifico|inferencia|liberacao|informacoes|apos|relatorio|"
        r"usuario|proprio|codigo|imovel|avaliacao)\b", re.I)   # "poligonal" é sem acento
    for r in RN.carregar():
        for item in RN.itens_do_usuario(r):
            for campo in ("modulo", "texto"):
                achado = suspeitas.search(str(item.get(campo) or ""))
                assert not achado, (
                    f"'{achado.group(0)}' sem acento em {r.get('versao')} → "
                    f"{item.get('modulo')} ({campo})")
        achado = suspeitas.search(str(r.get("titulo") or ""))
        assert not achado, f"título de {r.get('versao')} sem acento: {achado.group(0)}"
