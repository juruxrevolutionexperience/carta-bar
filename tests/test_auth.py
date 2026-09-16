"""Login del panel: hash de contraseña, token de sesión y las rutas /admin/*."""

import time

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app

# ------------------------------------------------------------- hash_clave


def test_verifica_la_contrasena_correcta() -> None:
    h = auth.hash_clave("correcto-caballo-bateria")
    assert auth.verificar_clave("correcto-caballo-bateria", h)


def test_rechaza_la_contrasena_incorrecta() -> None:
    h = auth.hash_clave("correcto-caballo-bateria")
    assert not auth.verificar_clave("otra-cosa", h)


def test_dos_hashes_de_la_misma_clave_son_distintos() -> None:
    # Sal aleatoria: si coincidieran, una tabla arcoiris rompería cualquier cuenta.
    assert auth.hash_clave("misma-clave") != auth.hash_clave("misma-clave")


def test_un_hash_con_formato_invalido_no_rompe_la_verificacion() -> None:
    assert not auth.verificar_clave("cualquier-cosa", "esto-no-es-un-hash-valido")


def test_un_hash_de_otro_algoritmo_se_rechaza() -> None:
    assert not auth.verificar_clave("clave", "bcrypt$12$sal$hash")


# ------------------------------------------------------- token de sesión


def test_el_token_de_sesion_valida_al_mismo_restaurante() -> None:
    token = auth.crear_token_sesion("la-catedral")
    assert auth.verificar_token_sesion(token) == "la-catedral"


def test_un_token_manipulado_se_rechaza() -> None:
    token = auth.crear_token_sesion("la-catedral")
    manipulado = token[:-4] + "abcd"
    assert auth.verificar_token_sesion(manipulado) is None


def test_un_token_basura_no_rompe_la_verificacion() -> None:
    assert auth.verificar_token_sesion("esto-no-es-base64-valido-!!") is None


def test_un_token_caducado_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    # Se crea "en el pasado" (sin dormir de verdad ni depender del redondeo
    # a segundos de time.time()) y se verifica con el reloj real.
    hace_rato = time.time() - auth._DURACION_SESION_S - 60
    with monkeypatch.context() as m:
        m.setattr(auth.time, "time", lambda: hace_rato)
        token = auth.crear_token_sesion("la-catedral")
    assert auth.verificar_token_sesion(token) is None


# --------------------------------------------------------------- rutas


@pytest.fixture
def claves() -> dict[str, str | None]:
    """Almacén en memoria: sustituye a la tabla restaurantes durante el test."""
    return {"hash": None}


@pytest.fixture
def cliente(
    monkeypatch: pytest.MonkeyPatch, claves: dict[str, str | None]
) -> TestClient:
    monkeypatch.setattr(
        "carta_bar.api.obtener_clave_hash", lambda restaurante_id: claves["hash"]
    )

    def _guardar(restaurante_id: str, clave_hash: str) -> None:
        claves["hash"] = clave_hash

    monkeypatch.setattr("carta_bar.api.guardar_clave_hash", _guardar)
    return TestClient(app)


def test_login_sin_contrasena_establecida_se_rechaza(cliente: TestClient) -> None:
    r = cliente.post("/admin/login", json={"clave": "lo-que-sea"})
    assert r.status_code == 401


def test_login_con_contrasena_correcta_entra(
    cliente: TestClient, claves: dict[str, str | None]
) -> None:
    claves["hash"] = auth.hash_clave("secreta123")
    r = cliente.post("/admin/login", json={"clave": "secreta123"})
    assert r.status_code == 204
    assert COOKIE_SESION in r.cookies


def test_login_con_contrasena_incorrecta_se_rechaza(
    cliente: TestClient, claves: dict[str, str | None]
) -> None:
    claves["hash"] = auth.hash_clave("secreta123")
    r = cliente.post("/admin/login", json={"clave": "incorrecta"})
    assert r.status_code == 401
    assert COOKIE_SESION not in r.cookies


def test_admin_sin_sesion_redirige_al_login(cliente: TestClient) -> None:
    r = cliente.get("/admin", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/admin/login"


def test_admin_con_sesion_valida_sirve_el_panel(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    # El panel real lo compila Vite (frontend/) a web/dist/admin.html; en los
    # tests no hay build, asi que se sirve uno de mentira desde una carpeta
    # aparte, igual que test_admin_fotos.py hace con DIR_FOTOS.
    (tmp_path / "admin.html").write_text("<h1>Panel de gestión</h1>", encoding="utf-8")
    monkeypatch.setattr("carta_bar.api.DIR_FRONTEND", tmp_path)

    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    r = cliente.get("/admin", follow_redirects=False)
    assert r.status_code == 200
    assert "panel" in r.text.lower()


def test_admin_con_cookie_de_otro_restaurante_no_entra(cliente: TestClient) -> None:
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion("otro-restaurante"))
    r = cliente.get("/admin", follow_redirects=False)
    assert r.status_code == 303


def test_cambiar_clave_sin_sesion_se_rechaza(cliente: TestClient) -> None:
    r = cliente.post(
        "/admin/cambiar-clave", json={"clave_actual": "a", "clave_nueva": "nueva1234"}
    )
    assert r.status_code == 401


def test_cambiar_clave_con_la_actual_incorrecta_se_rechaza(
    cliente: TestClient, claves: dict[str, str | None]
) -> None:
    claves["hash"] = auth.hash_clave("secreta123")
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    r = cliente.post(
        "/admin/cambiar-clave",
        json={"clave_actual": "mala", "clave_nueva": "nueva1234"},
    )
    assert r.status_code == 401
    assert auth.verificar_clave("secreta123", claves["hash"])  # sigue siendo la vieja


def test_cambiar_clave_funciona_y_la_nueva_sirve_para_entrar(
    cliente: TestClient, claves: dict[str, str | None]
) -> None:
    claves["hash"] = auth.hash_clave("secreta123")
    cliente.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    r = cliente.post(
        "/admin/cambiar-clave",
        json={"clave_actual": "secreta123", "clave_nueva": "nueva1234"},
    )
    assert r.status_code == 204
    assert auth.verificar_clave("nueva1234", claves["hash"])


def test_logout_borra_la_cookie(cliente: TestClient) -> None:
    r = cliente.post("/admin/logout")
    assert r.status_code == 204
    borrada = next(c for c in r.headers.get_list("set-cookie") if c.startswith(COOKIE_SESION))
    assert "Max-Age=0" in borrada or "expires=" in borrada.lower()
