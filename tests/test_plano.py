"""Plano del local: zonas (Terraza, Salon 1...) y mesas con forma, tamano y
posicion (docs/PEDIDO-EN-MESA.md, segundo bloque).

Dos capas, como en test_mesas.py: la logica del repositorio en memoria (sin
FastAPI) y los endpoints del panel. El SQL de verdad se probo aparte contra un
Postgres real (ver el commit)."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app
from carta_bar.mesas import (
    RepositorioMesasMemoria,
    ZonaNoExisteError,
    entrar_por_qr,
)


@pytest.fixture
def repo() -> RepositorioMesasMemoria:
    return RepositorioMesasMemoria()


# ------------------------------------------------------------------- zonas


def test_un_bar_sin_zonas_recibe_sala_y_siempre_la_misma(repo: RepositorioMesasMemoria) -> None:
    primera = repo.listar_zonas("bar1")
    segunda = repo.listar_zonas("bar1")
    assert [z.nombre for z in primera] == ["Sala"]
    assert primera == segunda


def test_las_mesas_sueltas_pasan_a_la_primera_zona(repo: RepositorioMesasMemoria) -> None:
    # Las mesas del primer bloque nacieron sin zona.
    mesa = repo.crear_mesa("bar1", "Vieja")
    repo.mesas[mesa.id] = mesa.model_copy(update={"zona_id": None})
    zonas = repo.listar_zonas("bar1")
    assert repo.mesas[mesa.id].zona_id == zonas[0].id


def test_crear_renombrar_y_ordenar_zonas(repo: RepositorioMesasMemoria) -> None:
    sala = repo.listar_zonas("bar1")[0]
    terraza = repo.crear_zona("bar1", "Terraza")
    assert terraza.orden == sala.orden + 1

    renombrada = repo.renombrar_zona("bar1", terraza.id, "Terraza norte")
    assert renombrada is not None and renombrada.nombre == "Terraza norte"

    assert repo.ordenar_zonas("bar1", [terraza.id, sala.id]) is True
    assert [z.id for z in repo.listar_zonas("bar1")] == [terraza.id, sala.id]


@pytest.mark.parametrize("tipo", ["a_medias", "repetidos", "ajeno"])
def test_un_orden_que_no_cuadra_se_rechaza_y_no_cambia_nada(
    repo: RepositorioMesasMemoria, tipo: str
) -> None:
    sala = repo.listar_zonas("bar1")[0]
    terraza = repo.crear_zona("bar1", "Terraza")
    ajena = repo.crear_zona("bar2", "Salon")
    malo = {
        "a_medias": [terraza.id],
        "repetidos": [terraza.id, terraza.id],
        "ajeno": [terraza.id, sala.id, ajena.id],
    }[tipo]
    assert repo.ordenar_zonas("bar1", malo) is False
    assert [z.id for z in repo.listar_zonas("bar1")] == [sala.id, terraza.id]


def test_una_zona_de_otro_bar_no_se_toca(repo: RepositorioMesasMemoria) -> None:
    ajena = repo.crear_zona("bar2", "Salon")
    assert repo.renombrar_zona("bar1", ajena.id, "X") is None
    assert repo.eliminar_zona("bar1", ajena.id) == "no_existe"
    assert [z.nombre for z in repo.listar_zonas("bar2")] == ["Salon"]


def test_eliminar_una_zona_se_lleva_sus_mesas(repo: RepositorioMesasMemoria) -> None:
    sala = repo.listar_zonas("bar1")[0]
    terraza = repo.crear_zona("bar1", "Terraza")
    en_terraza = repo.crear_mesa("bar1", "T1", terraza.id)
    en_sala = repo.crear_mesa("bar1", "S1", sala.id)

    assert repo.eliminar_zona("bar1", terraza.id) == "ok"
    assert [m.id for m in repo.listar_mesas("bar1")] == [en_sala.id]
    assert repo.mesa_por_token(en_terraza.token_qr) is None


def test_no_se_elimina_una_zona_con_clientes_sentados(repo: RepositorioMesasMemoria) -> None:
    terraza = repo.crear_zona("bar1", "Terraza")
    mesa = repo.crear_mesa("bar1", "T1", terraza.id)
    assert entrar_por_qr(repo, mesa.token_qr, "Ana", "es") is not None

    assert repo.eliminar_zona("bar1", terraza.id) == "sesion_abierta"
    assert [z.id for z in repo.listar_zonas("bar1")].count(terraza.id) == 1
    assert [m.id for m in repo.listar_mesas("bar1")] == [mesa.id]


# ------------------------------------------------------------------- mesas


def test_crear_mesa_con_diseno_y_en_su_zona(repo: RepositorioMesasMemoria) -> None:
    terraza = repo.crear_zona("bar1", "Terraza")
    mesa = repo.crear_mesa(
        "bar1", "Barril 1", terraza.id, forma="barril", x=3, y=4.5, ancho=1, alto=1, capacidad=2
    )
    assert (mesa.zona_id, mesa.forma, mesa.x, mesa.y, mesa.capacidad) == (
        terraza.id,
        "barril",
        3,
        4.5,
        2,
    )


def test_crear_mesa_sin_zona_va_a_la_primera(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "4")
    assert mesa.zona_id == repo.listar_zonas("bar1")[0].id


def test_crear_mesa_en_zona_ajena_falla(repo: RepositorioMesasMemoria) -> None:
    ajena = repo.crear_zona("bar2", "Salon")
    with pytest.raises(ZonaNoExisteError):
        repo.crear_mesa("bar1", "M", ajena.id)


def test_actualizar_mueve_y_cambia_solo_lo_pedido(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1", forma="redonda", capacidad=4)
    movida = repo.actualizar_mesa("bar1", mesa.id, {"x": 5, "y": 6})
    assert movida is not None
    assert (movida.x, movida.y, movida.forma, movida.capacidad) == (5, 6, "redonda", 4)
    assert repo.listar_mesas("bar1")[0].x == 5


def test_actualizar_ignora_el_token_y_el_estado(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1")
    cambiada = repo.actualizar_mesa(
        "bar1", mesa.id, {"token_qr": "robado", "activa": False, "nombre": "Nueva"}
    )
    assert cambiada is not None
    assert cambiada.token_qr == mesa.token_qr
    assert cambiada.activa is True
    assert cambiada.nombre == "Nueva"


def test_mover_una_mesa_a_otra_zona(repo: RepositorioMesasMemoria) -> None:
    terraza = repo.crear_zona("bar1", "Terraza")
    mesa = repo.crear_mesa("bar1", "M1")
    movida = repo.actualizar_mesa("bar1", mesa.id, {"zona_id": terraza.id})
    assert movida is not None and movida.zona_id == terraza.id
    with pytest.raises(ZonaNoExisteError):
        repo.actualizar_mesa("bar1", mesa.id, {"zona_id": "zona-que-no-existe"})


def test_una_mesa_ajena_no_se_actualiza(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1")
    assert repo.actualizar_mesa("bar2", mesa.id, {"x": 9}) is None
    assert repo.actualizar_mesa("bar1", "mesa-que-no-existe", {"x": 9}) is None
    assert repo.listar_mesas("bar1")[0].x == 0


def test_eliminar_mesa_sin_historial_la_borra_del_todo(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1")
    assert repo.eliminar_mesa("bar1", mesa.id) == "ok"
    assert mesa.id not in repo.mesas
    assert repo.eliminar_mesa("bar1", mesa.id) == "no_existe"


def test_eliminar_mesa_con_historial_la_archiva(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1")
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es")
    assert resultado is not None
    sesion, _ = resultado
    repo.sesiones[sesion.id] = sesion.model_copy(update={"estado": "cerrada"})

    assert repo.eliminar_mesa("bar1", mesa.id) == "ok"
    # Sigue en la base (el historial cuelga de ella) pero ya no se ve ni abre nada.
    assert repo.mesas[mesa.id].activa is False
    assert repo.listar_mesas("bar1") == []
    assert entrar_por_qr(repo, mesa.token_qr, "Luis", "es") is None
    assert repo.regenerar_token("bar1", mesa.id) is None


def test_no_se_elimina_una_mesa_con_clientes_sentados(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1")
    assert entrar_por_qr(repo, mesa.token_qr, "Ana", "es") is not None
    assert repo.eliminar_mesa("bar1", mesa.id) == "sesion_abierta"
    assert [m.id for m in repo.listar_mesas("bar1")] == [mesa.id]


def test_una_mesa_ajena_no_se_elimina(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "M1")
    assert repo.eliminar_mesa("bar2", mesa.id) == "no_existe"
    assert [m.id for m in repo.listar_mesas("bar1")] == [mesa.id]


# ------------------------------------------------------------- API del panel


@pytest.fixture
def gerente(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Repositorio limpio en cada test: las zonas se listan enteras y compartir
    # estado entre tests haria depender uno del otro.
    monkeypatch.setattr("carta_bar.api.mesas", RepositorioMesasMemoria())
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("get", "/admin/api/zonas", None),
        ("post", "/admin/api/zonas", {"nombre": "Terraza"}),
        ("put", "/admin/api/zonas/z1", {"nombre": "X"}),
        ("put", "/admin/api/orden-zonas", {"ids": ["a"]}),
        ("delete", "/admin/api/zonas/z1", None),
        ("put", "/admin/api/mesas/m1", {"x": 1}),
        ("delete", "/admin/api/mesas/m1", None),
    ],
)
def test_sin_sesion_se_rechaza_todo(metodo: str, ruta: str, cuerpo: object) -> None:
    r = getattr(TestClient(app), metodo)(ruta, **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 401


def test_zonas_por_api(gerente: TestClient) -> None:
    sala = gerente.get("/admin/api/zonas").json()
    assert [z["nombre"] for z in sala] == ["Sala"]

    terraza = gerente.post("/admin/api/zonas", json={"nombre": "  Terraza   norte "})
    assert terraza.status_code == 201
    assert terraza.json()["nombre"] == "Terraza norte"

    renombrada = gerente.put(f"/admin/api/zonas/{terraza.json()['id']}", json={"nombre": "Patio"})
    assert renombrada.status_code == 200 and renombrada.json()["nombre"] == "Patio"

    orden = [terraza.json()["id"], sala[0]["id"]]
    assert gerente.put("/admin/api/orden-zonas", json={"ids": orden}).status_code == 204
    assert [z["id"] for z in gerente.get("/admin/api/zonas").json()] == orden

    assert gerente.put("/admin/api/orden-zonas", json={"ids": orden[:1]}).status_code == 400
    assert gerente.delete(f"/admin/api/zonas/{terraza.json()['id']}").status_code == 204
    assert gerente.delete(f"/admin/api/zonas/{terraza.json()['id']}").status_code == 404
    assert gerente.put("/admin/api/zonas/no-existe", json={"nombre": "X"}).status_code == 404


@pytest.mark.parametrize("nombre", ["", "   ", "a" * 61])
def test_nombre_de_zona_invalido_da_422(gerente: TestClient, nombre: str) -> None:
    assert gerente.post("/admin/api/zonas", json={"nombre": nombre}).status_code == 422


def test_crear_mesa_a_secas_sigue_funcionando(gerente: TestClient) -> None:
    r = gerente.post("/admin/api/mesas", json={"nombre": "4"})
    assert r.status_code == 201
    mesa = r.json()
    assert mesa["forma"] == "cuadrada" and mesa["zona_id"] is not None


def test_crear_mesa_con_diseno_completo(gerente: TestClient) -> None:
    zona = gerente.post("/admin/api/zonas", json={"nombre": "Terraza"}).json()
    r = gerente.post(
        "/admin/api/mesas",
        json={
            "nombre": "Terraza 4",
            "zona_id": zona["id"],
            "forma": "rectangular",
            "x": 2,
            "y": 3.5,
            "ancho": 4,
            "alto": 2,
            "rotacion": 90,
            "capacidad": 8,
        },
    )
    assert r.status_code == 201
    mesa = r.json()
    assert (mesa["zona_id"], mesa["forma"], mesa["y"], mesa["rotacion"], mesa["capacidad"]) == (
        zona["id"],
        "rectangular",
        3.5,
        90,
        8,
    )
    assert gerente.get("/admin/api/mesas").json()[0]["id"] == mesa["id"]


@pytest.mark.parametrize(
    "cambio",
    [
        {"forma": "hexagonal"},
        {"ancho": 0},
        {"alto": 21},
        {"x": -1},
        {"rotacion": 360},
        {"capacidad": 0},
        {"nombre": "   "},
    ],
)
def test_diseno_invalido_da_422(gerente: TestClient, cambio: dict[str, object]) -> None:
    cuerpo = {"nombre": "M", **cambio}
    assert gerente.post("/admin/api/mesas", json=cuerpo).status_code == 422
    mesa = gerente.post("/admin/api/mesas", json={"nombre": "Buena"}).json()
    assert gerente.put(f"/admin/api/mesas/{mesa['id']}", json=cambio).status_code == 422


def test_crear_mesa_en_zona_que_no_existe_da_404(gerente: TestClient) -> None:
    r = gerente.post("/admin/api/mesas", json={"nombre": "M", "zona_id": "zona-fantasma"})
    assert r.status_code == 404


def test_mover_una_mesa_con_put_parcial(gerente: TestClient) -> None:
    mesa = gerente.post(
        "/admin/api/mesas", json={"nombre": "M", "forma": "redonda", "capacidad": 4}
    ).json()
    r = gerente.put(f"/admin/api/mesas/{mesa['id']}", json={"x": 7, "y": 8})
    assert r.status_code == 200
    movida = r.json()
    assert (movida["x"], movida["y"], movida["forma"], movida["capacidad"]) == (7, 8, "redonda", 4)
    assert movida["token_qr"] == mesa["token_qr"]
    assert gerente.put("/admin/api/mesas/no-existe", json={"x": 1}).status_code == 404


def test_eliminar_mesa_por_api(gerente: TestClient) -> None:
    mesa = gerente.post("/admin/api/mesas", json={"nombre": "M"}).json()
    assert gerente.delete(f"/admin/api/mesas/{mesa['id']}").status_code == 204
    assert gerente.get("/admin/api/mesas").json() == []
    assert gerente.delete(f"/admin/api/mesas/{mesa['id']}").status_code == 404


def test_no_se_borra_lo_que_tiene_clientes_sentados(gerente: TestClient) -> None:
    zona = gerente.post("/admin/api/zonas", json={"nombre": "Terraza"}).json()
    mesa = gerente.post("/admin/api/mesas", json={"nombre": "M", "zona_id": zona["id"]}).json()
    entra = TestClient(app).post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"]})
    assert entra.status_code == 200

    assert gerente.delete(f"/admin/api/mesas/{mesa['id']}").status_code == 409
    assert gerente.delete(f"/admin/api/zonas/{zona['id']}").status_code == 409
    assert [m["id"] for m in gerente.get("/admin/api/mesas").json()] == [mesa["id"]]


def test_una_mesa_borrada_ya_no_deja_entrar_por_su_qr(gerente: TestClient) -> None:
    mesa = gerente.post("/admin/api/mesas", json={"nombre": "M"}).json()
    gerente.delete(f"/admin/api/mesas/{mesa['id']}")
    r = TestClient(app).post("/api/mesa/entrar", json={"token_qr": mesa["token_qr"]})
    assert r.status_code == 404


# --------------------------------------------- ocupacion (mesas en rojo en el plano)


def test_una_mesa_con_clientes_sentados_sale_ocupada(repo: RepositorioMesasMemoria) -> None:
    ocupada = repo.crear_mesa("bar1", "1")
    libre = repo.crear_mesa("bar1", "2")
    assert entrar_por_qr(repo, ocupada.token_qr, "Ana", "es") is not None

    por_id = {m.id: m for m in repo.listar_mesas("bar1")}
    assert por_id[ocupada.id].ocupada is True
    assert por_id[libre.id].ocupada is False


def test_al_cerrar_la_sesion_la_mesa_deja_de_estar_ocupada(repo: RepositorioMesasMemoria) -> None:
    mesa = repo.crear_mesa("bar1", "1")
    resultado = entrar_por_qr(repo, mesa.token_qr, "Ana", "es")
    assert resultado is not None
    sesion, _ = resultado
    repo.sesiones[sesion.id] = sesion.model_copy(update={"estado": "cerrada"})

    assert repo.listar_mesas("bar1")[0].ocupada is False


def test_la_ocupacion_de_un_bar_no_pasa_a_otro(repo: RepositorioMesasMemoria) -> None:
    de_bar1 = repo.crear_mesa("bar1", "1")
    de_bar2 = repo.crear_mesa("bar2", "1")
    assert entrar_por_qr(repo, de_bar1.token_qr, "Ana", "es") is not None

    assert repo.listar_mesas("bar2")[0].id == de_bar2.id
    assert repo.listar_mesas("bar2")[0].ocupada is False


def test_las_mesas_nuevas_nacen_con_las_medidas_del_plano_fino() -> None:
    # Mismos valores que DISENO en frontend/src/admin/planoUtil.ts.
    from carta_bar.mesas import DISENO_POR_FORMA

    esperado: dict[str, tuple[float, float, int]] = {
        "redonda": (3, 3, 4),
        "cuadrada": (3, 3, 4),
        "rectangular": (6, 3, 6),
        "barril": (2, 2, 2),
        "taburete": (1, 1, 1),
    }
    assert DISENO_POR_FORMA == esperado
