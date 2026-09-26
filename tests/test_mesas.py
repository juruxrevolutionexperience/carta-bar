"""Pedido en mesa, primer bloque (docs/PEDIDO-EN-MESA.md): mesas, entrar por
QR (crea sesion o se une) y quien es el anfitrion.

Las pruebas de `entrar_por_qr` usan el repositorio en memoria directamente,
sin FastAPI: es logica de negocio pura (quien es anfitrion, la sesion unica
por mesa) y no deberia depender de la base de datos para poder probarse.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_COMENSAL, COOKIE_SESION, RESTAURANTE_ID, app
from carta_bar.mesas import (
    RepositorioMesasMemoria,
    SesionMesa,
    SesionYaAbiertaError,
    entrar_por_qr,
)

# --------------------------------------------------------------- entrar_por_qr


@pytest.fixture
def repo() -> RepositorioMesasMemoria:
    return RepositorioMesasMemoria()


def test_token_desconocido_no_entra(repo: RepositorioMesasMemoria) -> None:
    assert entrar_por_qr(repo, "token-que-no-existe", "Ana", "es") is None


def test_mesa_inactiva_no_entra(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    repo.mesas[mesa.id] = mesa.model_copy(update={"activa": False})
    assert entrar_por_qr(repo, mesa.token_qr, "Ana", "es") is None


def test_primera_persona_crea_sesion_y_es_anfitrion(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es")
    assert resultado is not None
    sesion, comensal = resultado
    assert sesion.mesa_id == mesa.id
    # La abrio un cliente: queda a la espera de que el camarero la acepte.
    assert sesion.estado == "por_confirmar"
    assert sesion.abierta_por == "cliente"
    assert comensal.rol == "anfitrion"
    assert comensal.nombre == "Ana"


def test_segunda_persona_mismo_token_es_invitado_de_la_misma_sesion(
    repo: RepositorioMesasMemoria,
) -> None:
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    primero = entrar_por_qr(repo, mesa.token_qr, "Ana", "es")
    segundo = entrar_por_qr(repo, mesa.token_qr, "Luis", "es")
    assert primero is not None and segundo is not None
    sesion_1, _ = primero
    sesion_2, comensal_2 = segundo
    assert sesion_1.id == sesion_2.id
    assert comensal_2.rol == "invitado"


def test_sin_nombre_se_asigna_comensal_numerado(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    assert entrar_por_qr(repo, mesa.token_qr, None, "es") is not None
    resultado = entrar_por_qr(repo, mesa.token_qr, "  ", "es")
    assert resultado is not None
    _, segundo = resultado
    assert segundo.nombre == "Comensal 2"


def test_dos_mesas_distintas_no_comparten_sesion(repo: RepositorioMesasMemoria) -> None:
    mesa_a = repo.crear_mesa("bar1", "Mesa A")
    mesa_b = repo.crear_mesa("bar1", "Mesa B")
    resultado_a = entrar_por_qr(repo, mesa_a.token_qr, "Ana", "es")
    resultado_b = entrar_por_qr(repo, mesa_b.token_qr, "Luis", "es")
    assert resultado_a is not None and resultado_b is not None
    _, entra_en_a = resultado_a
    sesion_b, _ = resultado_b
    assert entra_en_a.rol == "anfitrion"
    assert sesion_b.mesa_id == mesa_b.id


class _RepoConCarrera(RepositorioMesasMemoria):
    """Simula la carrera: dos peticiones ven sesion_abierta_de() == None a la
    vez, y la segunda en llegar a crear_sesion() se encuentra que la primera
    ya gano — debe unirse a esa, no fallar ni crear otra."""

    def __init__(self) -> None:
        super().__init__()
        self.primera_vez = True

    def crear_sesion(self, *args: Any, **kwargs: Any) -> SesionMesa:
        if self.primera_vez:
            self.primera_vez = False
            # Otra peticion "gano" justo aqui: crea la sesion por debajo.
            super().crear_sesion(*args, **kwargs)
            raise SesionYaAbiertaError()
        return super().crear_sesion(*args, **kwargs)


def test_carrera_al_crear_sesion_se_une_a_la_que_gano() -> None:
    repo = _RepoConCarrera()
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es")
    assert resultado is not None
    sesion, comensal = resultado
    assert sesion.mesa_id == mesa.id
    assert len(repo.sesiones) == 1
    # La otra peticion creo la sesion pero aun no habia metido a nadie: el
    # primero en sentarse es el anfitrion, gane quien gane la carrera.
    assert comensal.rol == "anfitrion"


# -------------------------------------------------------------------- API


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


def test_crear_mesa_exige_sesion(gerente: TestClient) -> None:
    sin_sesion = TestClient(app)
    r = sin_sesion.post("/admin/api/mesas", json={"nombre": "Terraza 1"})
    assert r.status_code == 401
    assert sin_sesion.get("/admin/api/mesas").status_code == 401


def test_gerente_crea_y_lista_mesas(gerente: TestClient) -> None:
    r = gerente.post("/admin/api/mesas", json={"nombre": "Terraza API 1"})
    assert r.status_code == 201
    creada = r.json()
    assert creada["nombre"] == "Terraza API 1"
    assert creada["activa"] is True
    assert len(creada["token_qr"]) > 10

    listado = gerente.get("/admin/api/mesas").json()
    assert any(m["id"] == creada["id"] for m in listado)


def test_entrar_por_qr_crea_sesion_y_pone_cookie(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza API 2"}).json()

    cliente = TestClient(app)
    r = cliente.post("/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"})
    assert r.status_code == 200
    datos = r.json()
    assert datos["rol"] == "anfitrion"
    assert COOKIE_COMENSAL in r.cookies


def test_segundo_en_entrar_es_invitado(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza API 3"}).json()

    primero = TestClient(app).post(
        "/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Ana"}
    )
    segundo = TestClient(app).post(
        "/api/mesa/entrar", json={"token_qr": creada["token_qr"], "nombre": "Luis"}
    )
    assert primero.json()["rol"] == "anfitrion"
    assert segundo.json()["rol"] == "invitado"
    assert primero.json()["sesion_id"] == segundo.json()["sesion_id"]


def test_token_desconocido_da_404(gerente: TestClient) -> None:
    r = TestClient(app).post("/api/mesa/entrar", json={"token_qr": "no-existe-este-token"})
    assert r.status_code == 404


# ------------------------------------------------------ regenerar el QR de una mesa


def test_regenerar_token_invalida_el_anterior(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    nueva = repo.regenerar_token("bar1", mesa.id)
    assert nueva is not None
    assert nueva.token_qr != mesa.token_qr
    assert nueva.id == mesa.id and nueva.nombre == mesa.nombre
    # El QR impreso antes ya no abre nada; el nuevo si.
    assert entrar_por_qr(repo, mesa.token_qr, "Ana", "es") is None
    assert entrar_por_qr(repo, nueva.token_qr, "Ana", "es") is not None


def test_regenerar_token_de_una_mesa_ajena_o_inexistente_da_none(
    repo: RepositorioMesasMemoria,
) -> None:
    mesa = repo.crear_mesa("bar1", "Terraza 7")
    assert repo.regenerar_token("bar2", mesa.id) is None
    assert repo.regenerar_token("bar1", "mesa-que-no-existe") is None
    # Y la mesa de bar1 conserva su token.
    assert repo.mesa_por_token(mesa.token_qr) is not None


def test_regenerar_qr_por_api(gerente: TestClient) -> None:
    creada = gerente.post("/admin/api/mesas", json={"nombre": "Terraza API 4"}).json()
    r = gerente.post(f"/admin/api/mesas/{creada['id']}/regenerar-qr")
    assert r.status_code == 200
    nueva = r.json()
    assert nueva["id"] == creada["id"]
    assert nueva["token_qr"] != creada["token_qr"]

    viejo = TestClient(app).post("/api/mesa/entrar", json={"token_qr": creada["token_qr"]})
    nuevo = TestClient(app).post("/api/mesa/entrar", json={"token_qr": nueva["token_qr"]})
    assert viejo.status_code == 404
    assert nuevo.status_code == 200


def test_regenerar_qr_exige_sesion_y_existir(gerente: TestClient) -> None:
    assert TestClient(app).post("/admin/api/mesas/mesa-x/regenerar-qr").status_code == 401
    assert gerente.post("/admin/api/mesas/mesa-que-no-existe/regenerar-qr").status_code == 404
