"""Valida el SQL con el parser real de PostgreSQL (libpg_query, via pglast).

Esto NO sustituye a probar contra un servidor: no comprueba que las tablas
existan ni que los tipos cuadren en ejecucion. Lo que si garantiza es que no
haya un error de sintaxis esperando al primer despliegue.
"""

import re
from pathlib import Path

import pglast
import pytest

from carta_bar.mesas import (
    _ANADIR_COMENSAL,
    _CERRAR_CADUCADAS,
    _COMENSALES_DE_SESION,
    _CREAR_SESION,
    _SESION_ABIERTA,
    _SESIONES_DEL_LOCAL,
)
from carta_bar.metricas import (
    _LEER_COSTES,
    _LEER_PREGUNTAS,
    _LEER_VISITAS,
    _SUMAR_PREGUNTA,
    _SUMAR_VISITA,
)
from carta_bar.uso import _GASTO_DEL_DIA, _INSERTAR


def a_sintaxis_postgres(sql: str) -> str:
    """psycopg usa %s como marcador; Postgres, $1. Se traduce para poder parsear."""
    contador = 0

    def sustituir(_: re.Match[str]) -> str:
        nonlocal contador
        contador += 1
        return f"${contador}"

    return re.sub(r"%s", sustituir, sql)


def test_el_esquema_es_sql_valido() -> None:
    sql = Path("sql/esquema.sql").read_text(encoding="utf-8")
    assert pglast.parse_sql(sql)


def test_el_esquema_crea_la_tabla_y_su_indice() -> None:
    sql = Path("sql/esquema.sql").read_text(encoding="utf-8")
    arbol = pglast.parse_sql(sql)
    tipos = {type(n.stmt).__name__ for n in arbol}
    assert "CreateStmt" in tipos
    assert "IndexStmt" in tipos


@pytest.mark.parametrize(
    "consulta",
    [
        _INSERTAR,
        _GASTO_DEL_DIA,
        _SUMAR_VISITA,
        _SUMAR_PREGUNTA,
        _LEER_VISITAS,
        _LEER_PREGUNTAS,
        _LEER_COSTES,
        _SESIONES_DEL_LOCAL,
        _SESION_ABIERTA,
        _CREAR_SESION,
        _CERRAR_CADUCADAS,
        _COMENSALES_DE_SESION,
        _ANADIR_COMENSAL,
    ],
)
def test_las_consultas_son_sql_valido(consulta: str) -> None:
    assert pglast.parse_sql(a_sintaxis_postgres(consulta))


@pytest.mark.parametrize("insert", [_INSERTAR, _CREAR_SESION, _ANADIR_COMENSAL])
def test_el_insert_manda_tantos_valores_como_columnas(insert: str) -> None:
    columnas = insert.split("(")[1].split(")")[0].count(",") + 1
    valores = insert.split("VALUES")[1].split("(")[1].split(")")[0].count(",") + 1
    assert columnas == valores, f"{columnas} columnas frente a {valores} valores"


def test_el_esquema_usa_numeric_para_el_dinero() -> None:
    # Con dinero, DOUBLE acumula error de redondeo al sumar miles de filas.
    sql = Path("sql/esquema.sql").read_text(encoding="utf-8").lower()
    assert "coste_usd               numeric" in " ".join(sql.split(" "))


def test_el_esquema_anade_la_columna_de_alergenos_confirmados_sin_romper_lo_existente() -> None:
    # Los platos que ya existian se dan por revisados (default true): si el
    # default fuera false, desplegar esto dejaria toda la carta en "consultar
    # alergenos" de golpe.
    sql = " ".join(Path("sql/esquema.sql").read_text(encoding="utf-8").split())
    assert (
        "ALTER TABLE platos ADD COLUMN IF NOT EXISTS alergenos_confirmados "
        "BOOLEAN NOT NULL DEFAULT true"
    ) in sql


def test_la_conversion_del_plano_se_hace_una_sola_vez() -> None:
    """Las zonas nuevas nacen ya en la version 2: si el default fuera 1, cada
    reinicio volveria a multiplicar las posiciones de las mesas."""
    sql = Path("sql/esquema.sql").read_text(encoding="utf-8")
    anade = sql.index("ADD COLUMN IF NOT EXISTS plano_version INTEGER NOT NULL DEFAULT 1")
    default_nuevo = sql.index("ALTER COLUMN plano_version SET DEFAULT 2")
    convierte = sql.index("WHERE plano_version = 1")
    assert anade < default_nuevo < convierte
    # Marca la zona como convertida en el mismo statement que mueve sus mesas.
    assert "UPDATE zonas SET plano_version = 2" in sql
