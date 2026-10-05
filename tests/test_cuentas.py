"""Resumen de cuenta impreso al cobrar (carta_bar/cuentas.py): que nace bien
de un resumen_mesa (sin las propuestas retiradas, sin inventar nada si no
habia pedido) y que la pantalla de impresion lo recibe por el mismo sondeo
que ya usan cocina y barra."""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, _eventos_cuentas, app
from carta_bar.cuentas import RepositorioCuentasMemoria, registrar_cuenta
from carta_bar.propuestas import ComandaMesa, Propuesta, ResumenPorPersona

PLATO = "p001"  # datos/la-catedral/carta.json: precio 19.0, disponible.
DESDE_SIEMPRE = datetime(2000, 1, 1, tzinfo=UTC)


def _propuesta(id_: str, nombre: str, total: float, estado: str = "confirmada") -> Propuesta:
    return Propuesta(
        id=id_,
        sesion_id="s1",
        comensal_id=f"com-{nombre}",
        comensal_nombre=nombre,
        plato_id=PLATO,
        nombre_plato="Tabla Mixta",
        precio_unitario=total,
        cantidad=1,
        total=total,
        estado=estado,
        creada_en=datetime.now(UTC),
    )


def test_registrar_cuenta_arma_la_foto_a_partir_del_resumen() -> None:
    repo = RepositorioCuentasMemoria()
    comanda = ComandaMesa(
        propuestas=[_propuesta("p1", "Ana", 19.0), _propuesta("p2", "Luis", 10.5)],
        total=29.5,
        por_persona=[
            ResumenPorPersona(nombre="Ana", total=19.0),
            ResumenPorPersona(nombre="Luis", total=10.5),
        ],
    )
    cuenta = registrar_cuenta(repo, "bar1", "Mesa 1", comanda)
    assert cuenta is not None
    assert cuenta.total == 29.5
    assert [lin.pedido_por_nombre for lin in cuenta.lineas] == ["Ana", "Luis"]
    assert repo.listar_recientes("bar1", DESDE_SIEMPRE) == [cuenta]


def test_registrar_cuenta_excluye_las_retiradas() -> None:
    """Esto es lo que cierra el bug real: una linea anulada en cocina queda
    como propuesta retirada (ver api.py, admin_anular_linea), y no debe
    colarse en el papel que se le da al cliente."""
    repo = RepositorioCuentasMemoria()
    comanda = ComandaMesa(
        propuestas=[
            _propuesta("p1", "Ana", 19.0),
            _propuesta("p2", "Ana", 5.0, estado="retirada"),
        ],
        total=19.0,
        por_persona=[ResumenPorPersona(nombre="Ana", total=19.0)],
    )
    cuenta = registrar_cuenta(repo, "bar1", "Mesa 1", comanda)
    assert cuenta is not None
    assert len(cuenta.lineas) == 1
    assert cuenta.total == 19.0


def test_registrar_cuenta_nada_que_cobrar_no_crea_nada() -> None:
    repo = RepositorioCuentasMemoria()
    comanda = ComandaMesa(propuestas=[], total=0, por_persona=[])
    assert registrar_cuenta(repo, "bar1", "Mesa 1", comanda) is None


def test_listar_recientes_no_mezcla_restaurantes() -> None:
    repo = RepositorioCuentasMemoria()
    comanda = ComandaMesa(
        propuestas=[_propuesta("p1", "Ana", 19.0)],
        total=19.0,
        por_persona=[ResumenPorPersona(nombre="Ana", total=19.0)],
    )
    registrar_cuenta(repo, "bar1", "Mesa 1", comanda)
    assert repo.listar_recientes("bar2", DESDE_SIEMPRE) == []


# -------------------------------------------------------------------- API


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


def _dato_del_evento(evento: str) -> list[dict]:
    assert evento.startswith("data:")
    return json.loads(evento[len("data:") :])


def test_cobrar_la_mesa_imprime_un_resumen_de_cuenta(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Cuenta 1"}).json()
    cliente = TestClient(app)
    r = cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    assert r.status_code == 200
    cliente.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    cliente.post("/api/mesa/propuestas/confirmar")

    r = gerente.post(f"/admin/api/mesas/{creada['id']}/cobrar")
    assert r.status_code == 204

    cuentas = _dato_del_evento(next(_eventos_cuentas(RESTAURANTE_ID)))
    cuenta = next(c for c in cuentas if c["mesa_nombre"] == "Terraza Cuenta 1")
    assert cuenta["total"] == 19.0
    assert cuenta["por_persona"] == [{"nombre": "Ana", "total": 19.0}]


def test_cobrar_sin_pedir_nada_no_imprime_cuenta(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Cuenta Vacia"}).json()
    cliente = TestClient(app)
    cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})

    r = gerente.post(f"/admin/api/mesas/{creada['id']}/cobrar")
    assert r.status_code == 204

    cuentas = _dato_del_evento(next(_eventos_cuentas(RESTAURANTE_ID)))
    assert all(c["mesa_nombre"] != "Terraza Cuenta Vacia" for c in cuentas)


def test_cuentas_eventos_exige_sesion() -> None:
    assert TestClient(app).get("/admin/api/cuentas/eventos").status_code == 401


def test_anular_una_linea_antes_de_cobrar_no_la_cobra(gerente: TestClient) -> None:
    """De punta a punta: el bug real (anular en cocina no afectaba a la
    cuenta) y su arreglo, pero ya en lo que de verdad se le da al cliente."""
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Cuenta 2"}).json()
    cliente = TestClient(app)
    cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    cliente.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    cliente.post("/api/mesa/propuestas/confirmar")

    ticket = next(
        t
        for t in gerente.get("/admin/api/tickets").json()
        if t["mesa_nombre"] == "Terraza Cuenta 2"
    )
    linea_id = ticket["lineas"][0]["id"]
    gerente.post(
        f"/admin/api/tickets/{ticket['id']}/lineas/{linea_id}/anular",
        json={"motivo": "Pedido por error"},
    )

    r = gerente.post(f"/admin/api/mesas/{creada['id']}/cobrar")
    assert r.status_code == 204

    cuentas = _dato_del_evento(next(_eventos_cuentas(RESTAURANTE_ID)))
    assert all(c["mesa_nombre"] != "Terraza Cuenta 2" for c in cuentas)

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})
