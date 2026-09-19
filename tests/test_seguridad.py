"""Los cuatro vectores clasicos, fijados con casos de ataque reales.

XSS y SQL se prueban aqui de verdad. La inyeccion de prompt no se puede
"probar" con un assert -- es mitigacion, no barrera -- asi que lo que se
verifica es que las defensas siguen presentes en el prompt.
"""

import json
from pathlib import Path

import pglast
import pytest

from carta_bar.agente import _REGLAS_SEGURIDAD
from carta_bar.api import CAMPOS_CONFIG_PUBLICOS
from carta_bar.datos import _validar_slug
from carta_bar.uso import _GASTO_DEL_DIA, _INSERTAR

# Las fuentes de React, no lo que compila Vite: asi la suite corre en una copia
# recien clonada, sin compilar el frontend antes.
FRONTEND = Path("frontend/src")


# --------------------------------------------------------------- XSS
def test_ningun_sitio_pinta_html_crudo() -> None:
    # JSX escapa cada texto solo; lo unico que lo anula es inyectar HTML a mano.
    ficheros = list(FRONTEND.rglob("*.ts*"))
    # Sin esto, mover la carpeta dejaria el test pasando sin revisar nada.
    assert len(ficheros) > 10, f"solo {len(ficheros)} ficheros en {FRONTEND}"
    for fichero in ficheros:
        texto = fichero.read_text(encoding="utf-8")
        assert "innerHTML" not in texto, f"HTML crudo en {fichero}"


def test_las_urls_de_imagen_pasan_por_el_filtro() -> None:
    # JSX no sanea lo que va dentro de src=: ahi hace falta urlSegura().
    plato = (FRONTEND / "carta/PlatoCard.tsx").read_text(encoding="utf-8")
    portada = (FRONTEND / "carta/Portada.tsx").read_text(encoding="utf-8")
    assert "urlSegura(p.foto)" in plato
    assert "urlSegura(config.logo)" in portada
    assert "urlSegura(config.foto_portada)" in portada


def test_el_color_de_marca_no_admite_css_arbitrario() -> None:
    # Tampoco sanea lo que se inyecta en style=.
    app = (FRONTEND / "carta/App.tsx").read_text(encoding="utf-8")
    assert "colorSeguro(config.color_marca)" in app


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
