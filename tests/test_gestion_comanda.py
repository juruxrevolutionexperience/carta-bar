"""Gestion de la comanda desde la mesa (docs/PEDIDO-EN-MESA.md): al entrar en
una mesa ocupada desde Servicio o Mesas, el personal ve todo lo pedido
agrupado por persona, puede anadir algo el mismo (sin que nadie haya
escaneado el QR: "no todos lo usan desde el movil"), ajustar el precio de una
linea y confirmar.
"""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, _resolver_restaurante, app

PLATO = "p001"  # datos/la-catedral/carta.json: precio 19.0, disponible.


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("get", "/admin/api/mesas/x/comanda", None),
        ("post", "/admin/api/mesas/x/comanda", {"plato_id": PLATO}),
        ("delete", "/admin/api/mesas/x/comanda/y", None),
        ("put", "/admin/api/mesas/x/comanda/y/precio", {"precio_unitario": 5}),
        ("post", "/admin/api/mesas/x/comanda/confirmar", None),
    ],
)
def test_gestion_comanda_exige_sesion_de_gerente(
    metodo: str, ruta: str, cuerpo: dict[str, object] | None
) -> None:
    r = TestClient(app).request(metodo.upper(), ruta, json=cuerpo)
    assert r.status_code == 401


def test_comanda_de_mesa_libre_da_404(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 1"}).json()
    assert gerente.get(f"/admin/api/mesas/{creada['id']}/comanda").status_code == 404
    r = gerente.post(f"/admin/api/mesas/{creada['id']}/comanda", json={"plato_id": PLATO})
    assert r.status_code == 404


def test_el_personal_anade_sin_que_nadie_haya_escaneado(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 2"}).json()
    gerente.post(f"/admin/api/mesas/{creada['id']}/abrir", json={"comensales": 2})

    r = gerente.post(
        f"/admin/api/mesas/{creada['id']}/comanda", json={"plato_id": PLATO, "cantidad": 2}
    )
    assert r.status_code == 201
    propuesta = r.json()
    assert propuesta["comensal_nombre"] == "Camarero"
    assert propuesta["total"] == 38.0

    resumen = gerente.get(f"/admin/api/mesas/{creada['id']}/comanda").json()
    assert resumen["total"] == 38.0
    assert resumen["por_persona"] == [{"nombre": "Camarero", "total": 38.0}]


def test_el_personal_anade_a_una_mesa_con_anfitrion(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 3"}).json()
    cliente = TestClient(app)
    cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    cliente.post("/api/mesa/propuestas", json={"plato_id": PLATO})

    r = gerente.post(f"/admin/api/mesas/{creada['id']}/comanda", json={"plato_id": PLATO})
    assert r.status_code == 201
    assert r.json()["comensal_nombre"] == "Camarero"

    resumen = gerente.get(f"/admin/api/mesas/{creada['id']}/comanda").json()
    nombres = {p["nombre"] for p in resumen["por_persona"]}
    assert nombres == {"Ana", "Camarero"}
    assert resumen["total"] == 38.0


def test_ajustar_precio_de_una_linea(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 4"}).json()
    gerente.post(f"/admin/api/mesas/{creada['id']}/abrir", json={"comensales": 1})
    propuesta = gerente.post(
        f"/admin/api/mesas/{creada['id']}/comanda", json={"plato_id": PLATO, "cantidad": 2}
    ).json()

    r = gerente.put(
        f"/admin/api/mesas/{creada['id']}/comanda/{propuesta['id']}/precio",
        json={"precio_unitario": 10},
    )
    assert r.status_code == 200
    assert r.json()["precio_unitario"] == 10.0
    assert r.json()["total"] == 20.0

    resumen = gerente.get(f"/admin/api/mesas/{creada['id']}/comanda").json()
    assert resumen["total"] == 20.0


def test_ajustar_precio_de_una_propuesta_de_otra_mesa_da_404(gerente: TestClient) -> None:
    creada_a = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 5a"}).json()
    creada_b = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 5b"}).json()
    gerente.post(f"/admin/api/mesas/{creada_a['id']}/abrir", json={"comensales": 1})
    gerente.post(f"/admin/api/mesas/{creada_b['id']}/abrir", json={"comensales": 1})
    de_a = gerente.post(
        f"/admin/api/mesas/{creada_a['id']}/comanda", json={"plato_id": PLATO}
    ).json()

    r = gerente.put(
        f"/admin/api/mesas/{creada_b['id']}/comanda/{de_a['id']}/precio",
        json={"precio_unitario": 1},
    )
    assert r.status_code == 404


def test_el_personal_quita_cualquier_linea(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 6"}).json()
    cliente = TestClient(app)
    cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    de_ana = cliente.post("/api/mesa/propuestas", json={"plato_id": PLATO}).json()

    r = gerente.delete(f"/admin/api/mesas/{creada['id']}/comanda/{de_ana['id']}")
    assert r.status_code == 204
    resumen = gerente.get(f"/admin/api/mesas/{creada['id']}/comanda").json()
    assert resumen["total"] == 0.0

    r = gerente.delete(f"/admin/api/mesas/{creada['id']}/comanda/{de_ana['id']}")
    assert r.status_code == 404


def test_confirmar_desde_el_panel_del_personal_crea_ticket(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 7"}).json()
    gerente.post(f"/admin/api/mesas/{creada['id']}/abrir", json={"comensales": 1})
    gerente.post(f"/admin/api/mesas/{creada['id']}/comanda", json={"plato_id": PLATO})

    r = gerente.post(f"/admin/api/mesas/{creada['id']}/comanda/confirmar")
    assert r.json()["confirmadas"] == 1

    tickets = gerente.get("/admin/api/tickets").json()
    assert any(t["mesa_nombre"] == "Terraza Comanda 7" for t in tickets)

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_no_se_gestiona_una_mesa_de_otro_restaurante(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comanda 8"}).json()
    gerente.post(f"/admin/api/mesas/{creada['id']}/abrir", json={"comensales": 1})

    app.dependency_overrides[_resolver_restaurante] = lambda: "otro-bar"
    ajeno = TestClient(app)
    ajeno.cookies.set(COOKIE_SESION, auth.crear_token_sesion("otro-bar"))
    try:
        assert ajeno.get(f"/admin/api/mesas/{creada['id']}/comanda").status_code == 404
        r = ajeno.post(f"/admin/api/mesas/{creada['id']}/comanda", json={"plato_id": PLATO})
        assert r.status_code == 404
    finally:
        app.dependency_overrides[_resolver_restaurante] = lambda: RESTAURANTE_ID
