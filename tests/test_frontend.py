"""Los textos de datos/idiomas.json: una clave que falta o queda vacia se ve
en pantalla delante del cliente, en cualquiera de los tres idiomas.

El HTML/JS de la interfaz (carta publica, login, panel de admin) ya esta
migrado a React, compilado con Vite (frontend/): sin archivos inline que
revisar aqui.
"""

import json
from pathlib import Path

import pytest

IDIOMAS = Path("datos/idiomas.json")


@pytest.mark.parametrize("clave", ["voz_hablar", "voz_parar", "voz_escuchando", "voz_sin_permiso"])
def test_los_textos_de_voz_estan_en_todos_los_idiomas(clave: str) -> None:
    idiomas = json.loads(IDIOMAS.read_text(encoding="utf-8"))
    for codigo, textos in idiomas.items():
        assert clave in textos, f"falta '{clave}' en '{codigo}'"
        assert textos[clave].strip(), f"'{clave}' vacio en '{codigo}'"


def test_ningun_idioma_se_queda_con_claves_a_medias() -> None:
    idiomas = json.loads(IDIOMAS.read_text(encoding="utf-8"))
    referencia = set(idiomas["es"])
    for codigo, textos in idiomas.items():
        faltan = referencia - set(textos)
        assert not faltan, f"a '{codigo}' le faltan: {sorted(faltan)}"
