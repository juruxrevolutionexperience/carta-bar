"""El limitador es la defensa del presupuesto: si se rompe, hay que enterarse."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from carta_bar.limites import ip_cliente, limite_superado


@pytest.fixture
def cliente() -> TestClient:
    """App minima con la misma clave y el mismo aviso que la real, sin LLM detras."""
    # Limitador nuevo por test: el global conserva limites de tests anteriores.
    limitador = Limiter(key_func=ip_cliente)
    app = FastAPI()
    app.state.limiter = limitador
    app.add_exception_handler(RateLimitExceeded, limite_superado)

    @app.post("/preguntar")
    @limitador.limit("3/minute")
    def preguntar(request: Request) -> dict[str, str]:
        return {"respuesta": "ok"}

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


def test_tras_el_proxy_inventarse_una_ip_no_da_cupo_nuevo(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("carta_bar.limites.CONFIAR_PROXY", True)
    # Mismo comensal real (lo que añade nginx al final), con otra IP falsa delante.
    for falsa in ("10.9.9.1", "10.9.9.2", "10.9.9.3"):
        cabecera = {"X-Forwarded-For": f"{falsa}, 203.0.113.7"}
        assert cliente.post("/preguntar", headers=cabecera).status_code == 200
    cabecera = {"X-Forwarded-For": "10.9.9.4, 203.0.113.7"}
    assert cliente.post("/preguntar", headers=cabecera).status_code == 429


def test_tras_el_proxy_cada_comensal_tiene_su_cupo(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("carta_bar.limites.CONFIAR_PROXY", True)
    for _ in range(3):
        cliente.post("/preguntar", headers={"X-Forwarded-For": "203.0.113.7"})
    otro = {"X-Forwarded-For": "198.51.100.4"}
    assert cliente.post("/preguntar", headers=otro).status_code == 200


def test_sin_proxy_la_cabecera_se_ignora(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("carta_bar.limites.CONFIAR_PROXY", False)
    for ip in ("203.0.113.1", "203.0.113.2", "203.0.113.3"):
        cliente.post("/preguntar", headers={"X-Forwarded-For": ip})
    otro = {"X-Forwarded-For": "198.51.100.4"}
    assert cliente.post("/preguntar", headers=otro).status_code == 429
