"""Valida el SQL con el parser real de PostgreSQL (libpg_query, via pglast).

Esto NO sustituye a probar contra un servidor: no comprueba que las tablas
existan ni que los tipos cuadren en ejecucion. Lo que si garantiza es que no
haya un error de sintaxis esperando al primer despliegue.
"""

import re
from pathlib import Path

import pglast
import pytest

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


@pytest.mark.parametrize("consulta", [_INSERTAR, _GASTO_DEL_DIA])
def test_las_consultas_son_sql_valido(consulta: str) -> None:
    assert pglast.parse_sql(a_sintaxis_postgres(consulta))


def test_el_insert_manda_tantos_valores_como_columnas() -> None:
    columnas = _INSERTAR.split("(")[1].split(")")[0].count(",") + 1
    marcadores = _INSERTAR.count("%s")
    assert columnas == marcadores, f"{columnas} columnas frente a {marcadores} marcadores"


def test_el_esquema_usa_numeric_para_el_dinero() -> None:
    # Con dinero, DOUBLE acumula error de redondeo al sumar miles de filas.
    sql = Path("sql/esquema.sql").read_text(encoding="utf-8").lower()
    assert "coste_usd               numeric" in " ".join(sql.split(" "))
