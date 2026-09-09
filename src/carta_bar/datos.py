import json
from pathlib import Path

from carta_bar.modelos import Categoria, Plato


def _ruta_carta(restaurante_id: str) -> Path:
    return Path(f"datos/{restaurante_id}/carta.json")


def _ruta_categorias(restaurante_id: str) -> Path:
    return Path(f"datos/{restaurante_id}/categorias.json")


def cargar_categorias(restaurante_id: str) -> list[Categoria]:
    datos = json.loads(_ruta_categorias(restaurante_id).read_text(encoding="utf-8"))
    return [Categoria.model_validate(c) for c in datos]


def cargar_carta(restaurante_id: str) -> list[Plato]:
    categorias_validas = {c.id for c in cargar_categorias(restaurante_id)}
    datos = json.loads(_ruta_carta(restaurante_id).read_text(encoding="utf-8"))
    platos = [Plato.model_validate(p) for p in datos]

    for plato in platos:
        if plato.categoria not in categorias_validas:
            raise ValueError(
                f"El plato '{plato.nombre}' tiene categoria '{plato.categoria}' "
                f"que no existe en categorias.json"
            )
    return platos
