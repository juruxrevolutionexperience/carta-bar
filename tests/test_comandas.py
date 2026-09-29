"""Pedido en mesa, bloque 3 (docs/PEDIDO-EN-MESA.md, "Bloque 3 en detalle"):
la comanda que sale de verdad hacia cocina o barra cuando el anfitrion
confirma. Sin ventana de agrupacion: se manda al instante (decidido con el
usuario, 2026-09-29).

La logica de reparto y numeracion se prueba con el repositorio en memoria,
sin FastAPI; el recorrido completo (confirmar -> aparece el ticket -> cambia
de estado), contra la API, igual que test_propuestas.py.
"""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import (
    COOKIE_SESION,
    RESTAURANTE_ID,
    _eventos_comandas,
    _eventos_tickets,
    _resolver_restaurante,
    app,
)
from carta_bar.comandas import Linea, RepositorioComandasMemoria, crear_comanda, resumen_comandas

PLATO = "p001"  # datos/la-catedral/carta.json: precio 19.0, disponible.
PLATO_2 = "p002"


def _linea(nombre: str = "Croquetas") -> Linea:
    return Linea(
        propuesta_id="prop-1",
        nombre_plato=nombre,
        precio_unitario=8,
        cantidad=1,
        pedido_por_nombre="Ana",
    )


# --------------------------------------------------------------- logica pura


@pytest.fixture
def repo() -> RepositorioComandasMemoria:
    return RepositorioComandasMemoria()


def test_crear_comanda_reparte_un_ticket_por_destino(repo: RepositorioComandasMemoria) -> None:
    tickets = crear_comanda(
        repo,
        "bar1",
        "s1",
        "Terraza 7",
        {"cocina": [_linea("Croquetas")], "barra": [_linea("Caña")]},
    )
    destinos = {t.destino for t in tickets}
    assert destinos == {"cocina", "barra"}
    assert all(t.comanda_id == tickets[0].comanda_id for t in tickets)
    assert all(t.numero_comanda == 1 for t in tickets)
    assert all(t.mesa_nombre == "Terraza 7" for t in tickets)


def test_sin_lineas_no_crea_nada(repo: RepositorioComandasMemoria) -> None:
    assert crear_comanda(repo, "bar1", "s1", "Terraza 7", {}) == []
    assert repo.listar_pendientes("bar1") == []


def test_numero_correlativo_por_dia_y_por_restaurante(repo: RepositorioComandasMemoria) -> None:
    primera = crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    segunda = crear_comanda(repo, "bar1", "s2", "Mesa 2", {"cocina": [_linea()]})
    de_otro_bar = crear_comanda(repo, "bar2", "s3", "Mesa 1", {"cocina": [_linea()]})
    assert primera[0].numero_comanda == 1
    assert segunda[0].numero_comanda == 2
    assert de_otro_bar[0].numero_comanda == 1


def test_listar_pendientes_no_incluye_las_servidas(repo: RepositorioComandasMemoria) -> None:
    (ticket,) = crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    assert len(repo.listar_pendientes("bar1")) == 1
    repo.actualizar_estado("bar1", ticket.id, "servida", ticket.creado_en)
    assert repo.listar_pendientes("bar1") == []


def test_listar_pendientes_filtra_por_destino(repo: RepositorioComandasMemoria) -> None:
    crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()], "barra": [_linea("Caña")]})
    assert [t.destino for t in repo.listar_pendientes("bar1", "barra")] == ["barra"]


def test_resumen_comandas_en_preparacion_mientras_falte_un_ticket(
    repo: RepositorioComandasMemoria,
) -> None:
    """Comida y bebida de la misma comanda: el cliente solo la ve "servido"
    cuando las dos partes lo estan, no antes."""
    tickets = crear_comanda(
        repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()], "barra": [_linea("Caña")]}
    )
    de_cocina = next(t for t in tickets if t.destino == "cocina")
    repo.actualizar_estado("bar1", de_cocina.id, "servida", de_cocina.creado_en)

    resumen = resumen_comandas(repo, "s1")
    assert len(resumen) == 1
    assert resumen[0].numero == 1
    assert resumen[0].estado == "en_preparacion"


def test_resumen_comandas_servido_cuando_todos_sus_tickets_lo_estan(
    repo: RepositorioComandasMemoria,
) -> None:
    (ticket,) = crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    repo.actualizar_estado("bar1", ticket.id, "servida", ticket.creado_en)
    resumen = resumen_comandas(repo, "s1")
    assert resumen == [resumen[0]]
    assert resumen[0].estado == "servido"


def test_resumen_comandas_varias_por_numero_y_orden(repo: RepositorioComandasMemoria) -> None:
    crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    resumen = resumen_comandas(repo, "s1")
    assert [r.numero for r in resumen] == [1, 2]
    assert all(r.estado == "en_preparacion" for r in resumen)


def test_resumen_comandas_no_mezcla_sesiones(repo: RepositorioComandasMemoria) -> None:
    crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    crear_comanda(repo, "bar1", "s2", "Mesa 2", {"cocina": [_linea()]})
    assert len(resumen_comandas(repo, "s1")) == 1


def test_no_se_ve_ni_se_toca_un_ticket_de_otro_restaurante(
    repo: RepositorioComandasMemoria,
) -> None:
    (ticket,) = crear_comanda(repo, "bar1", "s1", "Mesa 1", {"cocina": [_linea()]})
    assert repo.obtener_ticket("bar2", ticket.id) is None
    assert repo.actualizar_estado("bar2", ticket.id, "servida", ticket.creado_en) is None
    assert repo.listar_pendientes("bar2") == []


# -------------------------------------------------------------------- API


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


def _mesa_con_anfitrion(gerente: TestClient, nombre_mesa: str) -> TestClient:
    creada = gerente.post("/admin/api/mesas", json={"nombre": nombre_mesa}).json()
    cliente = TestClient(app)
    r = cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    assert r.status_code == 200
    return cliente


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("get", "/admin/api/tickets"),
        ("post", "/admin/api/tickets/x/estado"),
        ("get", "/admin/api/tickets/eventos"),
    ],
)
def test_tickets_exigen_sesion_de_gerente(metodo: str, ruta: str) -> None:
    r = TestClient(app).request(metodo.upper(), ruta, json={"estado": "servida"})
    assert r.status_code == 401


def test_confirmar_crea_un_ticket_visible_en_admin(gerente: TestClient) -> None:
    # Destino explicito, no el de la categoria: evita depender de si otro
    # test dejo "para_empezar" apuntando a otro sitio.
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 1")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "cantidad": 2})

    r = anfitrion.post("/api/mesa/propuestas/confirmar")
    assert r.json()["confirmadas"] == 1

    tickets = gerente.get("/admin/api/tickets").json()
    ticket = next(t for t in tickets if t["mesa_nombre"] == "Terraza Comandas 1")
    assert ticket["destino"] == "cocina"
    assert ticket["estado"] == "recibida"
    assert len(ticket["lineas"]) == 1
    linea = ticket["lineas"][0]
    assert linea["cantidad"] == 2
    assert linea["pedido_por_nombre"] == "Ana"

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_confirmar_reparte_en_dos_tickets_segun_destino(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    gerente.put(f"/admin/api/platos/{PLATO_2}/pedido", json={"destino": "barra"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 2")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO_2})

    anfitrion.post("/api/mesa/propuestas/confirmar")

    tickets = [
        t
        for t in gerente.get("/admin/api/tickets").json()
        if t["mesa_nombre"] == "Terraza Comandas 2"
    ]
    assert {t["destino"] for t in tickets} == {"cocina", "barra"}
    assert tickets[0]["numero_comanda"] == tickets[1]["numero_comanda"]

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})
    gerente.put(f"/admin/api/platos/{PLATO_2}/pedido", json={})


def test_el_alcohol_se_copia_del_plato_a_la_linea(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "barra", "alcohol": True})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 3")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas/confirmar")

    ticket = next(
        t
        for t in gerente.get("/admin/api/tickets").json()
        if t["mesa_nombre"] == "Terraza Comandas 3"
    )
    assert ticket["lineas"][0]["alcohol"] is True

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_sin_pendientes_confirmar_no_crea_ticket(gerente: TestClient) -> None:
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 4")
    r = anfitrion.post("/api/mesa/propuestas/confirmar")
    assert r.json()["confirmadas"] == 0
    assert all(
        t["mesa_nombre"] != "Terraza Comandas 4" for t in gerente.get("/admin/api/tickets").json()
    )


def test_cambiar_estado_hasta_servida_lo_quita_del_listado(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 5")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas/confirmar")
    ticket = next(
        t
        for t in gerente.get("/admin/api/tickets").json()
        if t["mesa_nombre"] == "Terraza Comandas 5"
    )

    r = gerente.post(f"/admin/api/tickets/{ticket['id']}/estado", json={"estado": "en_preparacion"})
    assert r.status_code == 200
    assert r.json()["estado"] == "en_preparacion"

    gerente.post(f"/admin/api/tickets/{ticket['id']}/estado", json={"estado": "servida"})
    restantes = gerente.get("/admin/api/tickets").json()
    assert all(t["id"] != ticket["id"] for t in restantes)

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_estado_invalido_o_ticket_inexistente(gerente: TestClient) -> None:
    r = gerente.post("/admin/api/tickets/no-existe/estado", json={"estado": "servida"})
    assert r.status_code == 404
    r = gerente.post("/admin/api/tickets/no-existe/estado", json={"estado": "algo-raro"})
    assert r.status_code == 422


def test_no_se_ven_tickets_de_otro_restaurante(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 6")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas/confirmar")
    ticket = next(
        t
        for t in gerente.get("/admin/api/tickets").json()
        if t["mesa_nombre"] == "Terraza Comandas 6"
    )

    app.dependency_overrides[_resolver_restaurante] = lambda: "otro-bar"
    ajeno = TestClient(app)
    ajeno.cookies.set(COOKIE_SESION, auth.crear_token_sesion("otro-bar"))
    try:
        assert all(t["id"] != ticket["id"] for t in ajeno.get("/admin/api/tickets").json())
        r = ajeno.post(f"/admin/api/tickets/{ticket['id']}/estado", json={"estado": "servida"})
        assert r.status_code == 404
    finally:
        app.dependency_overrides[_resolver_restaurante] = lambda: RESTAURANTE_ID

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_eventos_sse_manda_los_tickets_pendientes(gerente: TestClient) -> None:
    # Igual que test_propuestas.py: el generador se llama directamente, sin
    # abrir un stream HTTP de verdad (deja el hilo colgado en TestClient).
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 7")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas/confirmar")

    primer_evento = next(_eventos_tickets(RESTAURANTE_ID))
    assert primer_evento.startswith("data:")
    assert "Terraza Comandas 7" in primer_evento

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_eventos_sse_filtra_por_destino(gerente: TestClient) -> None:
    # La pantalla de impresion de cocina no debe recibir los de barra, ni al
    # reves (SeccionImpresion escucha solo su destino).
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    gerente.put(f"/admin/api/platos/{PLATO_2}/pedido", json={"destino": "barra"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 11")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO_2})
    anfitrion.post("/api/mesa/propuestas/confirmar")

    de_cocina = next(_eventos_tickets(RESTAURANTE_ID, "cocina"))
    de_barra = next(_eventos_tickets(RESTAURANTE_ID, "barra"))
    assert "Terraza Comandas 11" in de_cocina and '"destino": "barra"' not in de_cocina
    assert "Terraza Comandas 11" in de_barra and '"destino": "cocina"' not in de_barra

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})
    gerente.put(f"/admin/api/platos/{PLATO_2}/pedido", json={})


# ------------------------------------------------------ lo que ve el cliente


def test_mesa_comandas_exige_estar_en_una_mesa() -> None:
    assert TestClient(app).get("/api/mesa/comandas").status_code == 401


def test_el_cliente_ve_su_comanda_en_preparacion_y_luego_servida(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Comandas 8")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas/confirmar")

    resumen = anfitrion.get("/api/mesa/comandas").json()
    assert resumen == [{"numero": resumen[0]["numero"], "estado": "en_preparacion"}]

    ticket = next(
        t
        for t in gerente.get("/admin/api/tickets").json()
        if t["mesa_nombre"] == "Terraza Comandas 8"
    )
    gerente.post(f"/admin/api/tickets/{ticket['id']}/estado", json={"estado": "servida"})

    resumen = anfitrion.get("/api/mesa/comandas").json()
    assert resumen[0]["estado"] == "servido"

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_un_invitado_ve_la_misma_comanda_que_el_anfitrion(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comandas 9"}).json()
    anfitrion = TestClient(app)
    anfitrion.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    invitado = TestClient(app)
    invitado.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Luis"})

    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    anfitrion.post("/api/mesa/propuestas/confirmar")

    assert invitado.get("/api/mesa/comandas").json() == anfitrion.get("/api/mesa/comandas").json()

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})


def test_eventos_sse_de_comandas_manda_el_resumen(gerente: TestClient) -> None:
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"destino": "cocina"})
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Comandas 10"}).json()
    cliente = TestClient(app)
    entrada = cliente.post(
        "/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"}
    ).json()
    cliente.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    cliente.post("/api/mesa/propuestas/confirmar")

    primer_evento = next(_eventos_comandas(entrada["comensal_id"]))
    assert primer_evento.startswith("data:")
    assert "en_preparacion" in primer_evento

    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})
