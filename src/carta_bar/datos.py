import json
from pathlib import Path

from carta_bar.modelos import Categoria, Plato

CARTA = Path("datos/carta.json")
CATEGORIAS = Path("datos/categorias.json")


def cargar_categorias() -> list[Categoria]:
    datos = json.loads(CATEGORIAS.read_text(encoding="utf-8"))
    return [Categoria.model_validate(c) for c in datos]


def cargar_carta() -> list[Plato]:
    categorias_validas = {c.id for c in cargar_categorias()}
    datos = json.loads(CARTA.read_text(encoding="utf-8"))
    platos = [Plato.model_validate(p) for p in datos]

    for plato in platos:
        if plato.categoria not in categorias_validas:
            raise ValueError(
                f"El plato '{plato.nombre}' tiene categoria '{plato.categoria}' "
                f"que no existe en categorias.json"
            )
    return platos
