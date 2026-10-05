"""Resumen de cuenta impreso al cobrar una mesa (docs/PEDIDO-EN-MESA.md,
"Pedir la cuenta y cobrar"): una foto de lo que habia en la mesa en el
momento de cobrar, para que la pantalla dedicada de impresion (la misma de
cocina/barra, ver comandas.py) pueda sacar un papel para el cliente.

No es una factura: no lleva NIF, numeracion fiscal ni nada que exija
VeriFactu — eso es la Fase D de docs/PEDIDO-EN-MESA.md, aparcada. Vive sobre
propuestas.py (una cuenta nace siempre de un resumen_mesa ya calculado), pero
no sabe nada de mesas.py ni de comandas.py.
"""

import json
import os
import secrets
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

from carta_bar.propuestas import ComandaMesa, OpcionElegida

log = structlog.get_logger()


class LineaCuenta(BaseModel):
    nombre_plato: str
    formato: str | None = None
    opciones: list[OpcionElegida] = []
    cantidad: int
    precio_unitario: float
    total: float
    pedido_por_nombre: str


class ResumenPersonaCuenta(BaseModel):
    nombre: str
    total: float


class Cuenta(BaseModel):
    """Una foto de la cuenta en el momento de cobrar: no cambia despues,
    aunque la mesa se reutilice o la propuesta de la que nacio se borre."""

    id: str
    restaurante_id: str
    mesa_nombre: str
    lineas: list[LineaCuenta]
    por_persona: list[ResumenPersonaCuenta]
    total: float
    creada_en: datetime


class RepositorioCuentas(Protocol):
    def guardar(self, cuenta: Cuenta) -> None: ...

    def listar_recientes(self, restaurante_id: str, desde: datetime) -> list[Cuenta]:
        """Las cobradas desde `desde` en adelante, de la mas antigua a la mas
        nueva: lo que sondea la pantalla de impresion, para no perder ninguna
        aunque hubiera estado apagada un rato."""
        ...


def _id(prefijo: str) -> str:
    return f"{prefijo}-{secrets.token_hex(6)}"


def _ahora(ahora: datetime | None) -> datetime:
    return ahora if ahora is not None else datetime.now(UTC)


class RepositorioCuentasMemoria:
    """Para tests y para arrancar sin base de datos."""

    def __init__(self) -> None:
        self.cuentas: dict[str, Cuenta] = {}

    def guardar(self, cuenta: Cuenta) -> None:
        self.cuentas[cuenta.id] = cuenta

    def listar_recientes(self, restaurante_id: str, desde: datetime) -> list[Cuenta]:
        propias = [
            c
            for c in self.cuentas.values()
            if c.restaurante_id == restaurante_id and c.creada_en >= desde
        ]
        return sorted(propias, key=lambda c: c.creada_en)


_GUARDAR_CUENTA = """
INSERT INTO recibos_cuenta (id, restaurante_id, mesa_nombre, lineas, por_persona, total, creada_en)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_CUENTAS_RECIENTES = """
SELECT id, restaurante_id, mesa_nombre, lineas, por_persona, total, creada_en
FROM recibos_cuenta
WHERE restaurante_id = %s AND creada_en >= %s
ORDER BY creada_en
"""


def _cuenta_de_fila(f: tuple[Any, ...]) -> Cuenta:
    return Cuenta(
        id=f[0],
        restaurante_id=f[1],
        mesa_nombre=f[2],
        lineas=[LineaCuenta(**lin) for lin in f[3]],
        por_persona=[ResumenPersonaCuenta(**r) for r in f[4]],
        total=f[5],
        creada_en=f[6],
    )


class RepositorioCuentasPostgres:
    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def guardar(self, cuenta: Cuenta) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                _GUARDAR_CUENTA,
                (
                    cuenta.id,
                    cuenta.restaurante_id,
                    cuenta.mesa_nombre,
                    json.dumps([lin.model_dump() for lin in cuenta.lineas]),
                    json.dumps([r.model_dump() for r in cuenta.por_persona]),
                    cuenta.total,
                    cuenta.creada_en,
                ),
            )

    def listar_recientes(self, restaurante_id: str, desde: datetime) -> list[Cuenta]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_CUENTAS_RECIENTES, (restaurante_id, desde))
            return [_cuenta_de_fila(f) for f in cur.fetchall()]


# ------------------------------------------------------------ logica de negocio


def registrar_cuenta(
    repo: RepositorioCuentas,
    restaurante_id: str,
    mesa_nombre: str,
    comanda: ComandaMesa,
    ahora: datetime | None = None,
) -> Cuenta | None:
    """None si no habia nada que cobrar (mesa abierta y cerrada sin pedir
    nada): no tiene sentido imprimir una cuenta vacia."""
    activas = [p for p in comanda.propuestas if p.estado != "retirada"]
    if not activas:
        return None
    cuenta = Cuenta(
        id=_id("cuenta"),
        restaurante_id=restaurante_id,
        mesa_nombre=mesa_nombre,
        lineas=[
            LineaCuenta(
                nombre_plato=p.nombre_plato,
                formato=p.formato,
                opciones=p.opciones,
                cantidad=p.cantidad,
                precio_unitario=p.precio_unitario,
                total=p.total,
                pedido_por_nombre=p.comensal_nombre,
            )
            for p in activas
        ],
        por_persona=[
            ResumenPersonaCuenta(nombre=r.nombre, total=r.total) for r in comanda.por_persona
        ],
        total=comanda.total,
        creada_en=_ahora(ahora),
    )
    repo.guardar(cuenta)
    return cuenta


def crear_repositorio_cuentas() -> RepositorioCuentas:
    """Postgres si hay credenciales; memoria si no, igual que comandas."""
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")

    if not (usuario and clave and base):
        log.warning(
            "cuentas_sin_persistencia",
            motivo="faltan credenciales de POSTGRES en el entorno",
            efecto="los resumenes de cuenta se pierden al reiniciar",
        )
        return RepositorioCuentasMemoria()

    conninfo = f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"
    try:
        repo = RepositorioCuentasPostgres(conninfo)
        log.info("cuentas_persistente", destino=f"{host}:{puerto}/{base}")
        return repo
    except (psycopg.Error, OSError) as e:
        log.error("cuentas_sin_persistencia", motivo=str(e), efecto="se usan en memoria")
        return RepositorioCuentasMemoria()
