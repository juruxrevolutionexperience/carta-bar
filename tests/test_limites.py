"""El limitador es la defensa del presupuesto: si se rompe, hay que enterarse."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from carta_bar.limites import limite_superado, limiter


@pytest.fixture
def cliente() -> TestClient:
    """App minima con el mismo limitador que la real, pero sin LLM detras."""
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, limite_superado)

    @app.post("/preguntar")
    @limiter.limit("3/minute")
    def preguntar(request: Request) -> dict[str, str]:
        return {"respuesta": "ok"}

    limiter.reset()
    return TestClient(app)


def test_deja_pasar_hasta_el_limite(cliente: TestClient) -> None:
    for _ in range(3):
        assert cliente.post("/preguntar").status_code == 200


def test_corta_al_superar_el_limite(cliente: TestClient) -> None:
    for _ in range(3):
        cliente.post("/preguntar")
    assert cliente.post("/preguntar").status_code == 429


def test_el_aviso_llega_en_el_formato_que_pinta_el_chat(cliente: TestClient) -> None:
    for _ in range(4):
        respuesta = cliente.post("/preguntar")
    assert respuesta.status_code == 429
    assert "respuesta" in respuesta.json()
    assert respuesta.headers["Retry-After"] == "60"
