"""Productos: lo que le falta a un plato para pedirlo (carta_bar/productos.py).

Destino por categoria con excepcion por plato, formatos con precio, grupos de
extras reutilizables y alcohol. La logica con el repositorio en memoria; al
final, la API del panel y la carta publica con sus formatos.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, _resolver_restaurante, app
from carta_bar.productos import (
    DatosGrupo,
    DatosPedidoPlato,
    Formato,
    GrupoNoExisteError,
    Opcion,
    RepositorioProductosMemoria,
    con_formatos,
    config_productos,
    destino_de,
)


@pytest.fixture
def repo() -> RepositorioProductosMemoria:
    return RepositorioProductosMemoria()


def _extras() -> DatosGrupo:
    return DatosGrupo(
        nombre="Extras de hamburguesa",
        minimo=0,
        maximo=3,
        opciones=[Opcion(nombre="Queso", precio=1), Opcion(nombre="Bacon", precio=1.5)]
        + [Opcion(nombre="Huevo", precio=1)],
    )


def _punto() -> DatosGrupo:
    return DatosGrupo(
        nombre="Punto de la carne",
        minimo=1,
        maximo=1,
        opciones=[Opcion(nombre="Poco hecha"), Opcion(nombre="Al punto")]
        + [Opcion(nombre="Hecha")],
    )


# ------------------------------------------------------------------- destino


def test_sin_nada_todo_va_a_cocina(repo: RepositorioProductosMemoria) -> None:
    assert destino_de("hamburguesas", None, repo.destinos_categoria("bar1")) == "cocina"


def test_el_plato_hereda_el_destino_de_su_categoria(repo: RepositorioProductosMemoria) -> None:
    repo.fijar_destino_categoria("bar1", "bebidas", "barra")
    destinos = repo.destinos_categoria("bar1")
    assert destino_de("bebidas", None, destinos) == "barra"
    sin_destino = repo.guardar_pedido_plato("bar1", "cana", DatosPedidoPlato())
    assert destino_de("bebidas", sin_destino, destinos) == "barra"


def test_un_plato_suelto_puede_llevar_otro_destino(repo: RepositorioProductosMemoria) -> None:
    """Un cafe con hielo en "Postres" lo prepara la barra, no la cocina."""
    repo.fijar_destino_categoria("bar1", "postres", "cocina")
    cafe = repo.guardar_pedido_plato("bar1", "cafe", DatosPedidoPlato(destino="barra"))
    assert destino_de("postres", cafe, repo.destinos_categoria("bar1")) == "barra"


def test_el_destino_de_una_categoria_no_se_mezcla_entre_restaurantes(
    repo: RepositorioProductosMemoria,
) -> None:
    repo.fijar_destino_categoria("bar1", "bebidas", "barra")
    assert repo.destinos_categoria("bar2") == {}


# ------------------------------------------------------------------ formatos


def test_formatos_con_su_precio(repo: RepositorioProductosMemoria) -> None:
    datos = DatosPedidoPlato(
        formatos=[Formato(nombre="Tapa", precio=3), Formato(nombre="  Media  ración ", precio=6)]
    )
    guardado = repo.guardar_pedido_plato("bar1", "croquetas", datos)
    assert [(f.nombre, f.precio) for f in guardado.formatos] == [
        ("Tapa", 3),
        ("Media ración", 6),
    ]


@pytest.mark.parametrize(
    "formatos",
    [
        [{"nombre": "Tapa", "precio": 0}],
        [{"nombre": "Tapa", "precio": -2}],
        [{"nombre": "   ", "precio": 3}],
        [{"nombre": "Tapa", "precio": 3}, {"nombre": "tapa", "precio": 4}],
        [{"nombre": f"F{i}", "precio": 1} for i in range(11)],
    ],
)
def test_formatos_invalidos(formatos: list[dict[str, object]]) -> None:
    with pytest.raises(ValidationError):
        DatosPedidoPlato.model_validate({"formatos": formatos})


def test_el_precio_se_redondea_a_centimos() -> None:
    assert Formato(nombre="Caña", precio=2.499).precio == 2.5


# -------------------------------------------------------------------- grupos


def test_un_grupo_se_crea_y_se_asigna_a_varios_platos(repo: RepositorioProductosMemoria) -> None:
    extras = repo.crear_grupo("bar1", _extras())
    for plato in ("clasica", "pollo", "vegana"):
        repo.guardar_pedido_plato("bar1", plato, DatosPedidoPlato(grupos=[extras.id]))
    asignados = repo.listar_pedido_platos("bar1")
    assert all(asignados[p].grupos == [extras.id] for p in ("clasica", "pollo", "vegana"))


def test_cambiar_un_grupo_vale_para_todos_sus_platos(repo: RepositorioProductosMemoria) -> None:
    """La razon de que sean reutilizables: el queso sube de precio una vez."""
    extras = repo.crear_grupo("bar1", _extras())
    repo.guardar_pedido_plato("bar1", "clasica", DatosPedidoPlato(grupos=[extras.id]))
    caro = DatosGrupo(
        nombre="Extras de hamburguesa",
        maximo=2,
        opciones=[Opcion(nombre="Queso", precio=1.5), Opcion(nombre="Bacon", precio=2)],
    )
    repo.actualizar_grupo("bar1", extras.id, caro)
    config = config_productos(repo, "bar1")
    grupo = next(g for g in config.grupos if g.id == config.platos["clasica"].grupos[0])
    assert grupo.opciones[0].precio == 1.5


def test_grupos_en_el_orden_en_que_se_crearon(repo: RepositorioProductosMemoria) -> None:
    a = repo.crear_grupo("bar1", _extras())
    b = repo.crear_grupo("bar1", _punto())
    assert [g.id for g in repo.listar_grupos("bar1")] == [a.id, b.id]


def test_borrar_un_grupo_lo_quita_de_los_platos(repo: RepositorioProductosMemoria) -> None:
    extras = repo.crear_grupo("bar1", _extras())
    punto = repo.crear_grupo("bar1", _punto())
    repo.guardar_pedido_plato("bar1", "clasica", DatosPedidoPlato(grupos=[extras.id, punto.id]))
    assert repo.eliminar_grupo("bar1", extras.id) is True
    assert repo.listar_pedido_platos("bar1")["clasica"].grupos == [punto.id]
    assert repo.eliminar_grupo("bar1", extras.id) is False


def test_no_se_asigna_un_grupo_de_otro_restaurante(repo: RepositorioProductosMemoria) -> None:
    ajeno = repo.crear_grupo("bar2", _extras())
    with pytest.raises(GrupoNoExisteError):
        repo.guardar_pedido_plato("bar1", "clasica", DatosPedidoPlato(grupos=[ajeno.id]))
    assert repo.actualizar_grupo("bar1", ajeno.id, _punto()) is None
    assert repo.eliminar_grupo("bar1", ajeno.id) is False


@pytest.mark.parametrize(
    "grupo",
    [
        # Obligatorio elegir 2 de un grupo que como mucho deja 1.
        {"nombre": "Salsas", "minimo": 2, "maximo": 1, "opciones": [{"nombre": "Alioli"}]},
        # Deja elegir 3 y solo hay 2.
        {
            "nombre": "Salsas",
            "maximo": 3,
            "opciones": [{"nombre": "Alioli"}, {"nombre": "Brava"}],
        },
        # Sin opciones.
        {"nombre": "Salsas", "opciones": []},
        # Dos opciones iguales.
        {"nombre": "Salsas", "opciones": [{"nombre": "Brava"}, {"nombre": "brava"}]},
        # Precio negativo.
        {"nombre": "Salsas", "opciones": [{"nombre": "Brava", "precio": -1}]},
    ],
)
def test_grupos_invalidos(grupo: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DatosGrupo.model_validate(grupo)


def test_una_opcion_sin_precio_es_gratis() -> None:
    assert _punto().opciones[0].precio == 0


# ------------------------------------------------------------ carta publica


def test_la_carta_lleva_los_formatos_de_cada_plato(repo: RepositorioProductosMemoria) -> None:
    repo.guardar_pedido_plato(
        "bar1", "croquetas", DatosPedidoPlato(formatos=[Formato(nombre="Tapa", precio=3)])
    )
    carta: list[dict[str, object]] = [
        {"id": "croquetas", "nombre": "Croquetas"},
        {"id": "flan", "nombre": "Flan"},
    ]
    resultado = con_formatos(repo, "bar1", carta)
    assert resultado[0]["formatos"] == [{"nombre": "Tapa", "precio": 3}]
    assert resultado[1]["formatos"] == []
    # El nombre del plato llega tal cual: esto no traduce nada.
    assert resultado[0]["nombre"] == "Croquetas"


# ------------------------------------------------------------------------ API

PLATO = "p001"
CATEGORIA = "para_empezar"


@pytest.fixture
def gerente() -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("get", "/admin/api/productos", None),
        ("put", f"/admin/api/categorias/{CATEGORIA}/destino", {"destino": "barra"}),
        ("put", f"/admin/api/platos/{PLATO}/pedido", {}),
        ("post", "/admin/api/grupos-opciones", {"nombre": "X", "opciones": [{"nombre": "Y"}]}),
        ("put", "/admin/api/grupos-opciones/g", {"nombre": "X", "opciones": [{"nombre": "Y"}]}),
        ("delete", "/admin/api/grupos-opciones/g", None),
    ],
)
def test_el_panel_de_productos_exige_sesion(
    metodo: str, ruta: str, cuerpo: dict[str, object] | None
) -> None:
    cliente = TestClient(app)
    r = cliente.request(metodo.upper(), ruta, json=cuerpo)
    assert r.status_code == 401


def test_recorrido_del_panel(gerente: TestClient) -> None:
    r = gerente.post(
        "/admin/api/grupos-opciones",
        json={
            "nombre": "Punto de la carne",
            "minimo": 1,
            "maximo": 1,
            "opciones": [{"nombre": "Poco hecha"}, {"nombre": "Al punto"}],
        },
    )
    assert r.status_code == 201
    grupo = r.json()

    r = gerente.put(f"/admin/api/categorias/{CATEGORIA}/destino", json={"destino": "barra"})
    assert r.status_code == 204

    r = gerente.put(
        f"/admin/api/platos/{PLATO}/pedido",
        json={
            "destino": "cocina",
            "alcohol": False,
            "formatos": [{"nombre": "Media", "precio": 9}, {"nombre": "Entera", "precio": 16}],
            "grupos": [grupo["id"]],
        },
    )
    assert r.status_code == 200

    config = gerente.get("/admin/api/productos").json()
    assert config["destinos_categoria"][CATEGORIA] == "barra"
    assert config["platos"][PLATO]["destino"] == "cocina"
    assert config["platos"][PLATO]["grupos"] == [grupo["id"]]
    assert any(g["id"] == grupo["id"] for g in config["grupos"])

    # La carta del cliente ensena los formatos, sin los extras.
    plato = next(p for p in TestClient(app).get("/carta").json() if p["id"] == PLATO)
    assert plato["formatos"] == [
        {"nombre": "Media", "precio": 9},
        {"nombre": "Entera", "precio": 16},
    ]
    assert "grupos" not in plato
    # Y en ingles tambien, con los formatos sin traducir.
    plato_en = next(p for p in TestClient(app).get("/carta?idioma=en").json() if p["id"] == PLATO)
    assert [f["nombre"] for f in plato_en["formatos"]] == ["Media", "Entera"]

    assert gerente.delete(f"/admin/api/grupos-opciones/{grupo['id']}").status_code == 204
    config = gerente.get("/admin/api/productos").json()
    assert config["platos"][PLATO]["grupos"] == []


def test_errores_del_panel(gerente: TestClient) -> None:
    r = gerente.put("/admin/api/platos/plato-que-no-existe/pedido", json={})
    assert r.status_code == 404
    r = gerente.put(f"/admin/api/platos/{PLATO}/pedido", json={"grupos": ["grupo-inventado"]})
    assert r.status_code == 400
    r = gerente.put("/admin/api/categorias/no-existe/destino", json={"destino": "barra"})
    assert r.status_code == 404
    r = gerente.put(f"/admin/api/categorias/{CATEGORIA}/destino", json={"destino": "terraza"})
    assert r.status_code == 422
    r = gerente.put(
        f"/admin/api/platos/{PLATO}/pedido", json={"formatos": [{"nombre": "Tapa", "precio": 0}]}
    )
    assert r.status_code == 422
    malo = {"nombre": "X", "minimo": 2, "maximo": 1, "opciones": [{"nombre": "Y"}]}
    assert gerente.post("/admin/api/grupos-opciones", json=malo).status_code == 422
    bueno = {"nombre": "X", "opciones": [{"nombre": "Y"}]}
    assert gerente.put("/admin/api/grupos-opciones/no-existe", json=bueno).status_code == 404
    assert gerente.delete("/admin/api/grupos-opciones/no-existe").status_code == 404


def test_el_gerente_de_otro_restaurante_no_ve_ni_toca_estos_grupos(gerente: TestClient) -> None:
    creado = gerente.post(
        "/admin/api/grupos-opciones", json={"nombre": "Salsas", "opciones": [{"nombre": "Brava"}]}
    ).json()

    app.dependency_overrides[_resolver_restaurante] = lambda: "otro-bar"
    ajeno = TestClient(app)
    ajeno.cookies.set(COOKIE_SESION, auth.crear_token_sesion("otro-bar"))
    grupos_ajenos = ajeno.get("/admin/api/productos").json()["grupos"]
    assert all(g["id"] != creado["id"] for g in grupos_ajenos)
    bueno = {"nombre": "Mio", "opciones": [{"nombre": "Y"}]}
    assert ajeno.put(f"/admin/api/grupos-opciones/{creado['id']}", json=bueno).status_code == 404
    assert ajeno.delete(f"/admin/api/grupos-opciones/{creado['id']}").status_code == 404

    app.dependency_overrides[_resolver_restaurante] = lambda: RESTAURANTE_ID
    assert gerente.delete(f"/admin/api/grupos-opciones/{creado['id']}").status_code == 204
