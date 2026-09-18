"""Panel superadmin: /superadmin/login, /superadmin,
/superadmin/api/restaurantes. Sesion completamente aparte de la de un
restaurante (COOKIE_SESION_SUPERADMIN, no COOKIE_SESION)."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, COOKIE_SESION_SUPERADMIN, RESTAURANTE_ID, app
from carta_bar.modelos import ResumenRestaurante

CLAVE_SUPERADMIN = "clave-superadmin-de-prueba"


@pytest.fixture
def guardado() -> dict[str, object]:
    return {}


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch, guardado: dict[str, object]) -> TestClient:
    monkeypatch.setattr(
        "carta_bar.api.SUPERADMIN_CLAVE_HASH", auth.hash_clave(CLAVE_SUPERADMIN)
    )

    def _listar() -> list[ResumenRestaurante]:
        return [
            ResumenRestaurante(id="la-catedral", nombre="La CatedRal", num_platos=28),
            ResumenRestaurante(id="demo", nombre="Restaurante Demo", num_platos=1),
        ]

    def _crear(restaurante_id: str, nombre: str, clave_hash: str) -> None:
        guardado["restaurante_id"] = restaurante_id
        guardado["nombre"] = nombre
        guardado["clave_hash"] = clave_hash

    monkeypatch.setattr("carta_bar.api.listar_restaurantes", _listar)
    monkeypatch.setattr("carta_bar.api.crear_restaurante", _crear)
    return TestClient(app)


def _con_sesion_superadmin(cliente: TestClient) -> TestClient:
    token = auth.crear_token_sesion("__superadmin__")
    cliente.cookies.set(COOKIE_SESION_SUPERADMIN, token)
    return cliente


# --------------------------------------------------------------------- login


def test_login_con_clave_correcta_pone_la_cookie(cliente: TestClient) -> None:
    r = cliente.post("/superadmin/login", json={"clave": CLAVE_SUPERADMIN})
    assert r.status_code == 204
    assert COOKIE_SESION_SUPERADMIN in r.cookies


def test_login_con_clave_incorrecta_se_rechaza(cliente: TestClient) -> None:
    r = cliente.post("/superadmin/login", json={"clave": "lo-que-sea"})
    assert r.status_code == 401


def test_sin_clave_configurada_el_login_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("carta_bar.api.SUPERADMIN_CLAVE_HASH", None)
    r = TestClient(app).post("/superadmin/login", json={"clave": "lo-que-sea"})
    assert r.status_code == 401


# -------------------------------------------------------------------- panel


def test_panel_sin_sesion_redirige_al_login(cliente: TestClient) -> None:
    r = cliente.get("/superadmin", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/superadmin/login"


def test_una_sesion_de_restaurante_no_sirve_para_el_superadmin(cliente: TestClient) -> None:
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    r = cliente.get("/superadmin/api/restaurantes")
    assert r.status_code == 401


def test_una_sesion_de_superadmin_no_sirve_para_el_admin_de_un_restaurante(
    cliente: TestClient,
) -> None:
    _con_sesion_superadmin(cliente)
    r = cliente.get("/admin", follow_redirects=False)
    assert r.status_code == 303


# ---------------------------------------------------------------- listar


def test_listar_restaurantes_sin_sesion_se_rechaza(cliente: TestClient) -> None:
    r = cliente.get("/superadmin/api/restaurantes")
    assert r.status_code == 401


def test_listar_restaurantes_con_sesion(cliente: TestClient) -> None:
    _con_sesion_superadmin(cliente)
    r = cliente.get("/superadmin/api/restaurantes")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 2
    assert datos[0]["id"] == "la-catedral"
    assert datos[1]["num_platos"] == 1


# ----------------------------------------------------------------- crear


def test_crear_restaurante_sin_sesion_se_rechaza(cliente: TestClient) -> None:
    r = cliente.post(
        "/superadmin/api/restaurantes",
        json={"restaurante_id": "bar2", "nombre": "Bar Pepe", "clave": "clave12345"},
    )
    assert r.status_code == 401


def test_crea_un_restaurante_valido(cliente: TestClient, guardado: dict[str, object]) -> None:
    _con_sesion_superadmin(cliente)
    r = cliente.post(
        "/superadmin/api/restaurantes",
        json={"restaurante_id": "bar2", "nombre": "Bar Pepe", "clave": "clave12345"},
    )
    assert r.status_code == 201
    datos = r.json()
    assert datos["id"] == "bar2"
    assert datos["nombre"] == "Bar Pepe"
    assert datos["num_platos"] == 0
    assert guardado["restaurante_id"] == "bar2"
    # La clave nunca viaja ni se guarda en claro.
    assert guardado["clave_hash"] != "clave12345"


def test_crear_restaurante_con_subdominio_invalido_da_422(cliente: TestClient) -> None:
    _con_sesion_superadmin(cliente)
    r = cliente.post(
        "/superadmin/api/restaurantes",
        json={"restaurante_id": "Bar Pepe!", "nombre": "Bar Pepe", "clave": "clave12345"},
    )
    assert r.status_code == 422


def test_crear_restaurante_con_clave_corta_da_422(cliente: TestClient) -> None:
    _con_sesion_superadmin(cliente)
    r = cliente.post(
        "/superadmin/api/restaurantes",
        json={"restaurante_id": "bar2", "nombre": "Bar Pepe", "clave": "corta"},
    )
    assert r.status_code == 422
