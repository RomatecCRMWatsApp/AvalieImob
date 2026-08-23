# @module services.release_notes — o aviso "sistema atualizado" nasce sozinho a cada deploy.
#
# Fonte da verdade: backend/data/releases.json, versionado junto com o código.
# No startup, `sincronizar()` lê o arquivo e publica na Central de Novidades
# (coleção `novidades`) — idempotente por slug, então subir o mesmo build de novo
# não duplica nem reabre o aviso para quem já dispensou.
#
# REGRA DE PÚBLICO (decisão do dono, 23/08/2026): o aviso é para o USUÁRIO da
# plataforma. Item marcado `publico: "interno"` — painel administrativo (cupons,
# prospecção, leads, acessos de teste, NFS-e…) — fica registrado no arquivo mas
# NÃO vira aviso para ninguém.
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("romatec")

ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "releases.json"
PREFIXO_SLUG = "release-"
_FUSO_BR = timezone(timedelta(hours=-3))

# Ordem de prioridade da tag do aviso (a mais "forte" da lista manda).
_PESO_TIPO = {"novo": 3, "melhoria": 2, "correcao": 1}
_TAG_POR_TIPO = {"novo": "novidade", "melhoria": "melhoria", "correcao": "correcao"}
_ROTULO_TIPO = {"novo": "Novo", "melhoria": "Melhoria", "correcao": "Correção"}

# Bloqueia (exige clique) quando há novidade ou melhoria; correção pequena não trava.
_TIPOS_BLOQUEANTES = {"novo", "melhoria"}


def carregar(caminho: Path = None) -> list:
    """Lê o arquivo de releases. Sem arquivo (ou arquivo quebrado) → lista vazia."""
    caminho = caminho or ARQUIVO
    try:
        with open(caminho, encoding="utf-8") as fh:
            dados = json.load(fh)
        return list(dados.get("releases") or [])
    except FileNotFoundError:
        logger.warning("release_notes: %s não encontrado — sem avisos automáticos.", caminho)
        return []
    except (json.JSONDecodeError, OSError) as e:
        logger.error("release_notes: falha ao ler %s: %s", caminho, e)
        return []


def itens_do_usuario(release: dict) -> list:
    """Só o que interessa a quem USA a plataforma — administrativo fica de fora."""
    return [i for i in (release.get("itens") or [])
            if str(i.get("publico") or "usuario").lower() != "interno"
            and str(i.get("modulo") or "").strip()]


def _data_br(iso: str) -> str:
    """'2026-08-23T20:04:00-03:00' → '23/08/2026 às 20:04'."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    if dt.tzinfo is not None:
        dt = dt.astimezone(_FUSO_BR)
    return dt.strftime("%d/%m/%Y às %H:%M")


_VERSION_JSON = (Path(__file__).resolve().parent.parent.parent
                 / "frontend" / "build" / "version.json")


def versao_exibida(release: dict) -> str:
    """Versão que aparece no aviso — a MESMA do badge do rodapé.

    O bot do CI incrementa o `build-number` depois do commit, então o número que
    declaro no arquivo pode ficar 1 atrás do que foi ao ar. Se o build publicado
    (`frontend/build/version.json`) for do mesmo release e estiver à frente, ele
    manda — assim o popup e o badge nunca divergem.
    """
    declarada = str(release.get("versao") or "").strip()
    try:
        with open(_VERSION_JSON, encoding="utf-8") as fh:
            publicada = json.load(fh)
        build_real = int(publicada.get("build") or 0)
        v_real = str(publicada.get("version") or "").lstrip("vV")
        build_decl = int(release.get("build") or 0)
        # Só substitui dentro do mesmo release (bot bumpando 1-2 números), nunca
        # carimba uma nota antiga com a versão de hoje.
        if v_real and build_decl and 0 <= build_real - build_decl <= 3:
            return v_real
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        pass
    return declarada


def _titulo(release: dict, itens: list) -> str:
    if release.get("titulo"):
        return str(release["titulo"])
    n = len(itens)
    return "1 ferramenta atualizada" if n == 1 else f"{n} ferramentas atualizadas"


def _tag(itens: list) -> str:
    forte = max(itens, key=lambda i: _PESO_TIPO.get(i.get("tipo"), 0), default=None)
    return _TAG_POR_TIPO.get((forte or {}).get("tipo"), "novidade")


def _markdown(itens: list) -> str:
    """Fallback textual: o modal novo usa `itens`; o histórico/e-mail usa isto."""
    linhas = []
    for i in itens:
        rotulo = _ROTULO_TIPO.get(i.get("tipo"), "Atualização")
        linhas.append(f"**{i['modulo']}** — {rotulo}\n\n{i.get('texto') or ''}")
    return "\n\n".join(linhas)


def montar_novidade(release: dict) -> dict:
    """Converte uma entrada do arquivo no documento da Central de Novidades.

    Devolve {} quando a release não tem nada que interesse ao usuário.
    """
    itens = itens_do_usuario(release)
    if not itens:
        return {}
    versao = versao_exibida(release)
    quando = _data_br(release.get("data"))
    com_rota = next((i for i in itens if i.get("rota")), None)

    declarada = str(release.get("versao") or release.get("build") or "").strip()
    return {
        "slug": f"{PREFIXO_SLUG}{declarada}",
        "versao": versao,
        "titulo": _titulo(release, itens),
        "resumo": f"Sistema atualizado em {quando}." if quando else "Sistema atualizado.",
        "conteudo_md": _markdown(itens),
        "itens": [{"modulo": i["modulo"], "tipo": i.get("tipo") or "melhoria",
                   "texto": i.get("texto") or "", "rota": i.get("rota")} for i in itens],
        "atualizado_em_br": quando,
        "tag": _tag(itens),
        "bloqueante": any(i.get("tipo") in _TIPOS_BLOQUEANTES for i in itens),
        "publico_alvo": "todos",
        "cta_label": "Abrir a ferramenta" if com_rota else None,
        "cta_rota": (com_rota or {}).get("rota"),
        "automatica": True,
    }


async def sincronizar(db, caminho: Path = None) -> dict:
    """Publica os avisos das releases ainda não anunciadas. Idempotente por slug.

    Chamado no startup do servidor — é o que faz o aviso nascer sozinho.
    """
    from services import novidades as NOV

    criadas, ignoradas = [], 0
    for release in carregar(caminho):
        doc = montar_novidade(release)
        if not doc:
            ignoradas += 1           # release só com item interno: nada a anunciar
            continue
        try:
            if await db[NOV.C_NOV].find_one({"slug": doc["slug"]}):
                continue             # já anunciada — não reabre para quem dispensou
            novo = await NOV.criar(db, doc)
            # Aviso automático nasce PUBLICADO: o deploy é o ato de publicação.
            await db[NOV.C_NOV].update_one(
                {"id": novo["id"]},
                {"$set": {"publicada": True, "publicada_em": datetime.utcnow(),
                          "itens": doc["itens"], "atualizado_em_br": doc["atualizado_em_br"],
                          "automatica": True}})
            criadas.append(doc["slug"])
        except ValueError as e:       # slug duplicado numa corrida entre workers
            logger.info("release_notes: %s já existia (%s)", doc["slug"], e)
        except Exception as e:        # noqa: BLE001 — aviso nunca derruba o boot
            logger.error("release_notes: falha ao publicar %s: %s", doc.get("slug"), e)
    if criadas:
        logger.info("release_notes: avisos publicados: %s", ", ".join(criadas))
    return {"criadas": criadas, "sem_itens_de_usuario": ignoradas}
