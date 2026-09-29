"""Pedido en mesa, bloque 2 (docs/PEDIDO-EN-MESA.md, "Bloque 2 en detalle"):
propuestas de los comensales, con formatos y extras ya existentes (carta_bar/
productos.py), y su confirmacion por el anfitrion.

La logica de permisos (quien puede retirar, quien puede confirmar) se prueba
con el repositorio en memoria, sin FastAPI. El resto, contra la API completa,
igual que test_mesas.py y test_productos.py.
"""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import (
    COOKIE_SESION,
    RESTAURANTE_ID,
    _eventos_propuestas,
    _resolver_restaurante,
    app,
)
from carta_bar.propuestas import (
    OpcionElegida,
    RepositorioPropuestasMemoria,
    confirmar_pendientes,
    proponer,
    retirar,
)

PLATO = "p001"  # datos/la-catedral/carta.json: precio 19.0, disponible.

# --------------------------------------------------------------- logica pura


@pytest.fixture
def repo() -> RepositorioPropuestasMemoria:
    return RepositorioPropuestasMemoria()


def test_proponer_copia_precio_y_calcula_el_total(repo: RepositorioPropuestasMemoria) -> None:
    p = proponer(
        repo,
        "sesion-1",
        "comensal-1",
        "Ana",
        PLATO,
        "Tabla Mixta",
        9.0,
        "Media",
        2,
        [OpcionElegida(nombre="Queso", precio=1.5)],
        "sin picos",
    )
    assert p.precio_unitario == 9.0
    assert p.formato == "Media"
    # (9 + 1.5) * 2
    assert p.total == 21.0
    assert p.estado == "pendiente"
    assert p.nota == "sin picos"


def test_invitado_solo_retira_las_suyas(repo: RepositorioPropuestasMemoria) -> None:
    de_ana = proponer(repo, "s1", "ana", "Ana", PLATO, "X", 10, None, 1, [], None)
    de_luis = proponer(repo, "s1", "luis", "Luis", PLATO, "X", 10, None, 1, [], None)

    assert retirar(repo, de_luis.id, "ana", quien_es_anfitrion=False) == "sin_permiso"
    assert retirar(repo, de_ana.id, "ana", quien_es_anfitrion=False) == "ok"
    assert repo.obtener(de_ana.id).estado == "retirada"  # type: ignore[union-attr]
    assert repo.obtener(de_luis.id).estado == "pendiente"  # type: ignore[union-attr]


def test_el_anfitrion_retira_cualquiera(repo: RepositorioPropuestasMemoria) -> None:
    de_luis = proponer(repo, "s1", "luis", "Luis", PLATO, "X", 10, None, 1, [], None)
    assert retirar(repo, de_luis.id, "ana", quien_es_anfitrion=True) == "ok"


def test_no_se_puede_retirar_dos_veces_ni_lo_que_no_existe(
    repo: RepositorioPropuestasMemoria,
) -> None:
    p = proponer(repo, "s1", "ana", "Ana", PLATO, "X", 10, None, 1, [], None)
    assert retirar(repo, p.id, "ana", quien_es_anfitrion=False) == "ok"
    assert retirar(repo, p.id, "ana", quien_es_anfitrion=False) == "no_existe"
    assert retirar(repo, "no-existe", "ana", quien_es_anfitrion=False) == "no_existe"


def test_confirmar_pendientes_no_toca_las_retiradas_ni_otra_sesion(
    repo: RepositorioPropuestasMemoria,
) -> None:
    de_esta = proponer(repo, "s1", "ana", "Ana", PLATO, "X", 10, None, 1, [], None)
    retirada = proponer(repo, "s1", "luis", "Luis", PLATO, "X", 10, None, 1, [], None)
    retirar(repo, retirada.id, "luis", quien_es_anfitrion=False)
    de_otra = proponer(repo, "s2", "eva", "Eva", PLATO, "X", 10, None, 1, [], None)

    confirmadas = confirmar_pendientes(repo, "s1")
    assert [p.id for p in confirmadas] == [de_esta.id]
    assert confirmadas[0].estado == "confirmada"
    assert repo.obtener(de_esta.id).estado == "confirmada"  # type: ignore[union-attr]
    assert repo.obtener(retirada.id).estado == "retirada"  # type: ignore[union-attr]
    assert repo.obtener(de_otra.id).estado == "pendiente"  # type: ignore[union-attr]


# -------------------------------------------------------------------- API


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


def _mesa_con_anfitrion(gerente: TestClient, nombre_mesa: str) -> TestClient:
    """Crea una mesa y la primera persona que entra por su QR (anfitrion),
    devuelta como un TestClient ya con la cookie de comensal puesta."""
    creada = gerente.post("/admin/api/mesas", json={"nombre": nombre_mesa}).json()
    cliente = TestClient(app)
    r = cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    assert r.status_code == 200
    return cliente


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("post", "/api/mesa/propuestas"),
        ("get", "/api/mesa/propuestas"),
        ("delete", "/api/mesa/propuestas/x"),
        ("post", "/api/mesa/propuestas/confirmar"),
    ],
)
def test_propuestas_exigen_estar_en_una_mesa(metodo: str, ruta: str) -> None:
    r = TestClient(app).request(metodo.upper(), ruta, json={"plato_id": PLATO})
    assert r.status_code == 401


def test_proponer_un_plato_disponible(gerente: TestClient) -> None:
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 1")
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "cantidad": 2})
    assert r.status_code == 201
    p = r.json()
    assert p["nombre_plato"] and p["precio_unitario"] == 19.0
    assert p["total"] == 38.0
    assert p["estado"] == "pendiente"
    assert p["comensal_nombre"] == "Ana"


def test_se_puede_proponer_mientras_la_mesa_esta_por_confirmar(gerente: TestClient) -> None:
    """El cliente no pierde lo que va pidiendo mientras espera a que el
    camarero acepte la mesa (decidido con el usuario, 2026-09-29): puede ir
    llenando la cesta desde el primer momento."""
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 10")
    assert anfitrion.get("/api/mesa/yo").json()["estado"] == "por_confirmar"
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    assert r.status_code == 201


def test_plato_inexistente_o_no_disponible_da_404(gerente: TestClient) -> None:
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 2")
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": "plato-que-no-existe"})
    assert r.status_code == 404


def test_formato_que_no_existe_da_400(gerente: TestClient) -> None:
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 3")
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "formato": "Ese no existe"})
    assert r.status_code == 400


def test_formato_con_precio_distinto_al_del_plato(gerente: TestClient) -> None:
    gerente.put(
        f"/admin/api/platos/{PLATO}/pedido",
        json={"formatos": [{"nombre": "Media", "precio": 9}, {"nombre": "Entera", "precio": 16}]},
    )
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 4")
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "formato": "Media"})
    assert r.status_code == 201
    assert r.json()["precio_unitario"] == 9.0
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={})  # deja el plato como estaba


def test_opciones_de_un_grupo_asignado(gerente: TestClient) -> None:
    grupo = gerente.post(
        "/admin/api/grupos-opciones",
        json={
            "nombre": "Punto de la carne",
            "minimo": 1,
            "maximo": 1,
            "opciones": [{"nombre": "Poco hecha"}, {"nombre": "Al punto"}],
        },
    ).json()
    gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"grupos": [grupo["id"]]})
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 5")

    # Sin elegir el punto de la carne (minimo 1): rechazado.
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "opciones": []})
    assert r.status_code == 400

    # Una opcion que no es de ningun grupo del plato: rechazada.
    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "opciones": ["No existe"]})
    assert r.status_code == 400

    r = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO, "opciones": ["Al punto"]})
    assert r.status_code == 201
    assert r.json()["opciones"] == [{"nombre": "Al punto", "precio": 0.0}]

    gerente.delete(f"/admin/api/grupos-opciones/{grupo['id']}")


def test_invitado_solo_quita_las_suyas_el_anfitrion_cualquiera(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Propuestas 6"}).json()
    anfitrion = TestClient(app)
    anfitrion.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    invitado = TestClient(app)
    invitado.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Luis"})

    de_ana = anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO}).json()
    de_luis = invitado.post("/api/mesa/propuestas", json={"plato_id": PLATO}).json()

    assert invitado.delete(f"/api/mesa/propuestas/{de_ana['id']}").status_code == 403
    assert invitado.delete(f"/api/mesa/propuestas/{de_luis['id']}").status_code == 204
    assert anfitrion.delete(f"/api/mesa/propuestas/{de_ana['id']}").status_code == 204


def test_solo_el_anfitrion_confirma(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Propuestas 7"}).json()
    anfitrion = TestClient(app)
    anfitrion.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    invitado = TestClient(app)
    invitado.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Luis"})

    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})
    invitado.post("/api/mesa/propuestas", json={"plato_id": PLATO})

    assert invitado.post("/api/mesa/propuestas/confirmar").status_code == 403
    r = anfitrion.post("/api/mesa/propuestas/confirmar")
    assert r.status_code == 200
    assert r.json()["confirmadas"] == 2

    estados = {p["estado"] for p in anfitrion.get("/api/mesa/propuestas").json()}
    assert estados == {"confirmada"}


def test_no_se_ven_las_propuestas_de_otro_restaurante(gerente: TestClient) -> None:
    anfitrion = _mesa_con_anfitrion(gerente, "Terraza Propuestas 8")
    anfitrion.post("/api/mesa/propuestas", json={"plato_id": PLATO})

    app.dependency_overrides[_resolver_restaurante] = lambda: "otro-bar"
    try:
        assert anfitrion.get("/api/mesa/propuestas").status_code == 401
    finally:
        app.dependency_overrides[_resolver_restaurante] = lambda: RESTAURANTE_ID


def test_eventos_sse_exige_mesa(gerente: TestClient) -> None:
    assert TestClient(app).get("/api/mesa/propuestas/eventos").status_code == 401


def test_eventos_sse_manda_la_lista_de_la_sesion(gerente: TestClient) -> None:
    # El generador se llama directamente (ver _eventos_propuestas en api.py):
    # abrir un stream de verdad con TestClient no cierra el hilo que duerme
    # entre eventos y deja la suite colgada.
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza Propuestas 9"}).json()
    cliente = TestClient(app)
    entrada = cliente.post(
        "/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"}
    ).json()
    cliente.post("/api/mesa/propuestas", json={"plato_id": PLATO})

    primer_evento = next(_eventos_propuestas(entrada["comensal_id"]))
    assert primer_evento.startswith("data:")
    assert PLATO in primer_evento
