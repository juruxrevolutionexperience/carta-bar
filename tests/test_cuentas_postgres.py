"""Prueba RepositorioCuentasPostgres contra un Postgres real, igual que
test_comandas_postgres.py: la suite normal usa memoria para todo, asi que un
fallo de psycopg al adaptar `lineas`/`por_persona` (listas de dicts, columnas
JSONB) no lo detecta nada mas.

Requiere `pgserver` (no es dependencia del proyecto, se instala al vuelo):
    uv run --with pgserver pytest tests/test_cuentas_postgres.py -q

Si no esta instalado, se salta sin romper la suite normal.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

pgserver = pytest.importorskip("pgserver")

import psycopg  # noqa: E402

from carta_bar.cuentas import (  # noqa: E402
    Cuenta,
    LineaCuenta,
    OpcionElegida,
    RepositorioCuentasPostgres,
    ResumenPersonaCuenta,
)

T0 = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)
DESDE_SIEMPRE = datetime(2000, 1, 1, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[RepositorioCuentasPostgres]:
    servidor = pgserver.get_server(str(tmp_path / "pgdata"))
    uri = servidor.get_uri()
    with psycopg.connect(uri, autocommit=True) as conn:
        conn.execute(Path("sql/esquema.sql").read_text(encoding="utf-8"))
    try:
        yield RepositorioCuentasPostgres(uri)
    finally:
        servidor.cleanup()


def _cuenta_con_extras() -> Cuenta:
    return Cuenta(
        id="cuenta-1",
        restaurante_id="bar1",
        mesa_nombre="Mesa 1",
        lineas=[
            LineaCuenta(
                nombre_plato="Burger Completa",
                formato=None,
                opciones=[
                    OpcionElegida(nombre="Punto menos", precio=0),
                    OpcionElegida(nombre="Bacon", precio=1.5),
                ],
                cantidad=1,
                precio_unitario=15.9,
                total=17.4,
                pedido_por_nombre="Jose",
            )
        ],
        por_persona=[ResumenPersonaCuenta(nombre="Jose", total=17.4)],
        total=17.4,
        creada_en=T0,
    )


def test_guardar_y_listar_no_revienta_por_el_tipo_jsonb(
    repo: RepositorioCuentasPostgres,
) -> None:
    """El mismo fallo que ya paso con lineas_ticket.opciones: sin
    json.dumps(), psycopg intenta mandar la lista de Python como ARRAY, no
    como JSONB, y revienta."""
    repo.guardar(_cuenta_con_extras())

    recargadas = repo.listar_recientes("bar1", DESDE_SIEMPRE)
    assert len(recargadas) == 1
    cuenta = recargadas[0]
    assert cuenta.mesa_nombre == "Mesa 1"
    assert [o.nombre for o in cuenta.lineas[0].opciones] == ["Punto menos", "Bacon"]
    assert cuenta.por_persona == [ResumenPersonaCuenta(nombre="Jose", total=17.4)]


def test_listar_recientes_filtra_por_fecha_y_restaurante(
    repo: RepositorioCuentasPostgres,
) -> None:
    repo.guardar(_cuenta_con_extras())
    assert repo.listar_recientes("bar2", DESDE_SIEMPRE) == []
    assert repo.listar_recientes("bar1", datetime(2030, 1, 1, tzinfo=UTC)) == []
