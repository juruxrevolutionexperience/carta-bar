"""QR del restaurante: direccion y texto de la hoja imprimible.
GET/PUT /admin/api/qr*, GET /superadmin/api/restaurantes/{id}/qr."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import (
    COOKIE_SESION,
    COOKIE_SESION_SUPERADMIN,
    RESTAURANTE_ID,
    TEXTO_QR_POR_DEFECTO,
    TOKEN_SUPERADMIN,
    _url_publica,
    app,
)


@pytest.fixture
def texto_guardado() -> dict[str, str]:
    return {}


@pytest.fixture
def _datos(monkeypatch: pytest.MonkeyPatch, texto_guardado: dict[str, str]) -> None:
    monkeypatch.setattr(
        "carta_bar.api.cargar_config", lambda rid: {"nombre": f"Bar {rid}", "logo": ""}
    )
    monkeypatch.setattr("carta_bar.api.obtener_texto_qr", lambda rid: texto_guardado.get(rid, ""))

    def _guardar(rid: str, texto: str) -> bool:
        texto_guardado[rid] = texto
        return rid != "no-existe"

    monkeypatch.setattr("carta_bar.api.guardar_texto_qr", _guardar)
    monkeypatch.setattr("carta_bar.api._restaurante_existe", lambda rid: rid != "no-existe")


@pytest.fixture
def gerente(_datos: None) -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


@pytest.fixture
def superadmin(_datos: None) -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION_SUPERADMIN, auth.crear_token_sesion(TOKEN_SUPERADMIN))
    return c


# ------------------------------------------------------------ direccion


def test_la_catedral_conserva_su_direccion_historica() -> None:
    assert _url_publica("la-catedral") == "https://cartia.jurux.app"


def test_los_demas_bares_usan_su_id_como_subdominio() -> None:
    assert _url_publica("bar-pepe") == "https://bar-pepe.jurux.app"


# ------------------------------------------------------------ gerente


def test_sin_sesion_se_rechaza(_datos: None) -> None:
    sin = TestClient(app)
    assert sin.get("/admin/api/qr").status_code == 401
    assert sin.put("/admin/api/qr-texto", json={"texto": "x"}).status_code == 401


def test_devuelve_url_nombre_y_texto_por_defecto(gerente: TestClient) -> None:
    datos = gerente.get("/admin/api/qr").json()
    assert datos == {
        "url": _url_publica(RESTAURANTE_ID),
        "nombre": f"Bar {RESTAURANTE_ID}",
        "texto": TEXTO_QR_POR_DEFECTO,
    }


def test_el_texto_guardado_sustituye_al_de_por_defecto(gerente: TestClient) -> None:
    r = gerente.put("/admin/api/qr-texto", json={"texto": "  Mira  la carta "})
    assert r.status_code == 204
    assert gerente.get("/admin/api/qr").json()["texto"] == "Mira la carta"


def test_texto_vacio_vuelve_al_de_por_defecto(gerente: TestClient) -> None:
    gerente.put("/admin/api/qr-texto", json={"texto": "Otro"})
    assert gerente.put("/admin/api/qr-texto", json={"texto": "   "}).status_code == 204
    assert gerente.get("/admin/api/qr").json()["texto"] == TEXTO_QR_POR_DEFECTO


def test_texto_demasiado_largo_se_rechaza(gerente: TestClient) -> None:
    assert gerente.put("/admin/api/qr-texto", json={"texto": "x" * 121}).status_code == 422


# ------------------------------------------------------------ superadmin


def test_superadmin_exige_sesion(_datos: None) -> None:
    assert TestClient(app).get("/superadmin/api/restaurantes/bar-pepe/qr").status_code == 401


def test_el_gerente_no_entra_al_qr_del_superadmin(gerente: TestClient) -> None:
    assert gerente.get("/superadmin/api/restaurantes/bar-pepe/qr").status_code == 401


def test_superadmin_ve_el_qr_de_cualquier_restaurante(
    superadmin: TestClient, texto_guardado: dict[str, str]
) -> None:
    texto_guardado["bar-pepe"] = "Carta aquí"
    datos = superadmin.get("/superadmin/api/restaurantes/bar-pepe/qr").json()
    assert datos == {
        "url": "https://bar-pepe.jurux.app",
        "nombre": "Bar bar-pepe",
        "texto": "Carta aquí",
    }


def test_superadmin_restaurante_inexistente_o_id_raro_da_404(superadmin: TestClient) -> None:
    assert superadmin.get("/superadmin/api/restaurantes/no-existe/qr").status_code == 404
    assert superadmin.get("/superadmin/api/restaurantes/MAL%20ID/qr").status_code == 404
