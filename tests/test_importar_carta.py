"""Importador de carta desde una foto: herramienta de superadmin, el gerente
no la ve. Lee y propone (POST .../leer-carta); crear categorias y platos usa
los mismos endpoints de siempre, solo que con sesion de superadmin y para un
restaurante cualquiera."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from carta_bar import auth
from carta_bar.api import COOKIE_SESION_SUPERADMIN, TOKEN_SUPERADMIN, app
from carta_bar.costes import Consumo
from carta_bar.importador import PlatoLeido, leer_platos_de_foto
from carta_bar.llm import MODELO_TRADUCCION
from carta_bar.modelos import Categoria, Plato

JPEG_VALIDO = b"\xff\xd8\xff" + b"\x00" * 100
ARCHIVO = {"foto": ("carta.jpg", JPEG_VALIDO, "image/jpeg")}


@pytest.fixture
def guardado() -> dict[str, object]:
    return {}


@pytest.fixture
def _datos(monkeypatch: pytest.MonkeyPatch, guardado: dict[str, object]) -> None:
    monkeypatch.setattr("carta_bar.api._restaurante_existe", lambda rid: rid != "no-existe")
    monkeypatch.setattr("carta_bar.api.cargar_categorias", lambda rid: [])

    def _crear_cat(rid: str, nombre: str) -> Categoria:
        guardado["categoria"] = (rid, nombre)
        return Categoria(id="tostas", nombre=nombre, nombre_i18n={}, orden=1)

    def _crear_plato(rid: str, categoria: str, nombre: str, *resto: object, **kw: object) -> Plato:
        guardado["plato"] = (rid, categoria, nombre)
        return Plato(
            id="p1",
            categoria=categoria,
            nombre=nombre,
            descripcion="",
            precio=None,
            ingredientes=[],
            alergenos=[],
        )

    monkeypatch.setattr("carta_bar.api.crear_categoria", _crear_cat)
    monkeypatch.setattr("carta_bar.api.crear_plato", _crear_plato)
    monkeypatch.setattr("carta_bar.api.traducir_restaurante", lambda rid, control: None)
    # Presupuesto de sobra salvo que un test concreto lo cambie.
    monkeypatch.setattr("carta_bar.api.control.hay_presupuesto", lambda rid: True)
    monkeypatch.setattr("carta_bar.api.control.registrar", lambda rid, modelo, consumo: None)


@pytest.fixture
def superadmin(_datos: None) -> TestClient:
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION_SUPERADMIN, auth.crear_token_sesion(TOKEN_SUPERADMIN))
    return c


# ---------------------------------------------------------------- sesion


def test_todo_exige_sesion_de_superadmin(_datos: None) -> None:
    sin = TestClient(app)
    assert (
        sin.post("/superadmin/api/restaurantes/bar2/leer-carta", files=ARCHIVO).status_code == 401
    )
    assert sin.get("/superadmin/api/restaurantes/bar2/categorias").status_code == 401
    assert (
        sin.post(
            "/superadmin/api/restaurantes/bar2/categorias", json={"nombre": "Tostas"}
        ).status_code
        == 401
    )
    cuerpo = {
        "nombre": "Tosta",
        "descripcion": "Pan con algo",
        "precio": None,
        "categoria": "tostas",
    }
    assert sin.post("/superadmin/api/restaurantes/bar2/platos", json=cuerpo).status_code == 401


def test_restaurante_inexistente_da_404(superadmin: TestClient) -> None:
    assert superadmin.get("/superadmin/api/restaurantes/no-existe/categorias").status_code == 404
    r = superadmin.post("/superadmin/api/restaurantes/no-existe/leer-carta", files=ARCHIVO)
    assert r.status_code == 404


# ----------------------------------------------------------------- leer


def test_leer_carta_sin_presupuesto_da_429(
    superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("carta_bar.api.control.hay_presupuesto", lambda rid: False)
    r = superadmin.post("/superadmin/api/restaurantes/bar2/leer-carta", files=ARCHIVO)
    assert r.status_code == 429


def test_leer_carta_rechaza_un_archivo_que_no_es_jpeg(superadmin: TestClient) -> None:
    r = superadmin.post(
        "/superadmin/api/restaurantes/bar2/leer-carta",
        files={"foto": ("carta.jpg", b"esto no es una foto", "image/jpeg")},
    )
    assert r.status_code == 400


def test_leer_carta_devuelve_los_platos_leidos(
    superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    leidos = [
        PlatoLeido(
            nombre="Tosta de Salmón",
            descripcion="Salmón, aguacate y eneldo",
            ingredientes=["salmón", "aguacate"],
            precio=4.5,
        ),
        PlatoLeido(
            nombre="Tosta de Jamón",
            descripcion="Jamón ibérico y tomate",
            ingredientes=["jamón", "tomate"],
            precio=None,
        ),
    ]
    monkeypatch.setattr(
        "carta_bar.api.leer_platos_de_foto",
        lambda contenido: (leidos, Consumo(llamada="importar_carta", coste_usd=0.01)),
    )
    r = superadmin.post("/superadmin/api/restaurantes/bar2/leer-carta", files=ARCHIVO)
    assert r.status_code == 200
    datos = r.json()
    assert len(datos) == 2
    assert datos[0]["nombre"] == "Tosta de Salmón"
    assert datos[1]["precio"] is None


def test_leer_carta_con_error_del_modelo_da_502(
    superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _falla(contenido: bytes) -> tuple[list[PlatoLeido], object]:
        raise ValueError("no se pudo leer")

    monkeypatch.setattr("carta_bar.api.leer_platos_de_foto", _falla)
    r = superadmin.post("/superadmin/api/restaurantes/bar2/leer-carta", files=ARCHIVO)
    assert r.status_code == 502


# ------------------------------------------------------------- categorias


def test_crea_una_categoria_en_el_restaurante_indicado(
    superadmin: TestClient, guardado: dict[str, object]
) -> None:
    r = superadmin.post("/superadmin/api/restaurantes/bar2/categorias", json={"nombre": "Tostas"})
    assert r.status_code == 201
    assert guardado["categoria"] == ("bar2", "Tostas")


# ------------------------------------------------------------------ platos


def test_crea_un_plato_en_el_restaurante_indicado_y_lanza_la_traduccion(
    superadmin: TestClient, guardado: dict[str, object]
) -> None:
    cuerpo = {
        "nombre": "Tosta de Salmón",
        "descripcion": "Salmón, aguacate y eneldo",
        "precio": 4.5,
        "categoria": "tostas",
        "ingredientes": ["salmón", "aguacate"],
    }
    r = superadmin.post("/superadmin/api/restaurantes/bar2/platos", json=cuerpo)
    assert r.status_code == 201
    assert guardado["plato"] == ("bar2", "tostas", "Tosta de Salmón")
    # Igual que si lo hubiera creado el gerente a mano: entra sin confirmar.
    assert r.json()["categoria"] == "tostas"


def test_leer_platos_de_foto_llama_al_modelo_de_traduccion(monkeypatch: pytest.MonkeyPatch) -> None:
    from carta_bar import importador

    llamadas = []

    class ClienteFalso:
        @property
        def messages(self) -> "ClienteFalso":
            return self

        def parse(self, **k: object) -> SimpleNamespace:
            llamadas.append(k)
            return SimpleNamespace(
                parsed_output=importador.CartaLeida(
                    platos=[
                        importador.PlatoLeido(
                            nombre="Tosta de Salmón",
                            descripcion="Salmón y aguacate",
                            ingredientes=["salmón", "aguacate"],
                            precio=4.5,
                        )
                    ]
                ),
                usage=SimpleNamespace(
                    input_tokens=500,
                    output_tokens=200,
                    cache_creation_input_tokens=0,
                    cache_read_input_tokens=0,
                ),
            )

    monkeypatch.setattr(importador, "cliente", lambda: ClienteFalso())
    platos, consumo = leer_platos_de_foto(JPEG_VALIDO)
    assert platos[0].nombre == "Tosta de Salmón"
    assert llamadas[0]["model"] == MODELO_TRADUCCION
    assert llamadas[0]["thinking"] == {"type": "disabled"}
    contenido = llamadas[0]["messages"][0]["content"]  # type: ignore[index]
    assert contenido[0]["type"] == "image"
    assert consumo.coste_usd > 0
