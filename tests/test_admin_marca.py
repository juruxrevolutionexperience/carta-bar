"""Marca del restaurante desde el panel: nombre, logo y portada.
PUT /admin/api/marca, POST/DELETE /admin/api/marca/{logo|portada}."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app

JPEG_VALIDO = b"\xff\xd8\xff" + b"\x00" * 100
ARCHIVO = {"foto": ("f.jpg", JPEG_VALIDO, "image/jpeg")}


@pytest.fixture
def guardado() -> dict[str, object]:
    return {}


@pytest.fixture
def cliente(tmp_path, monkeypatch: pytest.MonkeyPatch, guardado: dict[str, object]) -> TestClient:
    monkeypatch.setattr("carta_bar.api.DIR_FOTOS", tmp_path)

    def _nombre(restaurante_id: str, nombre: str) -> bool:
        guardado["nombre"] = (restaurante_id, nombre)
        return True

    def _imagen(restaurante_id: str, campo: str, url: str) -> bool:
        guardado["imagen"] = (restaurante_id, campo, url)
        return True

    monkeypatch.setattr("carta_bar.api.actualizar_nombre_restaurante", _nombre)
    monkeypatch.setattr("carta_bar.api.actualizar_imagen_marca", _imagen)
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


# ---------------------------------------------------------------- sesion


def test_todo_exige_sesion() -> None:
    sin = TestClient(app)
    assert sin.put("/admin/api/marca", json={"nombre": "X"}).status_code == 401
    assert sin.post("/admin/api/marca/logo", files=ARCHIVO).status_code == 401
    assert sin.delete("/admin/api/marca/portada").status_code == 401


# ---------------------------------------------------------------- nombre


def test_cambia_el_nombre(cliente: TestClient, guardado: dict[str, object]) -> None:
    r = cliente.put("/admin/api/marca", json={"nombre": "  La   Catedral  "})
    assert r.status_code == 204
    assert guardado["nombre"] == (RESTAURANTE_ID, "La Catedral")


def test_nombre_vacio_o_solo_espacios_se_rechaza(cliente: TestClient) -> None:
    for nombre in ("", "   "):
        assert cliente.put("/admin/api/marca", json={"nombre": nombre}).status_code == 422


def test_nombre_demasiado_largo_se_rechaza(cliente: TestClient) -> None:
    assert cliente.put("/admin/api/marca", json={"nombre": "x" * 81}).status_code == 422


# ---------------------------------------------------------------- imagenes


@pytest.mark.parametrize(
    ("tipo", "campo", "archivo"),
    [("logo", "logo", "marca-logo"), ("portada", "foto_portada", "marca-portada")],
)
def test_sube_logo_y_portada(
    cliente: TestClient, guardado: dict[str, object], tmp_path, tipo: str, campo: str, archivo: str
) -> None:
    r = cliente.post(f"/admin/api/marca/{tipo}", files=ARCHIVO)
    assert r.status_code == 200
    url = r.json()["url"]
    assert url.startswith(f"/fotos/{RESTAURANTE_ID}/{archivo}.jpg?v=")
    assert guardado["imagen"] == (RESTAURANTE_ID, campo, url)
    assert (tmp_path / RESTAURANTE_ID / f"{archivo}.jpg").read_bytes() == JPEG_VALIDO


def test_la_imagen_subida_se_sirve_en_su_ruta_publica(cliente: TestClient) -> None:
    cliente.post("/admin/api/marca/logo", files=ARCHIVO)
    r = TestClient(app).get(f"/fotos/{RESTAURANTE_ID}/marca-logo.jpg")
    assert r.status_code == 200
    assert r.content == JPEG_VALIDO


def test_un_archivo_que_no_es_jpeg_se_rechaza(cliente: TestClient, tmp_path) -> None:
    r = cliente.post("/admin/api/marca/logo", files={"foto": ("f.jpg", b"texto", "image/jpeg")})
    assert r.status_code == 400
    assert not (tmp_path / RESTAURANTE_ID / "marca-logo.jpg").exists()


def test_una_imagen_demasiado_grande_se_rechaza(cliente: TestClient) -> None:
    grande = b"\xff\xd8\xff" + b"\x00" * (3 * 1024 * 1024)
    r = cliente.post("/admin/api/marca/portada", files={"foto": ("f.jpg", grande, "image/jpeg")})
    assert r.status_code == 413


def test_un_tipo_desconocido_da_422(cliente: TestClient) -> None:
    assert cliente.post("/admin/api/marca/banner", files=ARCHIVO).status_code == 422
    assert cliente.delete("/admin/api/marca/../x").status_code in (404, 405, 422)


def test_quitar_deja_el_campo_vacio_y_borra_el_archivo(
    cliente: TestClient, guardado: dict[str, object], tmp_path
) -> None:
    cliente.post("/admin/api/marca/portada", files=ARCHIVO)
    ruta = tmp_path / RESTAURANTE_ID / "marca-portada.jpg"
    assert ruta.exists()

    assert cliente.delete("/admin/api/marca/portada").status_code == 204
    assert guardado["imagen"] == (RESTAURANTE_ID, "foto_portada", "")
    assert not ruta.exists()
