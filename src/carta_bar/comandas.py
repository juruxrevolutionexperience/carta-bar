"""Comandas y tickets del pedido en mesa (docs/PEDIDO-EN-MESA.md, "Bloque 3
en detalle"): lo que sale de verdad hacia cocina o barra cuando el anfitrion
confirma. Vive sobre el bloque 2 (propuestas.py): una comanda nace siempre de
propuestas ya confirmadas, nunca se crea suelta.

Sin ventana de agrupacion (decidido con el usuario el 2026-09-29): confirmar
manda al instante. Si se quiere pedir algo mas, es una ronda nueva (otra
comanda). El alcohol solo se marca en la tarjeta del ticket, sin pedir
confirmacion expresa al servirlo — eso se deja para mas adelante si hace
falta de verdad.
"""

import os
import secrets
from datetime import UTC, date, datetime
from typing import Any, Literal, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

from carta_bar.productos import Destino

log = structlog.get_logger()

EstadoTicket = Literal["recibida", "en_preparacion", "servida"]


class OpcionElegida(BaseModel):
    nombre: str
    precio: float


class Linea(BaseModel):
    """Copia de una propuesta confirmada: nombre, precio y quien la pidio no
    cambian aunque el gerente toque la carta despues (mismo motivo que en
    propuestas.py)."""

    id: str = Field(default_factory=lambda: _id("linea"))
    propuesta_id: str
    nombre_plato: str
    formato: str | None = None
    precio_unitario: float
    cantidad: int = Field(ge=1)
    opciones: list[OpcionElegida] = Field(default_factory=list)
    nota: str | None = None
    alcohol: bool = False
    pedido_por_nombre: str
    # Nunca se borra: una linea equivocada o cancelada queda marcada, con el
    # motivo, para que quede constancia (docs/PEDIDO-EN-MESA.md, "Anular una
    # linea ya confirmada").
    anulada: bool = False
    motivo_anulacion: str | None = None


class Ticket(BaseModel):
    """La parte de una comanda que va a un destino (cocina o barra)."""

    id: str
    comanda_id: str
    restaurante_id: str
    sesion_id: str
    mesa_nombre: str
    numero_comanda: int
    destino: Destino
    lineas: list[Linea]
    estado: EstadoTicket = "recibida"
    creado_en: datetime
    actualizado_en: datetime


class RepositorioComandas(Protocol):
    def crear_comanda_con_tickets(
        self,
        restaurante_id: str,
        sesion_id: str,
        mesa_nombre: str,
        lineas_por_destino: dict[Destino, list[Linea]],
        ahora: datetime,
    ) -> list[Ticket]:
        """Crea la comanda (con su numero correlativo del dia) y un ticket por
        destino presente en `lineas_por_destino`. `lineas_por_destino` nunca
        esta vacio: quien llama ya filtro que hubiera algo que confirmar."""
        ...

    def listar_pendientes(
        self, restaurante_id: str, destino: Destino | None = None
    ) -> list[Ticket]:
        """Todos los que no estan "servida", del mas antiguo al mas nuevo."""
        ...

    def listar_de_sesion(self, sesion_id: str) -> list[Ticket]:
        """Todos los tickets de esa mesa, en cualquier estado: lo que ve el
        cliente de su propia comanda (a diferencia de listar_pendientes, que
        es para la pantalla de cocina de todo el restaurante)."""
        ...

    def obtener_ticket(self, restaurante_id: str, ticket_id: str) -> Ticket | None: ...

    def actualizar_estado(
        self, restaurante_id: str, ticket_id: str, estado: EstadoTicket, ahora: datetime
    ) -> Ticket | None: ...

    def anular_linea(
        self, restaurante_id: str, ticket_id: str, linea_id: str, motivo: str, ahora: datetime
    ) -> Ticket | None:
        """None si el ticket no es de ese restaurante o la linea no es de ese
        ticket. No borra nada: marca `anulada` y guarda el motivo."""
        ...


def _id(prefijo: str) -> str:
    return f"{prefijo}-{secrets.token_hex(6)}"


class RepositorioComandasMemoria:
    """Para tests y para arrancar sin base de datos."""

    def __init__(self) -> None:
        self.tickets: dict[str, Ticket] = {}
        self._numeros: dict[tuple[str, date], int] = {}

    def _siguiente_numero(self, restaurante_id: str, ahora: datetime) -> int:
        clave = (restaurante_id, ahora.date())
        siguiente = self._numeros.get(clave, 0) + 1
        self._numeros[clave] = siguiente
        return siguiente

    def crear_comanda_con_tickets(
        self,
        restaurante_id: str,
        sesion_id: str,
        mesa_nombre: str,
        lineas_por_destino: dict[Destino, list[Linea]],
        ahora: datetime,
    ) -> list[Ticket]:
        comanda_id = _id("comanda")
        numero = self._siguiente_numero(restaurante_id, ahora)
        creados = []
        for destino, lineas in lineas_por_destino.items():
            ticket = Ticket(
                id=_id("ticket"),
                comanda_id=comanda_id,
                restaurante_id=restaurante_id,
                sesion_id=sesion_id,
                mesa_nombre=mesa_nombre,
                numero_comanda=numero,
                destino=destino,
                lineas=lineas,
                creado_en=ahora,
                actualizado_en=ahora,
            )
            self.tickets[ticket.id] = ticket
            creados.append(ticket)
        return creados

    def listar_pendientes(
        self, restaurante_id: str, destino: Destino | None = None
    ) -> list[Ticket]:
        propios = [
            t
            for t in self.tickets.values()
            if t.restaurante_id == restaurante_id
            and t.estado != "servida"
            and (destino is None or t.destino == destino)
        ]
        return sorted(propios, key=lambda t: t.creado_en)

    def listar_de_sesion(self, sesion_id: str) -> list[Ticket]:
        propios = [t for t in self.tickets.values() if t.sesion_id == sesion_id]
        return sorted(propios, key=lambda t: t.creado_en)

    def obtener_ticket(self, restaurante_id: str, ticket_id: str) -> Ticket | None:
        ticket = self.tickets.get(ticket_id)
        return ticket if ticket is not None and ticket.restaurante_id == restaurante_id else None

    def actualizar_estado(
        self, restaurante_id: str, ticket_id: str, estado: EstadoTicket, ahora: datetime
    ) -> Ticket | None:
        actual = self.obtener_ticket(restaurante_id, ticket_id)
        if actual is None:
            return None
        nuevo = actual.model_copy(update={"estado": estado, "actualizado_en": ahora})
        self.tickets[ticket_id] = nuevo
        return nuevo

    def anular_linea(
        self, restaurante_id: str, ticket_id: str, linea_id: str, motivo: str, ahora: datetime
    ) -> Ticket | None:
        actual = self.obtener_ticket(restaurante_id, ticket_id)
        if actual is None or not any(lin.id == linea_id for lin in actual.lineas):
            return None
        lineas = [
            lin.model_copy(update={"anulada": True, "motivo_anulacion": motivo})
            if lin.id == linea_id
            else lin
            for lin in actual.lineas
        ]
        nuevo = actual.model_copy(update={"lineas": lineas, "actualizado_en": ahora})
        self.tickets[ticket_id] = nuevo
        return nuevo


_CANDADO_COMANDAS = "SELECT pg_advisory_xact_lock(hashtext(%s))"

_CREAR_COMANDA = """
INSERT INTO comandas (id, restaurante_id, sesion_id, numero, creada_en) VALUES (%s, %s, %s, %s, %s)
"""

_CREAR_TICKET = """
INSERT INTO tickets
    (id, comanda_id, restaurante_id, sesion_id, mesa_nombre, numero_comanda, destino,
     estado, creado_en, actualizado_en)
VALUES (%s, %s, %s, %s, %s, %s, %s, 'recibida', %s, %s)
"""

_CREAR_LINEA = """
INSERT INTO lineas_ticket
    (id, ticket_id, propuesta_id, nombre_plato, formato, precio_unitario, cantidad,
     opciones, nota, alcohol, pedido_por_nombre)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_COLUMNAS_TICKET = (
    "id, comanda_id, restaurante_id, sesion_id, mesa_nombre, numero_comanda, destino, "
    "estado, creado_en, actualizado_en"
)

_COLUMNAS_LINEA = (
    "id, propuesta_id, nombre_plato, formato, precio_unitario, cantidad, opciones, nota, "
    "alcohol, pedido_por_nombre, anulada, motivo_anulacion"
)

_ANULAR_LINEA = """
UPDATE lineas_ticket SET anulada = true, motivo_anulacion = %s
WHERE id = %s AND ticket_id = %s
"""

_LINEAS_DE_TICKET = f"SELECT {_COLUMNAS_LINEA} FROM lineas_ticket WHERE ticket_id = %s"

_TICKETS_PENDIENTES = f"""
SELECT {_COLUMNAS_TICKET} FROM tickets
WHERE restaurante_id = %s AND estado != 'servida'
"""

_TICKET_POR_ID = f"SELECT {_COLUMNAS_TICKET} FROM tickets WHERE restaurante_id = %s AND id = %s"

_TICKETS_DE_SESION = f"""
SELECT {_COLUMNAS_TICKET} FROM tickets WHERE sesion_id = %s ORDER BY creado_en
"""

_ACTUALIZAR_ESTADO_TICKET = """
UPDATE tickets SET estado = %s, actualizado_en = %s WHERE restaurante_id = %s AND id = %s
"""


def _linea_de_fila(f: tuple[Any, ...]) -> Linea:
    return Linea(
        id=f[0],
        propuesta_id=f[1],
        nombre_plato=f[2],
        formato=f[3],
        precio_unitario=f[4],
        cantidad=f[5],
        opciones=[OpcionElegida(**o) for o in f[6]],
        nota=f[7],
        alcohol=f[8],
        pedido_por_nombre=f[9],
        anulada=f[10],
        motivo_anulacion=f[11],
    )


class RepositorioComandasPostgres:
    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def crear_comanda_con_tickets(
        self,
        restaurante_id: str,
        sesion_id: str,
        mesa_nombre: str,
        lineas_por_destino: dict[Destino, list[Linea]],
        ahora: datetime,
    ) -> list[Ticket]:
        comanda_id = _id("comanda")
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_CANDADO_COMANDAS, (f"comandas:{restaurante_id}:{ahora.date()}",))
            cur.execute(
                "SELECT COUNT(*) FROM comandas WHERE restaurante_id = %s AND creada_en::date = %s",
                (restaurante_id, ahora.date()),
            )
            fila = cur.fetchone()
            numero = (fila[0] if fila else 0) + 1
            cur.execute(_CREAR_COMANDA, (comanda_id, restaurante_id, sesion_id, numero, ahora))

            creados = []
            for destino, lineas in lineas_por_destino.items():
                ticket_id = _id("ticket")
                cur.execute(
                    _CREAR_TICKET,
                    (
                        ticket_id,
                        comanda_id,
                        restaurante_id,
                        sesion_id,
                        mesa_nombre,
                        numero,
                        destino,
                        ahora,
                        ahora,
                    ),
                )
                for linea in lineas:
                    cur.execute(
                        _CREAR_LINEA,
                        (
                            linea.id,
                            ticket_id,
                            linea.propuesta_id,
                            linea.nombre_plato,
                            linea.formato,
                            linea.precio_unitario,
                            linea.cantidad,
                            [o.model_dump() for o in linea.opciones],
                            linea.nota,
                            linea.alcohol,
                            linea.pedido_por_nombre,
                        ),
                    )
                creados.append(
                    Ticket(
                        id=ticket_id,
                        comanda_id=comanda_id,
                        restaurante_id=restaurante_id,
                        sesion_id=sesion_id,
                        mesa_nombre=mesa_nombre,
                        numero_comanda=numero,
                        destino=destino,
                        lineas=lineas,
                        creado_en=ahora,
                        actualizado_en=ahora,
                    )
                )
        return creados

    def _con_lineas(self, cur: psycopg.Cursor[Any], filas: list[tuple[Any, ...]]) -> list[Ticket]:
        resultado = []
        for f in filas:
            cur.execute(_LINEAS_DE_TICKET, (f[0],))
            lineas = [_linea_de_fila(lf) for lf in cur.fetchall()]
            resultado.append(
                Ticket(
                    id=f[0],
                    comanda_id=f[1],
                    restaurante_id=f[2],
                    sesion_id=f[3],
                    mesa_nombre=f[4],
                    numero_comanda=f[5],
                    destino=f[6],
                    estado=f[7],
                    creado_en=f[8],
                    actualizado_en=f[9],
                    lineas=lineas,
                )
            )
        return resultado

    def listar_pendientes(
        self, restaurante_id: str, destino: Destino | None = None
    ) -> list[Ticket]:
        consulta = _TICKETS_PENDIENTES
        parametros: tuple[Any, ...] = (restaurante_id,)
        if destino is not None:
            consulta += " AND destino = %s"
            parametros = (restaurante_id, destino)
        consulta += " ORDER BY creado_en"
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(consulta, parametros)
            return self._con_lineas(cur, cur.fetchall())

    def listar_de_sesion(self, sesion_id: str) -> list[Ticket]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_TICKETS_DE_SESION, (sesion_id,))
            return self._con_lineas(cur, cur.fetchall())

    def obtener_ticket(self, restaurante_id: str, ticket_id: str) -> Ticket | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_TICKET_POR_ID, (restaurante_id, ticket_id))
            fila = cur.fetchone()
            if fila is None:
                return None
            return self._con_lineas(cur, [fila])[0]

    def actualizar_estado(
        self, restaurante_id: str, ticket_id: str, estado: EstadoTicket, ahora: datetime
    ) -> Ticket | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_ACTUALIZAR_ESTADO_TICKET, (estado, ahora, restaurante_id, ticket_id))
        return self.obtener_ticket(restaurante_id, ticket_id)

    def anular_linea(
        self, restaurante_id: str, ticket_id: str, linea_id: str, motivo: str, ahora: datetime
    ) -> Ticket | None:
        if self.obtener_ticket(restaurante_id, ticket_id) is None:
            return None
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_ANULAR_LINEA, (motivo, linea_id, ticket_id))
            if cur.rowcount == 0:
                return None
        return self.obtener_ticket(restaurante_id, ticket_id)


# ------------------------------------------------------------ logica de negocio


def _ahora(ahora: datetime | None) -> datetime:
    return ahora if ahora is not None else datetime.now(UTC)


def crear_comanda(
    repo: RepositorioComandas,
    restaurante_id: str,
    sesion_id: str,
    mesa_nombre: str,
    lineas_por_destino: dict[Destino, list[Linea]],
    ahora: datetime | None = None,
) -> list[Ticket]:
    """None si no hay nada que confirmar (lineas_por_destino vacio): quien
    llama no debe crear una comanda sin lineas."""
    if not lineas_por_destino:
        return []
    return repo.crear_comanda_con_tickets(
        restaurante_id, sesion_id, mesa_nombre, lineas_por_destino, _ahora(ahora)
    )


def anular_linea(
    repo: RepositorioComandas,
    restaurante_id: str,
    ticket_id: str,
    linea_id: str,
    motivo: str,
    ahora: datetime | None = None,
) -> Ticket | None:
    """El camarero anula una linea ya enviada (pedido equivocado, el cliente
    cambia de idea): nunca se borra, queda marcada con el motivo."""
    return repo.anular_linea(restaurante_id, ticket_id, linea_id, motivo, _ahora(ahora))


EstadoComandaCliente = Literal["en_preparacion", "servido"]


class ResumenComanda(BaseModel):
    """Lo que ve el cliente de su propia comanda (docs/PEDIDO-EN-MESA.md,
    seccion 11.1): solo si ya se sirvio del todo o no, sin colas ni minutos.
    Una comanda con tickets en cocina y en barra cuenta como servida solo
    cuando los dos lo estan."""

    numero: int
    estado: EstadoComandaCliente


def resumen_comandas(repo: RepositorioComandas, sesion_id: str) -> list[ResumenComanda]:
    por_numero: dict[int, list[Ticket]] = {}
    for ticket in repo.listar_de_sesion(sesion_id):
        por_numero.setdefault(ticket.numero_comanda, []).append(ticket)
    resultado = [
        ResumenComanda(
            numero=numero,
            estado="servido" if all(t.estado == "servida" for t in tickets) else "en_preparacion",
        )
        for numero, tickets in por_numero.items()
    ]
    return sorted(resultado, key=lambda r: r.numero)


def crear_repositorio_comandas() -> RepositorioComandas:
    """Postgres si hay credenciales; memoria si no, igual que mesas y productos."""
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")

    if not (usuario and clave and base):
        log.warning(
            "comandas_sin_persistencia",
            motivo="faltan credenciales de POSTGRES en el entorno",
            efecto="las comandas se pierden al reiniciar",
        )
        return RepositorioComandasMemoria()

    conninfo = f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"
    try:
        repo = RepositorioComandasPostgres(conninfo)
        log.info("comandas_persistente", destino=f"{host}:{puerto}/{base}")
        return repo
    except (psycopg.Error, OSError) as e:
        log.error("comandas_sin_persistencia", motivo=str(e), efecto="se usan en memoria")
        return RepositorioComandasMemoria()
