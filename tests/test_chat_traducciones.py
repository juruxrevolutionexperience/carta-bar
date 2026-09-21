"""El chat usa las traducciones guardadas de la carta (las que ve el cliente en
pantalla) en lugar de traducir el por su cuenta, y el traductor usa un modelo
mejor porque traduce una sola vez por plato."""

from types import SimpleNamespace

import numpy as np
import pytest

from carta_bar import agente, traductor
from carta_bar.api import RESTAURANTE_ID
from carta_bar.costes import Consumo, calcular_coste
from carta_bar.llm import MODELO_TRADUCCION
from carta_bar.modelos import Plato, RestriccionesCliente, huella_texto


def plato(id: str, **campos: object) -> Plato:
    datos: dict[str, object] = {
        "id": id,
        "categoria": "cocina",
        "nombre": f"Lubina {id}",
        "descripcion": "Lomo de lubina con salsa al cava",
        "ingredientes": ["lubina", "cava"],
        "alergenos": [],
    }
    return Plato.model_validate({**datos, **campos})


def traduccion(p: Plato, **cambios: object) -> dict[str, dict[str, object]]:
    fila: dict[str, object] = {
        "id": p.id,
        "hash": huella_texto(p),
        "nombre": "Wolfsbarsch al Cava",
        "descripcion": "Wolfsbarschfilet mit Cava-Sauce",
        "ingredientes": ["Wolfsbarschfilet", "Cava-Sauce"],
    }
    return {p.id: {**fila, **cambios}}


# ------------------------------------------------------------------ costes por modelo


def test_haiku_sigue_siendo_la_tarifa_por_defecto() -> None:
    # 1000 * 1$/M + 500 * 5$/M, como siempre.
    assert calcular_coste(1000, 500) == pytest.approx(0.0035)


def test_sonnet_5_cuesta_el_doble_que_haiku() -> None:
    assert calcular_coste(1000, 500, modelo="claude-sonnet-5") == pytest.approx(0.007)


def test_un_modelo_desconocido_se_cobra_a_la_tarifa_mas_cara_conocida() -> None:
    # Anotar de menos dejaria pasar el tope diario de gasto sin darse cuenta.
    desconocido = calcular_coste(1000, 500, modelo="claude-modelo-nuevo")
    assert desconocido >= calcular_coste(1000, 500, modelo="claude-sonnet-5")


def test_el_modelo_de_traduccion_tiene_precio_conocido() -> None:
    from carta_bar.costes import PRECIOS_POR_MODELO

    assert MODELO_TRADUCCION in PRECIOS_POR_MODELO


# ------------------------------------------------------------------ traductor


class ClienteFalso:
    def __init__(self) -> None:
        self.llamadas: list[dict[str, object]] = []

    @property
    def messages(self) -> "ClienteFalso":
        return self

    def parse(self, **k: object) -> SimpleNamespace:
        self.llamadas.append(k)
        return SimpleNamespace(
            parsed_output=traductor.PlatoTraducido(nombre="n", descripcion="d", ingredientes=["i"]),
            usage=SimpleNamespace(
                input_tokens=100,
                output_tokens=50,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            ),
        )


def test_traduce_con_el_modelo_de_traduccion_y_sin_pensar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    falso = ClienteFalso()
    monkeypatch.setattr(traductor, "cliente", lambda: falso)
    _, gasto = traductor.traducir_plato(plato("a"), "de")
    llamada = falso.llamadas[0]
    assert llamada["model"] == MODELO_TRADUCCION
    assert llamada["thinking"] == {"type": "disabled"}
    # El coste se calcula con la tarifa de ese modelo, no con la de Haiku.
    assert gasto.coste_usd == pytest.approx(calcular_coste(100, 50, modelo=MODELO_TRADUCCION))


@pytest.fixture
def carta_traducida(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    p = plato("a")
    estado: dict[str, object] = {"guardado": None, "traducidos": 0}
    monkeypatch.setattr(traductor, "cargar_carta", lambda rid: [p])
    monkeypatch.setattr(traductor, "cargar_traducciones", lambda rid, idioma: traduccion(p))

    def guardar(rid: str, idioma: str, filas: list[dict[str, object]]) -> None:
        estado["guardado"] = filas

    def traducir(plato_: Plato, idioma: str) -> tuple[traductor.PlatoTraducido, Consumo]:
        estado["traducidos"] = int(estado["traducidos"]) + 1  # type: ignore[call-overload]
        return (
            traductor.PlatoTraducido(nombre="nuevo", descripcion="nuevo", ingredientes=[]),
            Consumo(llamada="traduccion:de"),
        )

    monkeypatch.setattr(traductor, "guardar_traducciones", guardar)
    monkeypatch.setattr(traductor, "traducir_plato", traducir)
    return estado


def test_sin_forzar_no_se_rehace_lo_que_ya_esta_traducido(
    carta_traducida: dict[str, object],
) -> None:
    traductor.traducir_carta("bar", "de")
    assert carta_traducida["traducidos"] == 0


def test_forzar_rehace_las_traducciones_aunque_el_texto_no_haya_cambiado(
    carta_traducida: dict[str, object],
) -> None:
    # El hash solo mira el español: sin esto, cambiar de modelo o de instrucciones
    # no llegaria nunca a lo ya traducido.
    traductor.traducir_carta("bar", "de", forzar=True)
    assert carta_traducida["traducidos"] == 1
    assert carta_traducida["guardado"][0]["nombre"] == "nuevo"  # type: ignore[index]


# ------------------------------------------------------------------ chat


@pytest.fixture
def chat(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    visto = SimpleNamespace(prompt="", k=0, consultas=[], traducciones={})

    monkeypatch.setattr(agente, "cargar_categorias", lambda rid: [])
    monkeypatch.setattr(
        agente,
        "extraer_restricciones",
        lambda pregunta, cats, historial: (RestriccionesCliente(), Consumo(llamada="interprete")),
    )

    def buscar(texto: str, modelo: object, cand: list[Plato], vec: object, k: int) -> list:
        visto.k = k
        return [(1.0, p) for p in cand[:k]]

    def crear(**k: object) -> SimpleNamespace:
        visto.prompt = str(k["messages"][-1]["content"])  # type: ignore[index]
        return SimpleNamespace(usage=None, content=[], stop_reason="end_turn")

    def cargar(rid: str, idioma: str) -> dict[str, dict[str, object]]:
        visto.consultas.append((rid, idioma))
        if isinstance(visto.traducciones, Exception):
            raise visto.traducciones
        return visto.traducciones

    monkeypatch.setattr(agente, "buscar_platos", buscar)
    monkeypatch.setattr(agente, "cargar_traducciones", cargar)
    monkeypatch.setattr(
        agente, "cliente", lambda: SimpleNamespace(messages=SimpleNamespace(create=crear))
    )
    monkeypatch.setattr(agente, "medir", lambda nombre, usage: Consumo(llamada=nombre))
    monkeypatch.setattr(agente, "texto_de_respuesta", lambda r: "ok")
    return visto


def preguntar(carta: list[Plato], idioma: str) -> None:
    agente.responder_cliente(
        "algo de pescado", None, carta, np.zeros((len(carta), 1)), RESTAURANTE_ID, idioma  # type: ignore[arg-type]
    )


def test_el_chat_usa_la_traduccion_guardada_en_el_idioma_del_cliente(
    chat: SimpleNamespace,
) -> None:
    p = plato("a")
    chat.traducciones = traduccion(p)
    preguntar([p], "de")
    assert "Wolfsbarsch al Cava" in chat.prompt
    assert "Wolfsbarschfilet mit Cava-Sauce" in chat.prompt
    assert "Lomo de lubina" not in chat.prompt
    assert chat.consultas == [(RESTAURANTE_ID, "de")]


def test_una_traduccion_de_un_texto_anterior_se_descarta(chat: SimpleNamespace) -> None:
    p = plato("a")
    chat.traducciones = traduccion(p, hash="de-otra-version")
    preguntar([p], "de")
    assert "Wolfsbarsch" not in chat.prompt
    assert "Lomo de lubina con salsa al cava" in chat.prompt


def test_en_español_no_se_consultan_traducciones(chat: SimpleNamespace) -> None:
    preguntar([plato("a")], "es")
    assert chat.consultas == []


def test_si_no_se_pueden_leer_las_traducciones_el_chat_sigue_con_el_español(
    chat: SimpleNamespace,
) -> None:
    chat.traducciones = RuntimeError("la base de datos no responde")
    preguntar([plato("a")], "en")
    assert "Lomo de lubina con salsa al cava" in chat.prompt


def test_un_plato_sin_traduccion_sale_en_español(chat: SimpleNamespace) -> None:
    a, b = plato("a"), plato("b")
    chat.traducciones = traduccion(a)
    preguntar([a, b], "de")
    assert "Wolfsbarsch al Cava" in chat.prompt
    assert "Lubina b" in chat.prompt


# ------------------------------------------------------------------ cuantos platos


def test_se_pasan_hasta_15_platos_y_no_10(chat: SimpleNamespace) -> None:
    # Con 10, un celiaco veia 10 de 13 platos sin gluten y el chat decia "todas".
    preguntar([plato(f"p{i}") for i in range(20)], "es")
    assert chat.k == agente.MAX_PLATOS_EN_CONTEXTO == 15


def test_con_pocos_platos_se_pasan_todos(chat: SimpleNamespace) -> None:
    preguntar([plato(f"p{i}") for i in range(4)], "es")
    assert chat.k == 4


def test_el_limite_de_tokens_cubre_15_platos() -> None:
    # 10 platos piden ~410 tokens (medido); 15, ~600. Con margen para el aleman.
    assert agente.MAX_TOKENS_RESPUESTA >= 800

