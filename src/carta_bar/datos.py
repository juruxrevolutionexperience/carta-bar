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


def cargar_carta_traducida(restaurante_id: str, idioma: str) -> list[dict[str, object]]:
    carta = cargar_carta(restaurante_id)
    base = [p.model_dump() for p in carta]

    if idioma == "es":
        return base

    ruta = Path(f"datos/{restaurante_id}/carta.{idioma}.json")
    if not ruta.exists():
        return base

    trad = {d["id"]: d for d in json.loads(ruta.read_text(encoding="utf-8"))}

    for plato in base:
        t = trad.get(plato["id"])
        if t:
            plato["nombre"] = t["nombre"]
            plato["descripcion"] = t["descripcion"]
            plato["ingredientes"] = t["ingredientes"]
    return base
