import json
from pathlib import Path

from carta_bar.modelos import Plato

CARTA = Path("datos/carta.json")


def cargar_carta() -> list[Plato]:
    datos = json.loads(CARTA.read_text(encoding="utf-8"))
    return [Plato.model_validate(plato) for plato in datos]
