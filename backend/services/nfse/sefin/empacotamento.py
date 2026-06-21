# @module services.nfse.sefin.empacotamento — GZip + Base64 do XML (exigência Sefin/ADN).
from __future__ import annotations

import base64
import gzip


def gzip_base64(xml: str | bytes) -> str:
    """Comprime (GZip) e codifica (Base64) o XML — formato de transporte da Sefin."""
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    return base64.b64encode(gzip.compress(raw)).decode("ascii")


def base64_gunzip(payload: str) -> bytes:
    """Inverso de gzip_base64 (uso em testes/consulta)."""
    return gzip.decompress(base64.b64decode(payload))
