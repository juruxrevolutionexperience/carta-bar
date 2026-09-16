"""La interfaz es un HTML con JS en linea: sin esto, un fallo de sintaxis
solo se descubre abriendo el navegador. Y una traduccion que falta se ve
como una clave cruda en pantalla, delante del cliente.
"""

import json
import re
from pathlib import Path

import esprima
import pytest

INDICE = Path("web/index.html")
IDIOMAS = Path("datos/idiomas.json")
# El panel de admin (login + pantalla completa) ya esta migrado a React,
# compilado con Vite (frontend/): sin JS inline que revisar aqui.


def javascript(ruta: Path = INDICE) -> str:
    html = ruta.read_text(encoding="utf-8")
    js = "\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))
    # esprima llega a ES2017 y no conoce el catch sin variable (ES2019),
    # que los navegadores soportan desde 2018. Se adapta solo para analizar.
    return js.replace("}catch{", "}catch(_e){").replace("} catch {", "} catch (_e) {")


def test_el_javascript_de_la_interfaz_no_tiene_errores_de_sintaxis() -> None:
    esprima.parseScript(javascript())


def test_el_boton_de_voz_nace_oculto() -> None:
    # Mejora progresiva: si el navegador no reconoce voz o el JS falla,
    # no debe quedarse un boton muerto en la barra.
    html = INDICE.read_text(encoding="utf-8")
    assert 'id="microfono"' in html
    assert re.search(r'<button[^>]*id="microfono"[^>]*\shidden', html)


def test_el_boton_de_voz_no_envia_el_formulario() -> None:
    # Sin type="button" dentro de un <form>, el navegador lo trata como submit.
    html = INDICE.read_text(encoding="utf-8")
    boton = re.search(r"<button[^>]*id=\"microfono\"[^>]*>", html)
    assert boton is not None
    assert 'type="button"' in boton.group()


def test_el_dictado_respeta_el_tope_del_backend() -> None:
    # Si el navegador dictase mas de 500 caracteres, el backend lo rechazaria.
    assert "slice(0, 500)" in javascript()


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
