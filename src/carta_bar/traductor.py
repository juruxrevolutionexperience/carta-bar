import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from carta_bar.costes import Consumo, ConsumoTotal, medir
from carta_bar.datos import _validar_slug, cargar_carta
from carta_bar.llm import MODELO, cliente
from carta_bar.modelos import Plato
from carta_bar.presupuesto import ControlGasto
from carta_bar.uso import crear_repositorio

IDIOMAS = ["en", "de", "fr"]


class PlatoTraducido(BaseModel):
    nombre: str
    descripcion: str
    ingredientes: list[str]


def huella(plato: Plato) -> str:
    base = plato.nombre + "|" + plato.descripcion + "|" + "|".join(plato.ingredientes)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _ruta_traduccion(restaurante_id: str, idioma: str) -> Path:
    _validar_slug(restaurante_id, "restaurante_id")
    _validar_slug(idioma, "idioma")
    return Path(f"datos/{restaurante_id}/carta.{idioma}.json")


def cargar_traduccion(restaurante_id: str, idioma: str) -> dict[str, dict[str, object]]:
    ruta = _ruta_traduccion(restaurante_id, idioma)
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {d["id"]: d for d in datos}


def traducir_plato(plato: Plato, idioma: str) -> tuple[PlatoTraducido, Consumo]:
    c = cliente()
    nombres = {"en": "inglés", "de": "alemán", "fr": "francés"}
    respuesta = c.messages.parse(
        model=MODELO,
        max_tokens=500,
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
                    "- Usa vocabulario gastronómico natural, no traducción literal.\n\n"
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
    return respuesta.parsed_output, medir(f"traduccion:{idioma}", respuesta.usage)


def traducir_carta(restaurante_id: str, idioma: str) -> ConsumoTotal:
    carta = cargar_carta(restaurante_id)
    existentes = cargar_traduccion(restaurante_id, idioma)

    resultado = []
    traducidos = 0
    consumo = ConsumoTotal()

    for plato in carta:
        h = huella(plato)
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

    ruta = _ruta_traduccion(restaurante_id, idioma)
    ruta.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"{idioma}: {traducidos} traducidos, {len(carta) - traducidos} sin cambios "
        f"- ${consumo.coste_usd:.4f}"
    )
    return consumo


def main() -> None:
    """Traducir es gasto real: se contabiliza igual que las preguntas."""
    restaurante_id = "la-catedral"
    control = ControlGasto(crear_repositorio())
    total = ConsumoTotal()

    for idioma in IDIOMAS:
        total.consumos.extend(traducir_carta(restaurante_id, idioma).consumos)

    control.registrar(restaurante_id, MODELO, total)
    print(f"\nTotal traduccion: ${total.coste_usd:.4f} ({len(total.consumos)} llamadas)")


if __name__ == "__main__":
    main()
