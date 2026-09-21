"""CRUD (solo edicion) de platos desde el panel: PUT /admin/api/platos/{id}."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app

PLATO_VALIDO = {
    "nombre": "Tortilla de patatas",
    "descripcion": "Con cebolla, al punto",
    "precio": 9.5,
    "ingredientes": ["huevo", "patata", "cebolla"],
}


@pytest.fixture
def guardado() -> dict[str, object]:
    """Captura la ultima llamada a actualizar_plato_editable / actualizar_disponibilidad."""
    return {}


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch, guardado: dict[str, object]) -> TestClient:
    def _actualizar(
        restaurante_id: str,
        plato_id: str,
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
        alergenos_confirmados: bool | None = None,
    ) -> bool:
        guardado["alergenos_confirmados"] = alergenos_confirmados
        guardado["restaurante_id"] = restaurante_id
        guardado["plato_id"] = plato_id
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
        return plato_id != "no-existe"

    def _actualizar_disponibilidad(
        restaurante_id: str, plato_id: str, disponible: bool
    ) -> bool:
        guardado["restaurante_id"] = restaurante_id
        guardado["plato_id"] = plato_id
        guardado["disponible"] = disponible
        return plato_id != "no-existe"

    monkeypatch.setattr("carta_bar.api.actualizar_plato_editable", _actualizar)
    monkeypatch.setattr("carta_bar.api.actualizar_disponibilidad", _actualizar_disponibilidad)
    cliente = TestClient(app)
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return cliente


def test_sin_sesion_se_rechaza() -> None:
    r = TestClient(app).put("/admin/api/platos/p001", json=PLATO_VALIDO)
    assert r.status_code == 401


def test_edita_un_plato_existente(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.put("/admin/api/platos/p001", json=PLATO_VALIDO)
    assert r.status_code == 204
    assert guardado["restaurante_id"] == RESTAURANTE_ID
    assert guardado["plato_id"] == "p001"
    assert guardado["nombre"] == "Tortilla de patatas"
    assert guardado["precio"] == 9.5
    assert guardado["ingredientes"] == ["huevo", "patata", "cebolla"]


def test_un_plato_que_no_existe_da_404(cliente: TestClient) -> None:
    r = cliente.put("/admin/api/platos/no-existe", json=PLATO_VALIDO)
    assert r.status_code == 404


def test_precio_cero_o_negativo_se_rechaza(cliente: TestClient) -> None:
    for precio in (0, -5):
        r = cliente.put("/admin/api/platos/p001", json={**PLATO_VALIDO, "precio": precio})
        assert r.status_code == 422


def test_precio_nulo_significa_a_consultar(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.put("/admin/api/platos/p001", json={**PLATO_VALIDO, "precio": None})
    assert r.status_code == 204
    assert guardado["precio"] is None


def test_nombre_vacio_se_rechaza(cliente: TestClient) -> None:
    r = cliente.put("/admin/api/platos/p001", json={**PLATO_VALIDO, "nombre": ""})
    assert r.status_code == 422


def test_ingredientes_vacios_estan_permitidos(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.put("/admin/api/platos/p001", json={**PLATO_VALIDO, "ingredientes": []})
    assert r.status_code == 204
    assert guardado["ingredientes"] == []


# ------------------------------------------ alergenos, etiqueta, dieta


def test_guarda_alergenos_y_etiqueta(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    cuerpo = {
        **PLATO_VALIDO,
        "alergenos": ["huevos", "lacteos"],
        "etiqueta": "recomendacion_chef",
        "vegetariano": True,
        "sin_lactosa": False,
    }
    r = cliente.put("/admin/api/platos/p001", json=cuerpo)
    assert r.status_code == 204
    assert guardado["alergenos"] == ["huevos", "lacteos"]
    assert guardado["etiqueta"] == "recomendacion_chef"
    assert guardado["vegetariano"] is True


def test_sin_alergenos_ni_etiqueta_usa_los_valores_por_defecto(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.put("/admin/api/platos/p001", json=PLATO_VALIDO)
    assert r.status_code == 204
    assert guardado["alergenos"] == []
    assert guardado["etiqueta"] is None
    assert guardado["vegano"] is False


def test_un_alergeno_desconocido_se_rechaza(cliente: TestClient) -> None:
    r = cliente.put(
        "/admin/api/platos/p001", json={**PLATO_VALIDO, "alergenos": ["marisco-raro"]}
    )
    assert r.status_code == 422


def test_una_etiqueta_desconocida_se_rechaza(cliente: TestClient) -> None:
    r = cliente.put(
        "/admin/api/platos/p001", json={**PLATO_VALIDO, "etiqueta": "super-especial"}
    )
    assert r.status_code == 422


def test_sin_gluten_con_alergeno_gluten_se_rechaza(cliente: TestClient) -> None:
    r = cliente.put(
        "/admin/api/platos/p001",
        json={**PLATO_VALIDO, "sin_gluten": True, "alergenos": ["gluten"]},
    )
    assert r.status_code == 422


def test_sin_gluten_sin_alergeno_gluten_se_acepta(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.put(
        "/admin/api/platos/p001",
        json={**PLATO_VALIDO, "sin_gluten": True, "alergenos": ["lacteos"]},
    )
    assert r.status_code == 204
    assert guardado["sin_gluten"] is True


# ------------------------------------------------------ disponibilidad


def test_disponibilidad_sin_sesion_se_rechaza() -> None:
    r = TestClient(app).post(
        "/admin/api/platos/p001/disponibilidad", json={"disponible": False}
    )
    assert r.status_code == 401


def test_marca_un_plato_como_agotado(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.post("/admin/api/platos/p001/disponibilidad", json={"disponible": False})
    assert r.status_code == 204
    assert guardado["plato_id"] == "p001"
    assert guardado["disponible"] is False


def test_vuelve_a_marcar_un_plato_como_disponible(
    cliente: TestClient, guardado: dict[str, object]
) -> None:
    r = cliente.post("/admin/api/platos/p001/disponibilidad", json={"disponible": True})
    assert r.status_code == 204
    assert guardado["disponible"] is True


def test_disponibilidad_de_un_plato_que_no_existe_da_404(cliente: TestClient) -> None:
    r = cliente.post(
        "/admin/api/platos/no-existe/disponibilidad", json={"disponible": False}
    )
    assert r.status_code == 404
