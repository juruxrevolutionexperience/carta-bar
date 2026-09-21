"""Un plato cuyos alergenos el restaurante no ha revisado nunca se presenta como
apto: ni en el filtro del chat, ni en lo que se le cuenta al modelo, ni en la
carta. Es lo que hace seguro importar una carta con alergenos adivinados."""

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from carta_bar import agente, auth
from carta_bar.api import COOKIE_SESION, RESTAURANTE_ID, app
from carta_bar.busqueda import (
    exige_confirmacion,
    filtrar_por_restricciones,
    filtrar_por_restricciones_cliente,
)
from carta_bar.costes import Consumo
from carta_bar.modelos import Alergeno, Plato, RestriccionesCliente


def plato(id: str, confirmado: bool = True, **campos: object) -> Plato:
    datos: dict[str, object] = {
        "id": id,
        "categoria": "postres",
        "nombre": f"Plato {id}",
        "descripcion": "d",
        "ingredientes": ["huevo"],
        "alergenos": [],
        "alergenos_confirmados": confirmado,
    }
    return Plato.model_validate({**datos, **campos})


def ids(platos: list[Plato]) -> list[str]:
    return [p.id for p in platos]


# ------------------------------------------------------------------ filtro


def test_sin_restriccion_un_plato_sin_confirmar_se_puede_ofrecer() -> None:
    carta = [plato("a"), plato("b", confirmado=False)]
    assert ids(filtrar_por_restricciones_cliente(carta, RestriccionesCliente())) == ["a", "b"]


def test_un_alergeno_a_evitar_deja_fuera_al_plato_sin_confirmar() -> None:
    # El caso peligroso: alergenos vacios (no revisados) pasaban como "sin lacteos".
    carta = [plato("a", alergenos=[]), plato("b", confirmado=False, alergenos=[])]
    r = RestriccionesCliente(alergenos_excluir=[Alergeno.LACTEOS])
    assert ids(filtrar_por_restricciones_cliente(carta, r)) == ["a"]


@pytest.mark.parametrize("restriccion", ["vegano", "vegetariano", "sin_gluten", "sin_lactosa"])
def test_una_dieta_deja_fuera_al_plato_sin_confirmar(restriccion: str) -> None:
    marcados = {"vegano": True, "vegetariano": True, "sin_gluten": True, "sin_lactosa": True}
    carta = [plato("a", **marcados), plato("b", confirmado=False, **marcados)]
    r = RestriccionesCliente(**{restriccion: True})
    assert ids(filtrar_por_restricciones_cliente(carta, r)) == ["a"]


def test_pedir_una_categoria_o_un_ingrediente_no_exige_confirmacion() -> None:
    # Solo la seguridad (alergia, dieta) exige haber revisado los alergenos.
    carta = [plato("a"), plato("b", confirmado=False)]
    r = RestriccionesCliente(categoria_pedida="postres")
    assert ids(filtrar_por_restricciones_cliente(carta, r)) == ["a", "b"]


def test_exige_confirmacion_solo_con_restricciones_de_seguridad() -> None:
    assert exige_confirmacion(RestriccionesCliente()) is False
    assert exige_confirmacion(RestriccionesCliente(categoria_pedida="postres")) is False
    assert exige_confirmacion(RestriccionesCliente(sin_gluten=True)) is True
    assert exige_confirmacion(RestriccionesCliente(alergenos_excluir=[Alergeno.HUEVOS])) is True


def test_el_filtro_por_palabras_tambien_lo_respeta() -> None:
    carta = [plato("a", sin_gluten=True), plato("b", confirmado=False, sin_gluten=True)]
    assert ids(filtrar_por_restricciones(carta, "algo sin gluten")) == ["a"]
    assert ids(filtrar_por_restricciones(carta, "algo rico")) == ["a", "b"]


# ------------------------------------------------------------------ agente


@pytest.fixture
def modelo_falso(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Sin LLM ni embeddings: registra lo que se le enviaria al modelo."""
    visto = SimpleNamespace(prompt="", llamadas=0, restricciones=RestriccionesCliente())

    monkeypatch.setattr(agente, "cargar_categorias", lambda rid: [])
    monkeypatch.setattr(
        agente,
        "extraer_restricciones",
        lambda pregunta, cats, historial: (visto.restricciones, Consumo(llamada="interprete")),
    )
    monkeypatch.setattr(
        agente,
        "buscar_platos",
        lambda texto, modelo, candidatos, vectores, k: [(1.0, p) for p in candidatos],
    )

    def crear(**k: object) -> SimpleNamespace:
        visto.llamadas += 1
        visto.prompt = str(k["messages"][-1]["content"])  # type: ignore[index]
        return SimpleNamespace(usage=None, content=[])

    monkeypatch.setattr(
        agente, "cliente", lambda: SimpleNamespace(messages=SimpleNamespace(create=crear))
    )
    monkeypatch.setattr(agente, "medir", lambda nombre, usage: Consumo(llamada=nombre))
    monkeypatch.setattr(agente, "texto_de_respuesta", lambda r: "respuesta del modelo")
    return visto


def preguntar(carta: list[Plato], idioma: str = "es") -> agente.RespuestaAgente:
    return agente.responder_cliente(
        "algo sin gluten", None, carta, np.zeros((len(carta), 1)), RESTAURANTE_ID, idioma  # type: ignore[arg-type]
    )


def test_si_solo_quedan_platos_sin_confirmar_manda_al_personal_sin_gastar_llm(
    modelo_falso: SimpleNamespace,
) -> None:
    modelo_falso.restricciones = RestriccionesCliente(sin_gluten=True)
    carta = [plato("a", confirmado=False, sin_gluten=True)]
    frases = (("es", "personal"), ("en", "staff"), ("de", "Personal"), ("fr", "personnel"))
    for idioma, frase in frases:
        r = preguntar(carta, idioma)
        assert frase in r.texto
        assert "no tenemos" not in r.texto.lower()
    assert modelo_falso.llamadas == 0


def test_sin_platos_confirmados_ni_sin_confirmar_sigue_diciendo_que_no_hay(
    modelo_falso: SimpleNamespace,
) -> None:
    modelo_falso.restricciones = RestriccionesCliente(sin_gluten=True)
    carta = [plato("a", sin_gluten=False)]
    assert preguntar(carta).texto == agente.SIN_RESULTADOS["es"]


def test_al_modelo_le_llega_la_nota_de_platos_sin_confirmar(modelo_falso: SimpleNamespace) -> None:
    modelo_falso.restricciones = RestriccionesCliente(sin_gluten=True)
    carta = [plato("a", sin_gluten=True), plato("b", confirmado=False, sin_gluten=True)]
    preguntar(carta)
    assert "aún no ha confirmado" in modelo_falso.prompt
    assert "Plato b" not in modelo_falso.prompt  # ni se lista como opcion


def test_un_plato_sin_confirmar_no_se_describe_como_sin_alergenos(
    modelo_falso: SimpleNamespace,
) -> None:
    # Sin restriccion puede salir en la lista, pero nunca como "Alérgenos: ninguno".
    carta = [plato("b", confirmado=False, alergenos=[])]
    preguntar(carta)
    assert "SIN CONFIRMAR" in modelo_falso.prompt
    assert "Alérgenos: ninguno" not in modelo_falso.prompt


def test_un_plato_confirmado_sin_alergenos_si_es_ninguno(modelo_falso: SimpleNamespace) -> None:
    preguntar([plato("a", alergenos=[])])
    assert "Alérgenos: ninguno" in modelo_falso.prompt
    assert "SIN CONFIRMAR" not in modelo_falso.prompt


# ------------------------------------------------------------------ API del panel


@pytest.fixture
def panel(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, object]]:
    visto: dict[str, object] = {}

    def _actualizar(rid: str, pid: str, *args: object, **claves: object) -> bool:
        visto["editado"] = claves.get("alergenos_confirmados", "sin-clave")
        return True

    def _crear_especial(rid: str, *args: object, **claves: object) -> Plato:
        visto["especial"] = claves.get("alergenos_confirmados", "sin-clave")
        return plato("nuevo")

    def _crear(rid: str, cat: str, *args: object, **claves: object) -> Plato:
        visto["creado"] = claves.get("alergenos_confirmados", "sin-clave")
        return plato("nuevo")

    monkeypatch.setattr("carta_bar.api.actualizar_plato_editable", _actualizar)
    monkeypatch.setattr("carta_bar.api.crear_plato_especial", _crear_especial)
    monkeypatch.setattr("carta_bar.api.crear_plato", _crear)
    c = TestClient(app)
    c.cookies.set(COOKIE_SESION, auth.crear_token_sesion(RESTAURANTE_ID))
    return c, visto


CUERPO = {"nombre": "Flan", "descripcion": "Con caramelo", "precio": 4.5}


def test_un_plato_nuevo_entra_sin_confirmar_por_defecto(
    panel: tuple[TestClient, dict[str, object]],
) -> None:
    cliente, visto = panel
    cliente.post("/admin/api/platos", json={**CUERPO, "categoria": "postres"})
    cliente.post("/admin/api/platos/especiales", json=CUERPO)
    assert visto["creado"] is False
    assert visto["especial"] is False


def test_el_gerente_puede_confirmar_al_crear(panel: tuple[TestClient, dict[str, object]]) -> None:
    cliente, visto = panel
    body = {**CUERPO, "categoria": "postres", "alergenos_confirmados": True}
    cliente.post("/admin/api/platos", json=body)
    assert visto["creado"] is True


def test_editar_sin_mandar_el_campo_no_toca_la_confirmacion(
    panel: tuple[TestClient, dict[str, object]],
) -> None:
    cliente, visto = panel
    assert cliente.put("/admin/api/platos/p1", json=CUERPO).status_code == 204
    assert visto["editado"] is None  # None = "dejar como esta", no "desconfirmar"


def test_editar_puede_confirmar_o_desconfirmar(
    panel: tuple[TestClient, dict[str, object]],
) -> None:
    cliente, visto = panel
    cliente.put("/admin/api/platos/p1", json={**CUERPO, "alergenos_confirmados": True})
    assert visto["editado"] is True
    cliente.put("/admin/api/platos/p1", json={**CUERPO, "alergenos_confirmados": False})
    assert visto["editado"] is False


def test_la_carta_publica_expone_el_campo() -> None:
    assert plato("a", confirmado=False).model_dump()["alergenos_confirmados"] is False
    assert plato("a").model_dump()["alergenos_confirmados"] is True
