"""Prueba RepositorioComandasPostgres contra un Postgres real (no el de
memoria): la suite normal usa memoria para todo (conftest.py vacia las
credenciales de POSTGRES_*), asi que un fallo de psycopg al adaptar un tipo
de columna (como paso con `opciones`, una lista de dicts sin json.dumps() que
psycopg intentaba volcar como ARRAY en vez de JSONB) no lo detecta nada mas.

Requiere `pgserver` (no es dependencia del proyecto, se instala al vuelo):
    uv run --with pgserver pytest tests/test_comandas_postgres.py -q

Si no esta instalado, se salta sin romper la suite normal.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

pgserver = pytest.importorskip("pgserver")

import psycopg  # noqa: E402

from carta_bar.comandas import (  # noqa: E402
    Linea,
    OpcionElegida,
    RepositorioComandasPostgres,
)

T0 = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[RepositorioComandasPostgres]:
    servidor = pgserver.get_server(str(tmp_path / "pgdata"))
    uri = servidor.get_uri()
    with psycopg.connect(uri, autocommit=True) as conn:
        conn.execute(Path("sql/esquema.sql").read_text(encoding="utf-8"))
        # comandas.sesion_id es clave foranea: hace falta un restaurante, una
        # mesa y una sesion de verdad para poder colgar tickets de ellas.
        conn.execute("INSERT INTO restaurantes (id, nombre) VALUES ('bar1', 'Bar 1')")
        conn.execute(
            "INSERT INTO mesas (restaurante_id, id, nombre, token_qr) "
            "VALUES ('bar1', 'mesa-1', 'Mesa 1', 'tok1'), "
            "('bar1', 'mesa-2', 'Mesa 2', 'tok2')"
        )
        conn.execute(
            "INSERT INTO sesiones_mesa (id, restaurante_id, mesa_id, estado) "
            "VALUES ('sesion-1', 'bar1', 'mesa-1', 'abierta'), "
            "('sesion-2', 'bar1', 'mesa-2', 'abierta')"
        )
    try:
        yield RepositorioComandasPostgres(uri)
    finally:
        servidor.cleanup()


def _linea_con_extras() -> Linea:
    return Linea(
        propuesta_id="prop-1",
        nombre_plato="Burger Completa",
        formato=None,
        precio_unitario=15.9,
        cantidad=1,
        opciones=[
            OpcionElegida(nombre="Punto menos", precio=0),
            OpcionElegida(nombre="Bacon", precio=1.5),
        ],
        nota="sin cebolla",
        alcohol=False,
        pedido_por_nombre="Jose",
    )


def test_crear_comanda_con_opciones_no_revienta_por_el_tipo_jsonb(
    repo: RepositorioComandasPostgres,
) -> None:
    """Este es el fallo real que vio el usuario en producción: confirmar el
    pedido marcaba las propuestas como confirmadas pero no aparecia ningun
    ticket en Cocina, porque `opciones` se mandaba como lista de Python sin
    convertir a JSON y psycopg la interpretaba como un ARRAY, no como JSONB."""
    tickets = repo.crear_comanda_con_tickets(
        "bar1", "sesion-1", "Mesa 1", {"cocina": [_linea_con_extras()]}, T0
    )
    assert len(tickets) == 1
    assert tickets[0].lineas[0].opciones[0].nombre == "Punto menos"

    # Y se puede volver a leer (round-trip completo, como hace Cocina).
    recargado = repo.listar_pendientes("bar1")
    assert len(recargado) == 1
    assert [o.nombre for o in recargado[0].lineas[0].opciones] == ["Punto menos", "Bacon"]


def test_crear_comanda_sin_opciones_tambien_funciona(
    repo: RepositorioComandasPostgres,
) -> None:
    sin_extras = Linea(
        propuesta_id="prop-2",
        nombre_plato="Coca-Cola",
        formato=None,
        precio_unitario=2.5,
        cantidad=2,
        opciones=[],
        nota=None,
        alcohol=False,
        pedido_por_nombre="Ana",
    )
    tickets = repo.crear_comanda_con_tickets(
        "bar1", "sesion-2", "Mesa 2", {"barra": [sin_extras]}, T0
    )
    assert tickets[0].lineas[0].opciones == []
