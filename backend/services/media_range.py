"""Entrega de mídia (vídeo/áudio) com suporte a pedidos de intervalo (HTTP Range).

O FastAPI 0.110 / Starlette 0.37 do projeto responde 200 com o arquivo inteiro a
qualquer pedido, ignorando o cabeçalho ``Range``. O Safari (iPhone/iPad) exige 206
para tocar ``<video>`` e todos os navegadores precisam dele para pular para um ponto
do vídeo antes de baixá-lo inteiro (capítulos da demonstração).

``interpretar_range`` é PURA (testável). ``resposta_midia`` monta a resposta:
sem ``Range`` válido → 200 com o arquivo todo e ``Accept-Ranges: bytes``;
com ``Range`` válido → 206 com ``Content-Range``; fora do arquivo → 416.
"""
from __future__ import annotations

import os
import re
from typing import Iterator, Optional, Tuple

from starlette.responses import FileResponse, Response, StreamingResponse

EXTENSOES_MIDIA = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
}
_CHUNK = 256 * 1024
_RE_RANGE = re.compile(r"^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*$", re.I)


def eh_midia(nome: str) -> bool:
    return os.path.splitext(nome.lower())[1] in EXTENSOES_MIDIA


def interpretar_range(cabecalho: Optional[str], tamanho: int) -> Optional[Tuple[int, int]]:
    """Devolve (inicio, fim) inclusivos, ``None`` sem pedido de intervalo utilizável
    (vale o arquivo inteiro) ou levanta ``ValueError`` se o intervalo é insatisfazível.

    Só um intervalo por pedido (o que os players fazem); listas com vírgula caem no
    arquivo inteiro, que é uma resposta válida pela RFC 9110.
    """
    if not cabecalho or tamanho <= 0:
        return None
    if "," in cabecalho:
        return None
    m = _RE_RANGE.match(cabecalho)
    if not m:
        return None
    ini_s, fim_s = m.group(1), m.group(2)
    if ini_s == "" and fim_s == "":
        return None
    if ini_s == "":  # sufixo: últimos N bytes
        n = int(fim_s)
        if n <= 0:
            raise ValueError("intervalo vazio")
        return max(0, tamanho - n), tamanho - 1
    ini = int(ini_s)
    if ini >= tamanho:
        raise ValueError("início além do fim do arquivo")
    fim = int(fim_s) if fim_s else tamanho - 1
    if fim < ini:
        return None
    return ini, min(fim, tamanho - 1)


def _ler(caminho: str, ini: int, fim: int) -> Iterator[bytes]:
    with open(caminho, "rb") as f:
        f.seek(ini)
        resta = fim - ini + 1
        while resta > 0:
            bloco = f.read(min(_CHUNK, resta))
            if not bloco:
                break
            resta -= len(bloco)
            yield bloco


def resposta_midia(caminho: str, cabecalho_range: Optional[str]) -> Response:
    tipo = EXTENSOES_MIDIA.get(os.path.splitext(caminho.lower())[1], "application/octet-stream")
    tamanho = os.path.getsize(caminho)
    try:
        intervalo = interpretar_range(cabecalho_range, tamanho)
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{tamanho}",
                                                  "Accept-Ranges": "bytes"})
    if intervalo is None:
        return FileResponse(caminho, media_type=tipo, headers={"Accept-Ranges": "bytes"})
    ini, fim = intervalo
    return StreamingResponse(
        _ler(caminho, ini, fim),
        status_code=206,
        media_type=tipo,
        headers={
            "Content-Range": f"bytes {ini}-{fim}/{tamanho}",
            "Content-Length": str(fim - ini + 1),
            "Accept-Ranges": "bytes",
        },
    )
