import os
import sys
import threading

import structlog
from pydantic import BaseModel

from carta_bar.costes import Consumo, ConsumoTotal, medir
from carta_bar.datos import cargar_carta, cargar_traducciones, guardar_traducciones
from carta_bar.llm import MODELO_TRADUCCION, cliente
from carta_bar.modelos import Plato, huella_texto
from carta_bar.presupuesto import ControlGasto
from carta_bar.uso import crear_repositorio

log = structlog.get_logger()

IDIOMAS = ["en", "de", "fr"]


class PlatoTraducido(BaseModel):
    nombre: str
    descripcion: str
    ingredientes: list[str]


def traducir_plato(plato: Plato, idioma: str) -> tuple[PlatoTraducido, Consumo]:
    c = cliente()
    nombres = {"en": "inglés", "de": "alemán", "fr": "francés"}
    respuesta = c.messages.parse(
        model=MODELO_TRADUCCION,
        max_tokens=1000,
        # Traducir un plato no necesita razonar; sin esto, Sonnet 5 piensa por
        # defecto y ese pensamiento se paga como salida.
        thinking={"type": "disabled"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Traduce este plato de un restaurante español al {nombres[idioma]}.\n\n"
                    "Reglas:\n"
                    "- Si el nombre es un plato tradicional español reconocible "
                    "(rabo de toro, paella, gazpacho, salmorejo), MANTENLO en español.\n"
                    "- Si el nombre es simplemente una lista de ingredientes, tradúcelo.\n"
                    "- La descripción y los ingredientes SIEMPRE se traducen.\n"
                    "- Usa vocabulario gastronómico natural, no traducción literal.\n"
                    "- Usa el término EXACTO y habitual del idioma destino, sobre todo en "
                    "pescados, mariscos, carnes, quesos y productos típicos (p. ej. 'lubina' "
                    "es 'Wolfsbarsch' en alemán, 'sea bass' en inglés y 'bar' en francés; "
                    "'lenguado' es otro pescado distinto). No cambies una especie o un "
                    "ingrediente por otro parecido.\n"
                    "- Nunca inventes una palabra ni mezcles idiomas dentro de la traducción. "
                    "Si no conoces el término exacto, deja la palabra española tal cual.\n\n"
                    f"Nombre: {plato.nombre}\n"
                    f"Descripción: {plato.descripcion}\n"
                    f"Ingredientes: {', '.join(plato.ingredientes)}"
                ),
            }
        ],
        output_format=PlatoTraducido,
    )
    if respuesta.parsed_output is None:
        raise ValueError(f"No se pudo traducir el plato {plato.id}")
    return respuesta.parsed_output, medir(
        f"traduccion:{idioma}", respuesta.usage, MODELO_TRADUCCION
    )


def traducir_carta(restaurante_id: str, idioma: str, forzar: bool = False) -> ConsumoTotal:
    carta = cargar_carta(restaurante_id)
    existentes = {} if forzar else cargar_traducciones(restaurante_id, idioma)

    resultado = []
    traducidos = 0
    consumo = ConsumoTotal()

    for plato in carta:
        h = huella_texto(plato)
        previo = existentes.get(plato.id)

        if previo and previo.get("hash") == h:
            resultado.append(previo)
            continue

        t, gasto = traducir_plato(plato, idioma)
        consumo.consumos.append(gasto)
        resultado.append(
            {
                "id": plato.id,
                "hash": h,
                "nombre": t.nombre,
                "descripcion": t.descripcion,
                "ingredientes": t.ingredientes,
            }
        )
        traducidos += 1
        print(f"  traducido: {plato.nombre}")

    guardar_traducciones(restaurante_id, idioma, resultado)
    print(
        f"{idioma}: {traducidos} traducidos, {len(carta) - traducidos} sin cambios "
        f"- ${consumo.coste_usd:.4f}"
    )
    return consumo


_candados: dict[str, threading.Lock] = {}


def traducir_restaurante(restaurante_id: str, control: ControlGasto) -> None:
    """Traduce a los 3 idiomas lo que haya cambiado, tras guardar desde el panel.

    Se lanza en segundo plano: el gerente no espera al LLM. El hash de cada
    plato hace que solo se pague lo que cambio, asi que llamarla de mas sale
    gratis. Nunca lanza: una traduccion fallida no debe convertirse en un error
    ya despues de haber guardado el plato.
    """
    # Un candado por restaurante: dos guardados seguidos traducirian a la vez
    # el mismo plato y lo pagarian dos veces.
    with _candados.setdefault(restaurante_id, threading.Lock()):
        if not control.hay_presupuesto(restaurante_id):
            log.warning("traduccion_omitida_sin_presupuesto", restaurante_id=restaurante_id)
            return

        total = ConsumoTotal()
        for idioma in IDIOMAS:
            try:
                total.consumos.extend(traducir_carta(restaurante_id, idioma).consumos)
            except Exception as e:
                log.error(
                    "traduccion_fallida",
                    restaurante_id=restaurante_id,
                    idioma=idioma,
                    motivo=str(e),
                )
        if total.consumos:
            control.registrar(restaurante_id, MODELO_TRADUCCION, total)
            log.info(
                "traduccion_hecha",
                restaurante_id=restaurante_id,
                llamadas=len(total.consumos),
                coste_usd=round(total.coste_usd, 6),
            )


def main() -> None:
    """Traducir es gasto real: se contabiliza igual que las preguntas.

    `--forzar` rehace todas las traducciones aunque el texto no haya cambiado: el
    hash solo mira el español, asi que sin esto un cambio de modelo o de
    instrucciones nunca llegaria a las traducciones ya guardadas."""
    restaurante_id = os.getenv("RESTAURANTE_ID", "la-catedral")
    forzar = "--forzar" in sys.argv[1:]
    control = ControlGasto(crear_repositorio())
    total = ConsumoTotal()

    for idioma in IDIOMAS:
        total.consumos.extend(traducir_carta(restaurante_id, idioma, forzar=forzar).consumos)

    control.registrar(restaurante_id, MODELO_TRADUCCION, total)
    print(f"\nTotal traduccion: ${total.coste_usd:.4f} ({len(total.consumos)} llamadas)")


if __name__ == "__main__":
    main()
