"""Las cabeceras se prueban en una app real: un middleware mal montado no
falla, simplemente no aplica, y eso no se nota hasta que te auditan.
"""

import re

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from carta_bar.seguridad import CabecerasSeguridad, politica_csp


def nonce_del_html(html: str) -> str:
    encontrado = re.search(r'nonce="([^"]+)"', html)
    assert encontrado is not None, "la pagina no lleva nonce"
    return encontrado.group(1)


@pytest.fixture
def cliente() -> TestClient:
    app = FastAPI()
    app.add_middleware(CabecerasSeguridad)

    @app.get("/")
    def inicio(request: Request) -> HTMLResponse:
        return HTMLResponse(f'<script nonce="{request.state.nonce}">1</script>')

    return TestClient(app)


def test_la_respuesta_lleva_todas_las_cabeceras() -> None:
    app = FastAPI()
    app.add_middleware(CabecerasSeguridad)

    @app.get("/x")
    def x() -> dict[str, str]:
        return {}

    r = TestClient(app).get("/x")
    for cabecera in [
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Strict-Transport-Security",
    ]:
        assert cabecera in r.headers, f"falta {cabecera}"


def test_el_nonce_cambia_en_cada_peticion(cliente: TestClient) -> None:
    # Un nonce fijo no sirve de nada: el atacante lo copiaria en su inyeccion.
    nonces = {nonce_del_html(cliente.get("/").text) for _ in range(5)}
    assert len(nonces) == 5


def test_el_nonce_del_html_coincide_con_el_de_la_cabecera(cliente: TestClient) -> None:
    r = cliente.get("/")
    del_html = nonce_del_html(r.text)
    assert f"'nonce-{del_html}'" in r.headers["Content-Security-Policy"]


def test_la_politica_no_permite_scripts_inline_sueltos() -> None:
    # Con 'unsafe-inline' en script-src, toda la defensa se cae.
    directiva = [d for d in politica_csp("abc").split("; ") if d.startswith("script-src")][0]
    assert "'unsafe-inline'" not in directiva
    assert "'nonce-abc'" in directiva


def test_la_politica_cierra_los_vectores_clasicos() -> None:
    politica = politica_csp("abc")
    assert "object-src 'none'" in politica  # sin plugins ni <object>
    assert "base-uri 'self'" in politica  # sin secuestro de <base>
    assert "frame-ancestors 'none'" in politica  # sin clickjacking


def test_el_microfono_sigue_permitido_para_el_dictado() -> None:
    app = FastAPI()
    app.add_middleware(CabecerasSeguridad)

    @app.get("/x")
    def x() -> dict[str, str]:
        return {}

    permisos = TestClient(app).get("/x").headers["Permissions-Policy"]
    assert "microphone=(self)" in permisos
    assert "camera=()" in permisos
