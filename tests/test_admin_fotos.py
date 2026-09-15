"""Subida de fotos de platos: POST/DELETE /admin/api/platos/{id}/foto,
GET /fotos/{restaurante}/{archivo}."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app

JPEG_VALIDO = b"\xff\xd8\xff" + b"\x00" * 100
NO_JPEG = b"esto no es una imagen"


@pytest.fixture
def guardado() -> dict[str, object]:
    return {}


@pytest.fixture
def cliente(
    tmp_path, monkeypatch: pytest.MonkeyPatch, guardado: dict[str, object]
) -> TestClient:
    monkeypatch.setattr("carta_bar.api.DIR_FOTOS", tmp_path)

    def _actualizar(restaurante_id: str, plato_id: str, foto: str | None) -> bool:
        guardado["restaurante_id"] = restaurante_id
        guardado["plato_id"] = plato_id
        guardado["foto"] = foto
        return plato_id != "no-existe"

    monkeypatch.setattr("carta_bar.api.actualizar_foto_plato", _actualizar)
    cliente = TestClient(app)
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return cliente


# ------------------------------------------------------------- subir foto


def test_subir_foto_sin_sesion_se_rechaza() -> None:
    r = TestClient(app).post(
        "/admin/api/platos/p001/foto", files={"foto": ("f.jpg", JPEG_VALIDO, "image/jpeg")}
    )
    assert r.status_code == 401


def test_sube_una_foto_valida(cliente: TestClient, guardado: dict[str, object]) -> None:
    r = cliente.post(
        "/admin/api/platos/p001/foto", files={"foto": ("f.jpg", JPEG_VALIDO, "image/jpeg")}
    )
    assert r.status_code == 200
    datos = r.json()
    assert datos["foto"].startswith("/fotos/" + RESTAURANTE_ID + "/p001.jpg?v=")
    assert guardado["plato_id"] == "p001"
    assert guardado["foto"] == datos["foto"]


def test_un_archivo_que_no_es_jpeg_se_rechaza(cliente: TestClient) -> None:
    r = cliente.post(
        "/admin/api/platos/p001/foto", files={"foto": ("f.jpg", NO_JPEG, "image/jpeg")}
    )
    assert r.status_code == 400


def test_un_archivo_demasiado_grande_se_rechaza(cliente: TestClient) -> None:
    grande = b"\xff\xd8\xff" + b"\x00" * (3 * 1024 * 1024 + 1)
    r = cliente.post(
        "/admin/api/platos/p001/foto", files={"foto": ("f.jpg", grande, "image/jpeg")}
    )
    assert r.status_code == 413


def test_subir_foto_a_un_plato_que_no_existe_da_404(cliente: TestClient) -> None:
    r = cliente.post(
        "/admin/api/platos/no-existe/foto", files={"foto": ("f.jpg", JPEG_VALIDO, "image/jpeg")}
    )
    assert r.status_code == 404


# ------------------------------------------------------------ quitar foto


def test_quitar_foto_sin_sesion_se_rechaza() -> None:
    r = TestClient(app).delete("/admin/api/platos/p001/foto")
    assert r.status_code == 401


def test_quita_una_foto(
    cliente: TestClient, guardado: dict[str, object], tmp_path
) -> None:
    ruta = tmp_path / RESTAURANTE_ID / "p001.jpg"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(JPEG_VALIDO)

    r = cliente.delete("/admin/api/platos/p001/foto")
    assert r.status_code == 204
    assert guardado["foto"] is None
    assert not ruta.exists()


def test_quitar_foto_de_un_plato_que_no_existe_da_404(cliente: TestClient) -> None:
    r = cliente.delete("/admin/api/platos/no-existe/foto")
    assert r.status_code == 404


# ---------------------------------------------------------- servir la foto


def test_sirve_una_foto_existente(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("carta_bar.api.DIR_FOTOS", tmp_path)
    ruta = tmp_path / "la-catedral" / "p001.jpg"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(JPEG_VALIDO)

    r = TestClient(app).get("/fotos/la-catedral/p001.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content == JPEG_VALIDO


def test_una_foto_que_no_existe_da_404(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("carta_bar.api.DIR_FOTOS", tmp_path)
    r = TestClient(app).get("/fotos/la-catedral/no-existe.jpg")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "archivo",
    ["../../etc/passwd", "p001.jpg.exe", "p001.png", "..%2f..%2fetc%2fpasswd", "p001"],
)
def test_nombres_de_archivo_invalidos_dan_404(archivo: str) -> None:
    r = TestClient(app).get(f"/fotos/la-catedral/{archivo}")
    assert r.status_code == 404
