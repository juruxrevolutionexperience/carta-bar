import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from carta_bar.datos import cargar_carta
from carta_bar.llm import MODELO, cliente
from carta_bar.modelos import Plato

IDIOMAS = ["en", "de", "fr"]


class PlatoTraducido(BaseModel):
    nombre: str
    descripcion: str
    ingredientes: list[str]


def huella(plato: Plato) -> str:
    base = plato.nombre + "|" + plato.descripcion + "|" + "|".join(plato.ingredientes)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _ruta_traduccion(restaurante_id: str, idioma: str) -> Path:
    return Path(f"datos/{restaurante_id}/carta.{idioma}.json")


def cargar_traduccion(restaurante_id: str, idioma: str) -> dict[str, dict]:
    ruta = _ruta_traduccion(restaurante_id, idioma)
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {d["id"]: d for d in datos}


def traducir_plato(plato: Plato, idioma: str) -> PlatoTraducido:
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
    return respuesta.parsed_output


def traducir_carta(restaurante_id: str, idioma: str) -> None:
    carta = cargar_carta(restaurante_id)
    existentes = cargar_traduccion(restaurante_id, idioma)

    resultado = []
    traducidos = 0

    for plato in carta:
        h = huella(plato)
        previo = existentes.get(plato.id)

        if previo and previo.get("hash") == h:
            resultado.append(previo)
            continue

        t = traducir_plato(plato, idioma)
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
    print(f"{idioma}: {traducidos} traducidos, {len(carta) - traducidos} sin cambios")


def main() -> None:
    for idioma in IDIOMAS:
        traducir_carta("la-catedral", idioma)


if __name__ == "__main__":
    main()
