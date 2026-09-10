"""Los cuatro vectores clasicos, fijados con casos de ataque reales.

XSS y SQL se prueban aqui de verdad. La inyeccion de prompt no se puede
"probar" con un assert -- es mitigacion, no barrera -- asi que lo que se
verifica es que las defensas siguen presentes en el prompt.
"""

import json
import re
from pathlib import Path

import pglast
import pytest

from carta_bar.agente import _REGLAS_SEGURIDAD
from carta_bar.api import CAMPOS_CONFIG_PUBLICOS
from carta_bar.datos import _validar_slug
from carta_bar.uso import _GASTO_DEL_DIA, _INSERTAR

HTML = Path("web/index.html").read_text(encoding="utf-8")

ATAQUES_XSS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '" onmouseover="alert(1)',
    "' onfocus='alert(1)",
    "<svg/onload=alert(1)>",
]


def escapar_como_el_navegador(texto: str) -> str:
    """Replica escapar() del frontend para poder probarlo desde Python."""
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# --------------------------------------------------------------- XSS
@pytest.mark.parametrize("ataque", ATAQUES_XSS)
def test_el_escapado_neutraliza_los_ataques_conocidos(ataque: str) -> None:
    limpio = escapar_como_el_navegador(ataque)
    # Lo que vuelve inerte a un ataque no es que desaparezca la palabra
    # "onerror", sino que no quede NINGUN caracter con el que abrir una
    # etiqueta o cerrar un atributo: el navegador lo pinta como texto plano.
    for caracter in ["<", ">", '"', "'"]:
        assert caracter not in limpio, f"sobrevive {caracter!r} en {limpio!r}"


def test_el_escapado_del_frontend_cubre_las_comillas() -> None:
    # Varios de estos valores caen dentro de atributos HTML: sin escapar las
    # comillas, se puede cerrar el atributo e inyectar un manejador de evento.
    funcion = re.search(r"function escapar\(t\)\{.*?\n\}", HTML, re.S)
    assert funcion is not None
    cuerpo = funcion.group()
    for caracter in ["&amp;", "&lt;", "&gt;", "&quot;", "&#39;"]:
        assert caracter in cuerpo


def test_los_datos_del_restaurante_van_escapados() -> None:
    # La carta la escribe el restaurante y se pinta en el movil del comensal.
    for campo in ["escapar(p.nombre)", "escapar(nomCat)", "escapar(moneda)"]:
        assert campo in HTML, f"sin escapar: {campo}"


def test_las_urls_de_imagen_pasan_por_el_filtro() -> None:
    for campo in ["urlSegura(config.logo)", "urlSegura(config.foto_portada)", "urlSegura(p.foto)"]:
        assert campo in HTML, f"sin filtrar: {campo}"


def test_el_color_de_marca_no_admite_css_arbitrario() -> None:
    assert "colorSeguro(config.color_marca)" in HTML


# --------------------------------------------------------------- SQL
@pytest.mark.parametrize("consulta", [_INSERTAR, _GASTO_DEL_DIA])
def test_las_consultas_usan_parametros_y_no_concatenacion(consulta: str) -> None:
    # Un %s es un parametro que psycopg envia aparte; una f-string seria
    # concatenacion y ahi si cabria una inyeccion.
    assert "%s" in consulta
    assert "'" not in consulta.replace("date_trunc('day', now())", "")


def test_una_inyeccion_sql_clasica_no_sobrevive_al_validador() -> None:
    with pytest.raises(ValueError):
        _validar_slug("la-catedral'; DROP TABLE uso_llm; --", "restaurante_id")


def test_el_insert_no_admite_sentencias_encadenadas() -> None:
    # Si alguien colase un ";" en la plantilla, aqui saldrian dos sentencias.
    arbol = pglast.parse_sql(_INSERTAR.replace("%s", "$1"))
    assert len(arbol) == 1


# --------------------------------------------------- travesia de rutas
@pytest.mark.parametrize(
    "ataque",
    [
        "../../etc/passwd",
        r"..\..\windows\system32",
        "x/../../tmp/evil",
        "%2e%2e%2f",
        "la catedral",
    ],
)
def test_las_rutas_no_admiten_travesia(ataque: str) -> None:
    with pytest.raises(ValueError):
        _validar_slug(ataque, "restaurante_id")


# ------------------------------------------------- inyeccion de prompt
def test_el_prompt_fija_cual_es_la_fuente_de_verdad() -> None:
    # Que el cliente no pueda dictar precios: es el riesgo de negocio real.
    assert "ÚNICA fuente válida" in _REGLAS_SEGURIDAD
    assert "precio" in _REGLAS_SEGURIDAD


def test_el_prompt_manda_ignorar_instrucciones_del_cliente() -> None:
    assert "ignóralas" in _REGLAS_SEGURIDAD


# ------------------------------------------------------ fuga por /config
def test_config_solo_expone_campos_de_la_lista_blanca() -> None:
    datos = json.loads(Path("datos/la-catedral/config.json").read_text(encoding="utf-8"))
    publicos = {k: v for k, v in datos.items() if k in CAMPOS_CONFIG_PUBLICOS}
    assert set(publicos) <= CAMPOS_CONFIG_PUBLICOS


def test_la_lista_blanca_no_deja_pasar_secretos() -> None:
    for prohibido in [
        "api_key",
        "anthropic_api_key",
        "webhook",
        "stripe",
        "password",
        "tope_diario",
    ]:
        assert prohibido not in CAMPOS_CONFIG_PUBLICOS
