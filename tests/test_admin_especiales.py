"""Fuera de carta: POST /admin/api/platos/especiales,
DELETE /admin/api/platos/especiales/{id}."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app
from carta_bar.modelos import Plato

ESPECIAL_VALIDO = {
    "nombre": "Arroz del día",
    "descripcion": "Con sepia y gambón",
    "precio": 14.5,
    "ingredientes": ["arroz", "sepia", "gambón"],
}


@pytest.fixture
def guardado() -> dict[str, object]:
    return {}


@pytest.fixture
def cliente(tmp_path, monkeypatch: pytest.MonkeyPatch, guardado: dict[str, object]) -> TestClient:
    monkeypatch.setattr("carta_bar.api.DIR_FOTOS", tmp_path)

    def _crear(
        restaurante_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[object],
        etiqueta: object | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato:
        guardado["restaurante_id"] = restaurante_id
        guardado["nombre"] = nombre
        guardado["descripcion"] = descripcion
        guardado["precio"] = precio
        guardado["ingredientes"] = ingredientes
        guardado["alergenos"] = alergenos
        guardado["etiqueta"] = etiqueta
        guardado["vegano"] = vegano
        guardado["vegetariano"] = vegetariano
        guardado["sin_gluten"] = sin_gluten
        guardado["sin_lactosa"] = sin_lactosa
        return Plato(
            id="especial-abc123",
            categoria="especial-de-hoy",
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            ingredientes=ingredientes,
            alergenos=alergenos,  # type: ignore[arg-type]
            vegano=vegano,
            vegetariano=vegetariano,
            sin_gluten=sin_gluten,
            sin_lactosa=sin_lactosa,
            disponible=True,
            etiqueta=etiqueta,  # type: ignore[arg-type]
            foto=None,
        )

    def _eliminar(restaurante_id: str, plato_id: str) -> bool:
        guardado["eliminado_restaurante_id"] = restaurante_id
        guardado["eliminado_plato_id"] = plato_id
        return plato_id != "no-existe"

    monkeypatch.setattr("carta_bar.api.crear_plato_especial", _crear)
    monkeypatch.setattr("carta_bar.api.eliminar_plato_especial", _eliminar)
    cliente = TestClient(app)
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return cliente


# ------------------------------------------------------------------ crear


def test_crear_especial_sin_sesion_se_rechaza() -> None:
    r = TestClient(app).post("/admin/api/platos/especiales", json=ESPECIAL_VALIDO)
    assert r.status_code == 401


def test_crea_un_especial_valido(cliente: TestClient, guardado: dict[str, object]) -> None:
    r = cliente.post("/admin/api/platos/especiales", json=ESPECIAL_VALIDO)
    assert r.status_code == 201
    datos = r.json()
    assert datos["id"] == "especial-abc123"
    assert datos["categoria"] == "especial-de-hoy"
    assert datos["nombre"] == ESPECIAL_VALIDO["nombre"]
    assert guardado["restaurante_id"] == RESTAURANTE_ID
    assert guardado["nombre"] == ESPECIAL_VALIDO["nombre"]


def test_crear_especial_con_precio_invalido_da_422(cliente: TestClient) -> None:
    r = cliente.post("/admin/api/platos/especiales", json={**ESPECIAL_VALIDO, "precio": 0})
    assert r.status_code == 422


def test_crear_especial_incoherente_con_gluten_da_422(cliente: TestClient) -> None:
    r = cliente.post(
        "/admin/api/platos/especiales",
        json={**ESPECIAL_VALIDO, "sin_gluten": True, "alergenos": ["gluten"]},
    )
    assert r.status_code == 422


def test_crear_especial_sin_nombre_da_422(cliente: TestClient) -> None:
    r = cliente.post("/admin/api/platos/especiales", json={**ESPECIAL_VALIDO, "nombre": ""})
    assert r.status_code == 422


# ---------------------------------------------------------------- eliminar


def test_eliminar_especial_sin_sesion_se_rechaza() -> None:
    r = TestClient(app).delete("/admin/api/platos/especiales/especial-abc123")
    assert r.status_code == 401


def test_elimina_un_especial_existente(
    cliente: TestClient, guardado: dict[str, object], tmp_path
) -> None:
    ruta = tmp_path / RESTAURANTE_ID / "especial-abc123.jpg"
    ruta.parent.mkdir(parents=True)
    ruta.write_bytes(b"\xff\xd8\xff")

    r = cliente.delete("/admin/api/platos/especiales/especial-abc123")
    assert r.status_code == 204
    assert guardado["eliminado_plato_id"] == "especial-abc123"
    assert not ruta.exists()


def test_eliminar_especial_que_no_existe_da_404(cliente: TestClient) -> None:
    r = cliente.delete("/admin/api/platos/especiales/no-existe")
    assert r.status_code == 404
