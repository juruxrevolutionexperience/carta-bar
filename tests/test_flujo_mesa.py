"""Bloque 1 del flujo de mesa (docs/PEDIDO-EN-MESA.md, "Bloque 1 en detalle"):
estados de la mesa, abrir, unirse, confirmar, liberar, expulsar y el cierre
automatico de mesas olvidadas.

La logica se prueba con el repositorio en memoria y un reloj inyectado
(`ahora`), sin esperar 30 minutos de verdad. Al final, el mismo recorrido por
la API, como lo haran la carta y el panel.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_COMENSAL, COOKIE_SESION, RESTAURANTE_ID, _resolver_restaurante, app
from carta_bar.mesas import (
    ComensalExpulsadoError,
    Mesa,
    RepositorioMesasMemoria,
    abrir_mesa,
    cobrar_mesa,
    confirmar_mesa,
    entrar_por_qr,
    expulsar_comensal,
    liberar_mesa,
    mesas_del_local,
    mi_sesion,
    pedir_cuenta,
    sesion_de_mesa,
)

T0 = datetime(2026, 9, 26, 13, 0, tzinfo=UTC)


def _min(minutos: float) -> datetime:
    return T0 + timedelta(minutes=minutos)


@pytest.fixture
def repo() -> RepositorioMesasMemoria:
    return RepositorioMesasMemoria()


@pytest.fixture
def mesa(repo: RepositorioMesasMemoria) -> Mesa:
    return repo.crear_mesa("bar1", "Terraza 4")


def _estado(repo: RepositorioMesasMemoria, mesa: Mesa, ahora: datetime) -> str:
    return next(m.estado for m in mesas_del_local(repo, "bar1", ahora) if m.id == mesa.id)


# ------------------------------------------------------------------ estados


def test_mesa_sin_nadie_esta_libre(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    listada = next(m for m in mesas_del_local(repo, "bar1", T0) if m.id == mesa.id)
    assert listada.estado == "libre"
    assert listada.ocupada is False
    assert listada.comensales == 0


def test_cliente_escanea_y_queda_por_confirmar(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    assert entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0) is not None
    listada = next(m for m in mesas_del_local(repo, "bar1", T0) if m.id == mesa.id)
    assert listada.estado == "por_confirmar"
    assert listada.ocupada is True
    assert listada.comensales == 1
    assert listada.abierta_en == T0


def test_camarero_confirma_la_mesa_que_abrio_el_cliente(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    sesion = confirmar_mesa(repo, "bar1", mesa.id, ahora=_min(3))
    assert sesion is not None
    assert sesion.estado == "abierta"
    assert sesion.confirmada_en == _min(3)
    assert _estado(repo, mesa, _min(3)) == "abierta"


def test_confirmar_una_mesa_ya_abierta_no_cambia_nada(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    primera = confirmar_mesa(repo, "bar1", mesa.id, ahora=_min(3))
    segunda = confirmar_mesa(repo, "bar1", mesa.id, ahora=_min(5))
    assert primera is not None and segunda is not None
    assert segunda.id == primera.id
    assert segunda.confirmada_en == _min(3)


def test_confirmar_una_mesa_libre_no_hace_nada(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    assert confirmar_mesa(repo, "bar1", mesa.id, ahora=T0) is None
    assert repo.sesiones == {}


def test_camarero_abre_una_mesa_libre(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    sesion = abrir_mesa(repo, "bar1", mesa.id, comensales=4, ahora=T0)
    assert sesion is not None
    assert sesion.estado == "abierta"
    assert sesion.abierta_por == "personal"
    assert sesion.comensales_declarados == 4
    assert sesion.confirmada_en == T0


def test_cliente_que_escanea_una_mesa_abierta_por_el_camarero_es_anfitrion(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    abierta = abrir_mesa(repo, "bar1", mesa.id, ahora=T0)
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=_min(2))
    assert abierta is not None and resultado is not None
    sesion, comensal = resultado
    assert sesion.id == abierta.id
    # Ya la acepto el camarero al abrirla: no vuelve a quedar por confirmar.
    assert sesion.estado == "abierta"
    assert comensal.rol == "anfitrion"


def test_abrir_una_mesa_que_abrio_el_cliente_la_acepta_sin_crear_otra(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    del_cliente, _ = resultado
    sesion = abrir_mesa(repo, "bar1", mesa.id, comensales=3, ahora=_min(4))
    assert sesion is not None
    assert sesion.id == del_cliente.id
    assert sesion.estado == "abierta"
    assert sesion.abierta_por == "cliente"
    assert sesion.comensales_declarados == 3
    assert len(repo.sesiones) == 1


def test_abrir_una_mesa_inexistente_o_ajena_devuelve_none(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    assert abrir_mesa(repo, "bar1", "mesa-que-no-existe", ahora=T0) is None
    assert abrir_mesa(repo, "bar2", mesa.id, ahora=T0) is None
    assert repo.sesiones == {}


# ------------------------------------------------------------ unirse (sin codigo)


def test_los_demas_entran_como_invitados_sin_codigo(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    resultado = entrar_por_qr(repo, mesa.token_qr, "Luis", "en", ahora=_min(1))
    assert resultado is not None
    _, luis = resultado
    assert luis.rol == "invitado"
    assert _estado(repo, mesa, _min(1)) == "por_confirmar"


def test_volver_a_escanear_con_la_cookie_no_duplica_al_comensal(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    primero = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert primero is not None
    _, ana = primero
    otra_vez = entrar_por_qr(repo, mesa.token_qr, None, "es", ahora=_min(1), comensal_actual=ana.id)
    assert otra_vez is not None
    assert otra_vez[1].id == ana.id
    assert len(repo.listar_comensales(otra_vez[0].id)) == 1


def test_la_cookie_de_una_sesion_ya_cerrada_no_cuela_en_la_nueva(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    primero = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert primero is not None
    vieja, ana = primero
    liberar_mesa(repo, "bar1", mesa.id, ahora=_min(60))
    nueva = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=_min(90), comensal_actual=ana.id)
    assert nueva is not None
    assert nueva[0].id != vieja.id
    assert nueva[1].id != ana.id


# --------------------------------------------------------------------- liberar


def test_liberar_cierra_la_sesion_y_la_mesa_vuelve_a_libre(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    sesion, ana = resultado
    assert liberar_mesa(repo, "bar1", mesa.id, ahora=_min(10)) is True

    cerrada = repo.sesiones[sesion.id]
    assert cerrada.estado == "cerrada"
    assert cerrada.motivo_cierre == "liberada"
    assert cerrada.cerrada_en == _min(10)
    assert _estado(repo, mesa, _min(10)) == "libre"
    # El cliente ya no tiene mesa: la carta la olvida.
    assert mi_sesion(repo, "bar1", ana.id, ahora=_min(11)) is None


def test_despues_de_liberar_el_siguiente_que_escanea_abre_otra_sesion(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    liberar_mesa(repo, "bar1", mesa.id, ahora=_min(10))
    resultado = entrar_por_qr(repo, mesa.token_qr, "Marta", "es", ahora=_min(20))
    assert resultado is not None
    sesion, marta = resultado
    assert sesion.estado == "por_confirmar"
    assert marta.rol == "anfitrion"
    assert len(repo.sesiones) == 2


def test_liberar_una_mesa_libre_o_ajena_no_hace_nada(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    assert liberar_mesa(repo, "bar1", mesa.id, ahora=T0) is False
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert liberar_mesa(repo, "bar2", mesa.id, ahora=T0) is False
    assert _estado(repo, mesa, T0) == "por_confirmar"


# ------------------------------------------------------------ pedir la cuenta


def test_el_anfitrion_pide_la_cuenta_con_la_mesa_abierta(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    _, ana = resultado
    abrir_mesa(repo, "bar1", mesa.id, ahora=_min(1))

    sesion = pedir_cuenta(repo, "bar1", ana.id, ahora=_min(5))
    assert sesion is not None
    assert sesion.estado == "cuenta_pedida"
    assert _estado(repo, mesa, _min(5)) == "cuenta_pedida"


def test_un_invitado_no_puede_pedir_la_cuenta(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    resultado = entrar_por_qr(repo, mesa.token_qr, "Luis", "es", ahora=T0)
    assert resultado is not None
    _, luis = resultado
    abrir_mesa(repo, "bar1", mesa.id, ahora=_min(1))
    assert pedir_cuenta(repo, "bar1", luis.id, ahora=_min(5)) is None


def test_no_se_puede_pedir_la_cuenta_sin_que_acepten_la_mesa(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    _, ana = resultado
    assert pedir_cuenta(repo, "bar1", ana.id, ahora=_min(5)) is None


def test_no_se_pide_la_cuenta_de_otro_restaurante_ni_expulsado(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    _, ana = resultado
    abrir_mesa(repo, "bar1", mesa.id, ahora=_min(1))
    assert pedir_cuenta(repo, "bar2", ana.id, ahora=_min(5)) is None

    expulsar_comensal(repo, "bar1", ana.id, ahora=_min(6))
    assert pedir_cuenta(repo, "bar1", ana.id, ahora=_min(7)) is None


def test_cobrar_cierra_con_motivo_cobrada(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    sesion, ana = resultado
    abrir_mesa(repo, "bar1", mesa.id, ahora=_min(1))
    pedir_cuenta(repo, "bar1", ana.id, ahora=_min(5))

    assert cobrar_mesa(repo, "bar1", mesa.id, ahora=_min(10)) is True
    cerrada = repo.sesiones[sesion.id]
    assert cerrada.estado == "cerrada"
    assert cerrada.motivo_cierre == "cobrada"
    assert _estado(repo, mesa, _min(10)) == "libre"


def test_cobrar_una_mesa_libre_o_ajena_no_hace_nada(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    assert cobrar_mesa(repo, "bar1", mesa.id, ahora=T0) is False
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert cobrar_mesa(repo, "bar2", mesa.id, ahora=T0) is False


# ------------------------------------------------------------ cierre automatico


def test_por_confirmar_sin_aceptar_se_cierra_a_los_30_minutos(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    sesion, _ = resultado
    assert _estado(repo, mesa, _min(29)) == "por_confirmar"
    assert _estado(repo, mesa, _min(31)) == "libre"
    assert repo.sesiones[sesion.id].motivo_cierre == "automatica"


def test_los_30_minutos_cuentan_desde_que_se_abrio_no_desde_la_ultima_entrada(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    """Que entren mas amigos no alarga la espera: si el camarero no la acepta
    en media hora, es una mesa falsa o abandonada."""
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    entrar_por_qr(repo, mesa.token_qr, "Luis", "es", ahora=_min(25))
    assert _estado(repo, mesa, _min(31)) == "libre"


def test_una_mesa_aceptada_no_caduca_a_los_30_minutos(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    confirmar_mesa(repo, "bar1", mesa.id, ahora=_min(5))
    assert _estado(repo, mesa, _min(60)) == "abierta"


def test_cualquier_mesa_se_cierra_tras_4_horas_sin_actividad(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    sesion = abrir_mesa(repo, "bar1", mesa.id, ahora=T0)
    assert sesion is not None
    assert _estado(repo, mesa, _min(4 * 60 - 1)) == "abierta"
    assert _estado(repo, mesa, _min(4 * 60 + 1)) == "libre"
    assert repo.sesiones[sesion.id].motivo_cierre == "automatica"


def test_la_actividad_aleja_el_cierre_de_4_horas(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    abrir_mesa(repo, "bar1", mesa.id, ahora=T0)
    # Alguien se sienta a las 3 h: el reloj de 4 h vuelve a empezar.
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=_min(180))
    assert _estado(repo, mesa, _min(300)) == "abierta"
    assert _estado(repo, mesa, _min(180 + 4 * 60 + 1)) == "libre"


def test_mirar_el_estado_no_cuenta_como_actividad(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    """Un movil olvidado con la carta abierta no debe mantener viva la mesa."""
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    _, ana = resultado
    confirmar_mesa(repo, "bar1", mesa.id, ahora=T0)
    for minuto in range(0, 4 * 60, 30):
        mi_sesion(repo, "bar1", ana.id, ahora=_min(minuto))
    assert mi_sesion(repo, "bar1", ana.id, ahora=_min(4 * 60 + 1)) is None


def test_el_cierre_automatico_solo_toca_su_restaurante(repo: RepositorioMesasMemoria) -> None:
    de_bar1 = repo.crear_mesa("bar1", "1")
    de_bar2 = repo.crear_mesa("bar2", "1")
    entrar_por_qr(repo, de_bar1.token_qr, "Ana", "es", ahora=T0)
    entrar_por_qr(repo, de_bar2.token_qr, "Luis", "es", ahora=T0)
    mesas_del_local(repo, "bar1", _min(31))
    estados = {s.restaurante_id: s.estado for s in repo.sesiones.values()}
    assert estados == {"bar1": "cerrada", "bar2": "por_confirmar"}


def test_tras_un_cierre_automatico_la_mesa_se_puede_volver_a_abrir(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    """El cierre se aplica al leer: quien escanea justo despues no debe chocar
    con la sesion caducada (el indice de una sesion por mesa lo impediria)."""
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    resultado = entrar_por_qr(repo, mesa.token_qr, "Marta", "es", ahora=_min(45))
    assert resultado is not None
    sesion, marta = resultado
    assert sesion.abierta_en == _min(45)
    assert marta.rol == "anfitrion"


# -------------------------------------------------------------------- expulsar


def test_expulsado_pierde_el_acceso_aunque_conserve_la_cookie(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    resultado = entrar_por_qr(repo, mesa.token_qr, "Bromista", "es", ahora=_min(1))
    assert resultado is not None
    _, bromista = resultado

    expulsado = expulsar_comensal(repo, "bar1", bromista.id, ahora=_min(2))
    assert expulsado is not None and expulsado.expulsado_en == _min(2)
    assert mi_sesion(repo, "bar1", bromista.id, ahora=_min(3)) is None
    with pytest.raises(ComensalExpulsadoError):
        entrar_por_qr(repo, mesa.token_qr, None, "es", ahora=_min(3), comensal_actual=bromista.id)
    # Ya no cuenta como comensal de la mesa.
    listada = next(m for m in mesas_del_local(repo, "bar1", _min(3)) if m.id == mesa.id)
    assert listada.comensales == 1


def test_si_expulsan_al_anfitrion_pasa_a_serlo_el_siguiente(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    ana = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    luis = entrar_por_qr(repo, mesa.token_qr, "Luis", "es", ahora=_min(1))
    marta = entrar_por_qr(repo, mesa.token_qr, "Marta", "es", ahora=_min(2))
    assert ana is not None and luis is not None and marta is not None

    expulsar_comensal(repo, "bar1", ana[1].id, ahora=_min(3))
    roles = {c.nombre: c.rol for c in repo.listar_comensales(ana[0].id)}
    assert roles == {"Ana": "invitado", "Luis": "anfitrion", "Marta": "invitado"}


def test_si_se_queda_sin_nadie_el_siguiente_que_entra_es_anfitrion(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    ana = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert ana is not None
    expulsar_comensal(repo, "bar1", ana[1].id, ahora=_min(1))
    resultado = entrar_por_qr(repo, mesa.token_qr, "Luis", "es", ahora=_min(2))
    assert resultado is not None
    assert resultado[1].rol == "anfitrion"


def test_no_se_expulsa_a_un_comensal_de_otro_restaurante(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    assert resultado is not None
    _, ana = resultado
    assert expulsar_comensal(repo, "bar2", ana.id, ahora=_min(1)) is None
    assert expulsar_comensal(repo, "bar1", "comensal-que-no-existe", ahora=_min(1)) is None
    assert mi_sesion(repo, "bar1", ana.id, ahora=_min(1)) is not None


# ---------------------------------------------------------- lo que ve cada uno


def test_mi_sesion_cuenta_lo_que_necesita_la_carta(
    repo: RepositorioMesasMemoria, mesa: Mesa
) -> None:
    ana = entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    luis = entrar_por_qr(repo, mesa.token_qr, "Luis", "es", ahora=_min(1))
    assert ana is not None and luis is not None
    datos = mi_sesion(repo, "bar1", luis[1].id, ahora=_min(2))
    assert datos is not None
    assert datos.mesa == "Terraza 4"
    assert datos.estado == "por_confirmar"
    assert datos.rol == "invitado"
    assert datos.nombre == "Luis"
    assert datos.comensales == ["Ana", "Luis"]
    # Desde otro subdominio, esa cookie no vale.
    assert mi_sesion(repo, "bar2", luis[1].id, ahora=_min(2)) is None


def test_sesion_de_mesa_para_el_panel(repo: RepositorioMesasMemoria, mesa: Mesa) -> None:
    assert sesion_de_mesa(repo, "bar1", mesa.id, ahora=T0) is None
    entrar_por_qr(repo, mesa.token_qr, "Ana", "es", ahora=T0)
    resultado = sesion_de_mesa(repo, "bar1", mesa.id, ahora=_min(1))
    assert resultado is not None
    sesion, comensales = resultado
    assert sesion.estado == "por_confirmar"
    assert [c.nombre for c in comensales] == ["Ana"]
    assert sesion_de_mesa(repo, "bar2", mesa.id, ahora=_min(1)) is None


# ------------------------------------------------------------------------ API


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


def _mesa_nueva(gerente: TestClient, nombre: str) -> dict[str, str]:
    r = gerente.post("/admin/api/mesas", json={"nombre": nombre})
    assert r.status_code == 201
    datos: dict[str, str] = r.json()
    return datos


def _en_listado(gerente: TestClient, mesa_id: str) -> dict[str, object]:
    fila: dict[str, object] = next(
        m for m in gerente.get("/admin/api/mesas").json() if m["id"] == mesa_id
    )
    return fila


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("post", "/admin/api/mesas/mesa-x/abrir"),
        ("post", "/admin/api/mesas/mesa-x/confirmar"),
        ("post", "/admin/api/mesas/mesa-x/liberar"),
        ("get", "/admin/api/mesas/mesa-x/sesion"),
        ("post", "/admin/api/comensales/comensal-x/expulsar"),
    ],
)
def test_las_acciones_del_personal_exigen_sesion(metodo: str, ruta: str) -> None:
    assert getattr(TestClient(app), metodo)(ruta).status_code == 401


def test_recorrido_completo_por_la_api(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 1")
    assert _en_listado(gerente, mesa["id"])["estado"] == "libre"

    cliente = TestClient(app)
    r = cliente.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    assert r.status_code == 200
    assert r.json()["estado"] == "por_confirmar"
    assert r.json()["rol"] == "anfitrion"
    fila = _en_listado(gerente, mesa["id"])
    assert fila["estado"] == "por_confirmar" and fila["comensales"] == 1

    yo = cliente.get("/api/mesa/yo")
    assert yo.status_code == 200
    assert yo.json()["mesa"] == "Flujo API 1"

    r = gerente.post(f"/admin/api/mesas/{mesa['id']}/confirmar")
    assert r.status_code == 200 and r.json()["estado"] == "abierta"
    assert cliente.get("/api/mesa/yo").json()["estado"] == "abierta"

    sesion = gerente.get(f"/admin/api/mesas/{mesa['id']}/sesion").json()
    assert [c["nombre"] for c in sesion["comensales"]] == ["Ana"]

    assert gerente.post(f"/admin/api/mesas/{mesa['id']}/liberar").status_code == 204
    assert _en_listado(gerente, mesa["id"])["estado"] == "libre"
    assert cliente.get("/api/mesa/yo").status_code == 401
    assert gerente.get(f"/admin/api/mesas/{mesa['id']}/sesion").status_code == 404
    assert gerente.post(f"/admin/api/mesas/{mesa['id']}/liberar").status_code == 404


def test_abrir_por_api_con_y_sin_comensales(gerente: TestClient) -> None:
    con = _mesa_nueva(gerente, "Flujo API 2")
    sin = _mesa_nueva(gerente, "Flujo API 3")
    r = gerente.post(f"/admin/api/mesas/{con['id']}/abrir", json={"comensales": 4})
    assert r.status_code == 200
    assert r.json()["comensales_declarados"] == 4 and r.json()["abierta_por"] == "personal"
    r = gerente.post(f"/admin/api/mesas/{sin['id']}/abrir")
    assert r.status_code == 200 and r.json()["comensales_declarados"] is None
    assert gerente.post("/admin/api/mesas/mesa-que-no-existe/abrir").status_code == 404
    r = gerente.post(f"/admin/api/mesas/{con['id']}/abrir", json={"comensales": 0})
    assert r.status_code == 422


def test_volver_a_escanear_devuelve_el_mismo_comensal(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 4")
    cliente = TestClient(app)
    primero = cliente.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    segundo = cliente.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"]})
    assert primero.json()["comensal_id"] == segundo.json()["comensal_id"]
    assert _en_listado(gerente, mesa["id"])["comensales"] == 1


def test_expulsar_por_api(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 5")
    TestClient(app).post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    bromista = TestClient(app)
    r = bromista.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "X"})
    comensal_id = r.json()["comensal_id"]

    r = gerente.post(f"/admin/api/comensales/{comensal_id}/expulsar")
    assert r.status_code == 200 and r.json()["expulsado_en"] is not None
    # La cookie sigue en su movil, pero ya no le vale para nada.
    bromista.cookies.set(COOKIE_COMENSAL, auth.crear_token_sesion(comensal_id))
    assert bromista.get("/api/mesa/yo").status_code == 401
    bromista.cookies.set(COOKIE_COMENSAL, auth.crear_token_sesion(comensal_id))
    r = bromista.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"]})
    assert r.status_code == 403
    assert gerente.post("/admin/api/comensales/comensal-que-no-existe/expulsar").status_code == 404


def test_yo_sin_cookie_o_con_cookie_falsa_da_401() -> None:
    assert TestClient(app).get("/api/mesa/yo").status_code == 401
    falso = TestClient(app)
    falso.cookies.set(COOKIE_COMENSAL, "esto-no-es-un-token")
    assert falso.get("/api/mesa/yo").status_code == 401


def test_el_gerente_de_otro_restaurante_no_toca_estas_mesas(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 6")
    cliente = TestClient(app)
    r = cliente.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    comensal_id = r.json()["comensal_id"]

    app.dependency_overrides[_resolver_restaurante] = lambda: "otro-bar"
    ajeno = TestClient(app)
    ajeno.cookies.set(COOKIE_SESION, auth.crear_token_sesion("otro-bar"))
    assert ajeno.post(f"/admin/api/mesas/{mesa['id']}/abrir").status_code == 404
    assert ajeno.post(f"/admin/api/mesas/{mesa['id']}/confirmar").status_code == 404
    assert ajeno.post(f"/admin/api/mesas/{mesa['id']}/liberar").status_code == 404
    assert ajeno.get(f"/admin/api/mesas/{mesa['id']}/sesion").status_code == 404
    assert ajeno.post(f"/admin/api/comensales/{comensal_id}/expulsar").status_code == 404
    # Y la cookie del cliente no sirve en el subdominio del otro bar.
    con_su_cookie = TestClient(app)
    con_su_cookie.cookies.set(COOKIE_COMENSAL, auth.crear_token_sesion(comensal_id))
    assert con_su_cookie.get("/api/mesa/yo").status_code == 401

    app.dependency_overrides[_resolver_restaurante] = lambda: RESTAURANTE_ID
    assert _en_listado(gerente, mesa["id"])["estado"] == "por_confirmar"
    assert cliente.get("/api/mesa/yo").status_code == 200


# ------------------------------------------------------------- pedir la cuenta (API)


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("post", "/api/mesa/pedir-cuenta"),
        ("post", "/admin/api/mesas/mesa-x/cobrar"),
    ],
)
def test_pedir_cuenta_y_cobrar_exigen_sesion(metodo: str, ruta: str) -> None:
    assert getattr(TestClient(app), metodo)(ruta).status_code == 401


def test_pedir_cuenta_y_cobrar_por_api(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 7")
    cliente = TestClient(app)
    cliente.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    gerente.post(f"/admin/api/mesas/{mesa['id']}/confirmar")

    r = cliente.post("/api/mesa/pedir-cuenta")
    assert r.status_code == 204
    assert cliente.get("/api/mesa/yo").json()["estado"] == "cuenta_pedida"
    assert _en_listado(gerente, mesa["id"])["estado"] == "cuenta_pedida"

    assert gerente.post(f"/admin/api/mesas/{mesa['id']}/cobrar").status_code == 204
    assert _en_listado(gerente, mesa["id"])["estado"] == "libre"
    assert cliente.get("/api/mesa/yo").status_code == 401


def test_pedir_cuenta_sin_haberla_aceptado_se_rechaza(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 8")
    cliente = TestClient(app)
    cliente.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    assert cliente.post("/api/mesa/pedir-cuenta").status_code == 403


def test_invitado_no_puede_pedir_la_cuenta_por_api(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 9")
    anfitrion = TestClient(app)
    anfitrion.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Ana"})
    invitado = TestClient(app)
    invitado.post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"], "nombre": "Luis"})
    gerente.post(f"/admin/api/mesas/{mesa['id']}/confirmar")

    assert invitado.post("/api/mesa/pedir-cuenta").status_code == 403


def test_cobrar_una_mesa_ya_libre_da_404(gerente: TestClient) -> None:
    mesa = _mesa_nueva(gerente, "Flujo API 10")
    assert gerente.post(f"/admin/api/mesas/{mesa['id']}/cobrar").status_code == 404
