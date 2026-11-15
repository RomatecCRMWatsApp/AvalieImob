import pytest
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from services.media_range import interpretar_range, resposta_midia, eh_midia


def test_interpretar_range_casos():
    assert interpretar_range(None, 100) is None
    assert interpretar_range("bytes=0-", 100) == (0, 99)
    assert interpretar_range("bytes=0-1", 100) == (0, 1)
    assert interpretar_range("bytes=50-500", 100) == (50, 99)
    assert interpretar_range("bytes=-10", 100) == (90, 99)
    assert interpretar_range("bytes=0-1,5-6", 100) is None
    assert interpretar_range("lixo", 100) is None
    with pytest.raises(ValueError):
        interpretar_range("bytes=100-", 100)


def test_eh_midia():
    assert eh_midia("video/apresentacoes/a.MP4")
    assert not eh_midia("static/js/main.js")


def test_resposta_206_e_416(tmp_path):
    f = tmp_path / "v.mp4"
    dados = bytes(range(256)) * 40
    f.write_bytes(dados)

    async def ep(request):
        return resposta_midia(str(f), request.headers.get("range"))

    c = TestClient(Starlette(routes=[Route("/v.mp4", ep)]))
    r = c.get("/v.mp4")
    assert r.status_code == 200 and r.headers["accept-ranges"] == "bytes" and r.content == dados
    r = c.get("/v.mp4", headers={"Range": "bytes=0-1"})
    assert r.status_code == 206 and r.content == dados[:2]
    assert r.headers["content-range"] == f"bytes 0-1/{len(dados)}"
    r = c.get("/v.mp4", headers={"Range": "bytes=1000-"})
    assert r.status_code == 206 and r.content == dados[1000:]
    r = c.get("/v.mp4", headers={"Range": f"bytes={len(dados)}-"})
    assert r.status_code == 416
