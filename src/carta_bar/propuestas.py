"""Propuestas del pedido en mesa (docs/PEDIDO-EN-MESA.md, "Bloque 2 en
detalle"): lo que un comensal quiere de la mesa antes de que exista comanda.
Vive sobre el bloque 1 (mesas.py): necesita una sesion abierta y un comensal
dentro, pero no sabe nada de cocina, tickets ni cuenta (eso es el bloque 3).

Quien puede confirmar o quitar cualquier propuesta es el anfitrion; eso lo
decide quien llama (api.py conoce el rol del comensal via mesas.py). El
camarero podra hacer lo mismo cuando exista su rol (bloque 3): de momento solo
el anfitrion desatasca una mesa desde la propia carta.
"""

import json
import os
import secrets
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

log = structlog.get_logger()

EstadoPropuesta = Literal["pendiente", "confirmada", "retirada"]
ResultadoRetirar = Literal["ok", "no_existe", "sin_permiso"]


class OpcionElegida(BaseModel):
    """Copia de una opcion de un grupo de extras en el momento de pedirla
    (mismo motivo que nombre_plato/precio_unitario: un cambio de precio del
    grupo no debe alterar lo ya propuesto)."""

    nombre: str
    precio: float = Field(ge=0)


class Propuesta(BaseModel):
    id: str
    sesion_id: str
    comensal_id: str
    comensal_nombre: str
    plato_id: str
    nombre_plato: str
    formato: str | None = None
    precio_unitario: float
    cantidad: int = Field(ge=1, le=20)
    opciones: list[OpcionElegida] = Field(default_factory=list)
    nota: str | None = None
    total: float
    estado: EstadoPropuesta = "pendiente"
    creada_en: datetime


class RepositorioPropuestas(Protocol):
    def guardar(self, propuesta: Propuesta) -> None: ...

    def listar_de_sesion(self, sesion_id: str) -> list[Propuesta]:
        """Todas, incluidas las retiradas: la carta las tacha, no las oculta."""
        ...

    def obtener(self, propuesta_id: str) -> Propuesta | None: ...

    def actualizar_estado(self, propuesta_id: str, estado: EstadoPropuesta) -> Propuesta | None:
        """None si no existe. No comprueba el estado anterior: eso lo hace la
        logica de negocio antes de llamar."""
        ...

    def confirmar_pendientes(self, sesion_id: str, ahora: datetime) -> int:
        """Marca como 'confirmada' las pendientes de la sesion. Devuelve cuantas."""
        ...


def _id(prefijo: str) -> str:
    return f"{prefijo}-{secrets.token_hex(6)}"


def _ahora(ahora: datetime | None) -> datetime:
    return ahora if ahora is not None else datetime.now(UTC)


def _total(precio_unitario: float, opciones: list[OpcionElegida], cantidad: int) -> float:
    return round((precio_unitario + sum(o.precio for o in opciones)) * cantidad, 2)


def proponer(
    repo: RepositorioPropuestas,
    sesion_id: str,
    comensal_id: str,
    comensal_nombre: str,
    plato_id: str,
    nombre_plato: str,
    precio_unitario: float,
    formato: str | None,
    cantidad: int,
    opciones: list[OpcionElegida],
    nota: str | None,
    ahora: datetime | None = None,
) -> Propuesta:
    propuesta = Propuesta(
        id=_id("propuesta"),
        sesion_id=sesion_id,
        comensal_id=comensal_id,
        comensal_nombre=comensal_nombre,
        plato_id=plato_id,
        nombre_plato=nombre_plato,
        formato=formato,
        precio_unitario=precio_unitario,
        cantidad=cantidad,
        opciones=opciones,
        nota=nota,
        total=_total(precio_unitario, opciones, cantidad),
        creada_en=_ahora(ahora),
    )
    repo.guardar(propuesta)
    return propuesta


def retirar(
    repo: RepositorioPropuestas, propuesta_id: str, quien_id: str, quien_es_anfitrion: bool
) -> ResultadoRetirar:
    """Un invitado solo quita las suyas; el anfitrion, cualquiera. Solo se
    puede quitar mientras siga pendiente: una ya confirmada la anula el
    personal (bloque 3), no se retira sola."""
    propuesta = repo.obtener(propuesta_id)
    if propuesta is None or propuesta.estado != "pendiente":
        return "no_existe"
    if propuesta.comensal_id != quien_id and not quien_es_anfitrion:
        return "sin_permiso"
    actualizada = repo.actualizar_estado(propuesta_id, "retirada")
    return "ok" if actualizada is not None else "no_existe"


def confirmar_pendientes(
    repo: RepositorioPropuestas, sesion_id: str, ahora: datetime | None = None
) -> int:
    return repo.confirmar_pendientes(sesion_id, _ahora(ahora))


class RepositorioPropuestasMemoria:
    """Para tests y para arrancar sin base de datos."""

    def __init__(self) -> None:
        self.propuestas: dict[str, Propuesta] = {}

    def guardar(self, propuesta: Propuesta) -> None:
        self.propuestas[propuesta.id] = propuesta

    def listar_de_sesion(self, sesion_id: str) -> list[Propuesta]:
        return sorted(
            (p for p in self.propuestas.values() if p.sesion_id == sesion_id),
            key=lambda p: p.creada_en,
        )

    def obtener(self, propuesta_id: str) -> Propuesta | None:
        return self.propuestas.get(propuesta_id)

    def actualizar_estado(self, propuesta_id: str, estado: EstadoPropuesta) -> Propuesta | None:
        actual = self.propuestas.get(propuesta_id)
        if actual is None:
            return None
        nueva = actual.model_copy(update={"estado": estado})
        self.propuestas[propuesta_id] = nueva
        return nueva

    def confirmar_pendientes(self, sesion_id: str, ahora: datetime) -> int:
        n = 0
        for propuesta in list(self.propuestas.values()):
            if propuesta.sesion_id == sesion_id and propuesta.estado == "pendiente":
                self.propuestas[propuesta.id] = propuesta.model_copy(
                    update={"estado": "confirmada"}
                )
                n += 1
        return n


_COLUMNAS = (
    "id, sesion_id, comensal_id, comensal_nombre, plato_id, nombre_plato, formato, "
    "precio_unitario, cantidad, opciones, nota, total, estado, creada_en"
)

_GUARDAR = f"""
INSERT INTO propuestas ({_COLUMNAS}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_LISTAR_DE_SESION = f"SELECT {_COLUMNAS} FROM propuestas WHERE sesion_id = %s ORDER BY creada_en"

_OBTENER = f"SELECT {_COLUMNAS} FROM propuestas WHERE id = %s"

_ACTUALIZAR_ESTADO = f"""
UPDATE propuestas SET estado = %s WHERE id = %s RETURNING {_COLUMNAS}
"""

_CONFIRMAR_PENDIENTES = """
UPDATE propuestas SET estado = 'confirmada'
WHERE sesion_id = %s AND estado = 'pendiente'
"""


def _propuesta_de_fila(f: tuple[Any, ...]) -> Propuesta:
    return Propuesta(
        id=f[0],
        sesion_id=f[1],
        comensal_id=f[2],
        comensal_nombre=f[3],
        plato_id=f[4],
        nombre_plato=f[5],
        formato=f[6],
        precio_unitario=f[7],
        cantidad=f[8],
        opciones=[OpcionElegida(**o) for o in f[9]],
        nota=f[10],
        total=f[11],
        estado=f[12],
        creada_en=f[13],
    )


class RepositorioPropuestasPostgres:
    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def guardar(self, propuesta: Propuesta) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                _GUARDAR,
                (
                    propuesta.id,
                    propuesta.sesion_id,
                    propuesta.comensal_id,
                    propuesta.comensal_nombre,
                    propuesta.plato_id,
                    propuesta.nombre_plato,
                    propuesta.formato,
                    propuesta.precio_unitario,
                    propuesta.cantidad,
                    json.dumps([o.model_dump() for o in propuesta.opciones]),
                    propuesta.nota,
                    propuesta.total,
                    propuesta.estado,
                    propuesta.creada_en,
                ),
            )

    def listar_de_sesion(self, sesion_id: str) -> list[Propuesta]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_LISTAR_DE_SESION, (sesion_id,))
            return [_propuesta_de_fila(f) for f in cur.fetchall()]

    def obtener(self, propuesta_id: str) -> Propuesta | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_OBTENER, (propuesta_id,))
            fila = cur.fetchone()
        return None if fila is None else _propuesta_de_fila(fila)

    def actualizar_estado(self, propuesta_id: str, estado: EstadoPropuesta) -> Propuesta | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_ACTUALIZAR_ESTADO, (estado, propuesta_id))
            fila = cur.fetchone()
        return None if fila is None else _propuesta_de_fila(fila)

    def confirmar_pendientes(self, sesion_id: str, ahora: datetime) -> int:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_CONFIRMAR_PENDIENTES, (sesion_id,))
            return cur.rowcount


def crear_repositorio_propuestas() -> RepositorioPropuestas:
    """Postgres si hay credenciales; memoria si no, igual que mesas y productos."""
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")

    if not (usuario and clave and base):
        log.warning(
            "propuestas_sin_persistencia",
            motivo="faltan credenciales de POSTGRES en el entorno",
            efecto="las propuestas se pierden al reiniciar",
        )
        return RepositorioPropuestasMemoria()

    conninfo = f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"
    try:
        repo = RepositorioPropuestasPostgres(conninfo)
        log.info("propuestas_persistente", destino=f"{host}:{puerto}/{base}")
        return repo
    except (psycopg.Error, OSError) as e:
        log.error("propuestas_sin_persistencia", motivo=str(e), efecto="se usan en memoria")
        return RepositorioPropuestasMemoria()
