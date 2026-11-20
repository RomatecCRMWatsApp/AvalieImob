# @module services.privacidade.documentos — Versão/hash dos Termos e do Aviso de Privacidade.
#
# Os textos são arquivos Markdown. A VERSÃO aceita é a 1ª linha "versao: X" do arquivo
# e o HASH é o SHA-256 do conteúdo exato servido. O aceite do usuário grava os dois,
# então dá para provar QUAL texto foi aceito (sem depender de memória do sistema).
#
# Diretórios procurados (o 1º que tiver o arquivo vence):
#   1. PRIVACIDADE_DOCS_DIR (env) — usar em produção com o texto APROVADO;
#   2. backend/data/privacidade/;
#   3. docs/privacidade/minutas/ (repositório — MINUTAS para revisão jurídica).
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional

TIPOS = {
    "termos": "termos-de-uso.md",
    "privacidade": "aviso-de-privacidade.md",
}

_BACKEND = Path(__file__).resolve().parents[2]
_REPO = _BACKEND.parent


def _diretorios():
    env = (os.getenv("PRIVACIDADE_DOCS_DIR", "") or "").strip()
    if env:
        yield Path(env)
    yield _BACKEND / "data" / "privacidade"
    yield _REPO / "docs" / "privacidade" / "minutas"


def carregar(tipo: str) -> Optional[Dict[str, str]]:
    """Devolve {tipo, versao, hash, texto, minuta} ou None se não houver arquivo."""
    nome = TIPOS.get(tipo)
    if not nome:
        return None
    for d in _diretorios():
        p = d / nome
        if p.is_file():
            texto = p.read_text(encoding="utf-8")
            versao = "sem-versao"
            for linha in texto.splitlines()[:10]:
                if linha.lower().startswith("versao:"):
                    versao = linha.split(":", 1)[1].strip() or versao
                    break
            return {
                "tipo": tipo,
                "versao": versao,
                "hash": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
                "texto": texto,
                "minuta": "MINUTA" in texto.upper()[:2000],
            }
    return None
