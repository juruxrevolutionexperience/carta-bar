"""Gestion de categorias y alta de platos desde el panel:
POST/PUT/DELETE /admin/api/categorias, PUT /admin/api/orden-categorias,
POST /admin/api/platos.

Sin base de datos: se sustituyen las funciones de datos que importa api.py. El
SQL de verdad se probo aparte contra un Postgres real (ver el commit)."""

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, _indices, app
from carta_bar.datos import _validar_slug, id_categoria_libre, id_plato_nuevo, slug_categoria
from carta_bar.modelos import Categoria, Plato

PLATO_VALIDO = {
    "categoria": "postres",
    "nombre": "Flan casero",
    "descripcion": "Con caramelo",
    "precio": 4.5,
    "ingredientes": ["huevo", "leche"],
    "alergenos": ["huevos", "lacteos"],
}


@pytest.fixture
def llamadas() -> dict[str, list[tuple[object, ...]]]:
    return {}


@pytest.fixture
def cliente(
    monkeypatch: pytest.MonkeyPatch, llamadas: dict[str, list[tuple[object, ...]]]
) -> TestClient:
    def anotar(nombre: str, *args: object) -> None:
        llamadas.setdefault(nombre, []).append(args)

    def _crear_categoria(rid: str, nombre: str) -> Categoria:
        anotar("crear_categoria", rid, nombre)
        return Categoria(id="nueva", nombre=nombre, nombre_i18n={}, orden=7)

    def _renombrar(rid: str, cid: str, nombre: str) -> Categoria | None:
        anotar("renombrar", rid, cid, nombre)
        if cid == "no-existe":
            return None
        return Categoria(id=cid, nombre=nombre, nombre_i18n={}, orden=2)

    def _ordenar(rid: str, ids: list[str]) -> bool:
        anotar("ordenar", rid, tuple(ids))
        return ids != ["mal"]

    def _eliminar(rid: str, cid: str) -> str:
        anotar("eliminar", rid, cid)
        return {"no-existe": "no_existe", "con-platos": "con_platos"}.get(cid, "ok")

    def _crear_plato(rid: str, categoria: str, nombre: str, *resto: object) -> Plato | None:
        anotar("crear_plato", rid, categoria, nombre)
        if categoria == "no-existe":
            return None
        return Plato(
            id="plato-0000000001-abcd",
            categoria=categoria,
            nombre=nombre,
            descripcion="d",
            precio=4.5,
            ingredientes=[],
            alergenos=[],
        )

    monkeypatch.setattr("carta_bar.api.crear_categoria", _crear_categoria)
    monkeypatch.setattr("carta_bar.api.renombrar_categoria", _renombrar)
    monkeypatch.setattr("carta_bar.api.ordenar_categorias", _ordenar)
    monkeypatch.setattr("carta_bar.api.eliminar_categoria", _eliminar)
    monkeypatch.setattr("carta_bar.api.crear_plato", _crear_plato)

    def _eliminar_plato(rid: str, pid: str) -> bool:
        anotar("eliminar_plato", rid, pid)
        return pid != "no-existe"

    monkeypatch.setattr("carta_bar.api.eliminar_plato", _eliminar_plato)
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c


# -------------------------------------------------------- sin sesion: nada


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("post", "/admin/api/categorias", {"nombre": "X"}),
        ("put", "/admin/api/categorias/postres", {"nombre": "X"}),
        ("put", "/admin/api/orden-categorias", {"ids": ["a"]}),
        ("delete", "/admin/api/categorias/postres", None),
        ("post", "/admin/api/platos", PLATO_VALIDO),
        ("delete", "/admin/api/platos/plato-1", None),
    ],
)
def test_sin_sesion_se_rechaza_todo(metodo: str, ruta: str, cuerpo: object) -> None:
    r = getattr(TestClient(app), metodo)(ruta, **({"json": cuerpo} if cuerpo else {}))
    assert r.status_code == 401


# -------------------------------------------------------------- categorias


def test_crea_una_categoria(
    cliente: TestClient, llamadas: dict[str, list[tuple[object, ...]]]
) -> None:
    r = cliente.post("/admin/api/categorias", json={"nombre": "Bebidas"})
    assert r.status_code == 201
    assert r.json()["orden"] == 7
    assert llamadas["crear_categoria"] == [(RESTAURANTE_ID, "Bebidas")]


def test_el_nombre_se_limpia_de_espacios(
    cliente: TestClient, llamadas: dict[str, list[tuple[object, ...]]]
) -> None:
    cliente.post("/admin/api/categorias", json={"nombre": "  Postres    y   café "})
    assert llamadas["crear_categoria"][0][1] == "Postres y café"


@pytest.mark.parametrize("nombre", ["", "   ", "???", "---", "a" * 61])
def test_nombres_de_categoria_invalidos_dan_422(cliente: TestClient, nombre: str) -> None:
    assert cliente.post("/admin/api/categorias", json={"nombre": nombre}).status_code == 422
    assert cliente.put("/admin/api/categorias/x", json={"nombre": nombre}).status_code == 422


def test_renombra_una_categoria(
    cliente: TestClient, llamadas: dict[str, list[tuple[object, ...]]]
) -> None:
    r = cliente.put("/admin/api/categorias/postres", json={"nombre": "Dulces"})
    assert r.status_code == 200
    assert r.json()["nombre"] == "Dulces"
    assert llamadas["renombrar"] == [(RESTAURANTE_ID, "postres", "Dulces")]


def test_renombrar_una_que_no_existe_da_404(cliente: TestClient) -> None:
    assert cliente.put("/admin/api/categorias/no-existe", json={"nombre": "X"}).status_code == 404


def test_ordena_las_categorias(
    cliente: TestClient, llamadas: dict[str, list[tuple[object, ...]]]
) -> None:
    r = cliente.put("/admin/api/orden-categorias", json={"ids": ["b", "a"]})
    assert r.status_code == 204
    assert llamadas["ordenar"] == [(RESTAURANTE_ID, ("b", "a"))]


def test_un_orden_que_no_cuadra_da_400(cliente: TestClient) -> None:
    assert cliente.put("/admin/api/orden-categorias", json={"ids": ["mal"]}).status_code == 400


def test_ordenar_sin_lista_da_422(cliente: TestClient) -> None:
    assert cliente.put("/admin/api/orden-categorias", json={}).status_code == 422


def test_elimina_una_categoria_vacia(
    cliente: TestClient, llamadas: dict[str, list[tuple[object, ...]]]
) -> None:
    assert cliente.delete("/admin/api/categorias/postres").status_code == 204
    assert llamadas["eliminar"] == [(RESTAURANTE_ID, "postres")]


def test_eliminar_una_con_platos_da_409_con_explicacion(cliente: TestClient) -> None:
    r = cliente.delete("/admin/api/categorias/con-platos")
    assert r.status_code == 409
    assert "platos" in r.text


def test_eliminar_una_que_no_existe_da_404(cliente: TestClient) -> None:
    assert cliente.delete("/admin/api/categorias/no-existe").status_code == 404


# ------------------------------------------------------------------ platos


def test_crea_un_plato_en_su_categoria(
    cliente: TestClient, llamadas: dict[str, list[tuple[object, ...]]]
) -> None:
    r = cliente.post("/admin/api/platos", json=PLATO_VALIDO)
    assert r.status_code == 201
    assert r.json()["categoria"] == "postres"
    assert llamadas["crear_plato"] == [(RESTAURANTE_ID, "postres", "Flan casero")]


def test_crear_plato_en_categoria_que_no_existe_da_404(cliente: TestClient) -> None:
    r = cliente.post("/admin/api/platos", json={**PLATO_VALIDO, "categoria": "no-existe"})
    assert r.status_code == 404


def test_crear_un_plato_invalida_el_indice_del_chat(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sin esto, el chat no conoceria el plato nuevo hasta el proximo reinicio.
    monkeypatch.setitem(_indices, RESTAURANTE_ID, ([], None))
    cliente.post("/admin/api/platos", json=PLATO_VALIDO)
    assert RESTAURANTE_ID not in _indices


@pytest.mark.parametrize(
    "cambio",
    [
        {"precio": 0},
        {"nombre": ""},
        {"categoria": ""},
        {"sin_gluten": True, "alergenos": ["gluten"]},
    ],
)
def test_crear_plato_invalido_da_422(cliente: TestClient, cambio: dict[str, object]) -> None:
    assert cliente.post("/admin/api/platos", json={**PLATO_VALIDO, **cambio}).status_code == 422


def test_elimina_un_plato_e_invalida_el_indice_del_chat(
    cliente: TestClient,
    llamadas: dict[str, list[tuple[object, ...]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(_indices, RESTAURANTE_ID, ([], None))
    assert cliente.delete("/admin/api/platos/plato-1").status_code == 204
    assert llamadas["eliminar_plato"] == [(RESTAURANTE_ID, "plato-1")]
    assert RESTAURANTE_ID not in _indices


def test_eliminar_un_plato_que_no_existe_da_404(cliente: TestClient) -> None:
    assert cliente.delete("/admin/api/platos/no-existe").status_code == 404


def test_crear_plato_sin_categoria_da_422(cliente: TestClient) -> None:
    cuerpo = {k: v for k, v in PLATO_VALIDO.items() if k != "categoria"}
    assert cliente.post("/admin/api/platos", json=cuerpo).status_code == 422


# ------------------------------------------------------------ helpers puros


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("Postres", "postres"),
        ("Postres y Café", "postres_y_cafe"),
        ("  Niños   ", "ninos"),
        ("Tapas & Raciones", "tapas_raciones"),
        ("Menú 2x1", "menu_2x1"),
        ("???", ""),
        ("", ""),
    ],
)
def test_slug_categoria(nombre: str, esperado: str) -> None:
    assert slug_categoria(nombre) == esperado


def test_id_categoria_libre_evita_los_ocupados() -> None:
    assert id_categoria_libre("postres", set()) == "postres"
    assert id_categoria_libre("postres", {"postres"}) == "postres_2"
    assert id_categoria_libre("postres", {"postres", "postres_2", "postres_3"}) == "postres_4"


def test_los_ids_de_plato_nuevo_valen_para_rutas_de_foto_y_salen_ordenados(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # _ruta_foto pasa el id por _validar_slug: un id que no lo cumpliera dejaria
    # el plato sin poder subirle foto.
    horas = iter([1_000_000_000, 1_000_000_001, 1_000_000_900])
    monkeypatch.setattr("carta_bar.datos.time.time", lambda: next(horas))
    ids = [id_plato_nuevo() for _ in range(3)]
    for i in ids:
        _validar_slug(i, "plato_id")
    assert ids == sorted(ids)
