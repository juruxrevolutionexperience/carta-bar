"""Mesas y sesiones del pedido en mesa (docs/PEDIDO-EN-MESA.md).

Primer bloque de la Fase A: dar de alta mesas, entrar por su QR (crea sesion
o se une a la que ya este abierta) y quien es el anfitrion. Propuestas,
comandas y cocina llegan en el siguiente bloque, encima de esto.

El acceso a datos vive detras de un Protocol, igual que en uso.py: la logica
de "quien es anfitrion" se puede probar entera sin levantar Postgres.
"""

import os
import secrets
from typing import Literal, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

log = structlog.get_logger()

EstadoSesion = Literal["abierta", "cuenta_pedida", "cerrada"]
RolComensal = Literal["anfitrion", "invitado"]


class Mesa(BaseModel):
    id: str
    restaurante_id: str
    nombre: str
    token_qr: str
    activa: bool = True


class SesionMesa(BaseModel):
    id: str
    restaurante_id: str
    mesa_id: str
    estado: EstadoSesion = "abierta"


class Comensal(BaseModel):
    id: str
    sesion_id: str
    nombre: str
    rol: RolComensal
    idioma: str = "es"


class SesionYaAbiertaError(Exception):
    """Dos personas escanearon la mesa a la vez: ya existe una sesion abierta."""


class RepositorioMesas(Protocol):
    def crear_mesa(self, restaurante_id: str, nombre: str) -> Mesa: ...

    def listar_mesas(self, restaurante_id: str) -> list[Mesa]: ...

    def regenerar_token(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        """Token nuevo para la mesa (el QR impreso deja de valer). None si no existe."""
        ...

    def mesa_por_token(self, token_qr: str) -> Mesa | None: ...

    def sesion_abierta_de(self, restaurante_id: str, mesa_id: str) -> SesionMesa | None: ...

    def crear_sesion(self, restaurante_id: str, mesa_id: str) -> SesionMesa:
        """Lanza SesionYaAbiertaError si otra peticion se adelanto creandola."""
        ...

    def contar_comensales(self, sesion_id: str) -> int: ...

    def anadir_comensal(
        self, sesion_id: str, nombre: str, rol: RolComensal, idioma: str
    ) -> Comensal: ...


def _id(prefijo: str) -> str:
    return f"{prefijo}-{secrets.token_hex(6)}"


class RepositorioMesasMemoria:
    """Para tests y para arrancar sin base de datos."""

    def __init__(self) -> None:
        self.mesas: dict[str, Mesa] = {}
        self.sesiones: dict[str, SesionMesa] = {}
        self.comensales: dict[str, list[Comensal]] = {}

    def crear_mesa(self, restaurante_id: str, nombre: str) -> Mesa:
        mesa = Mesa(
            id=_id("mesa"),
            restaurante_id=restaurante_id,
            nombre=nombre,
            token_qr=secrets.token_urlsafe(20),
        )
        self.mesas[mesa.id] = mesa
        return mesa

    def listar_mesas(self, restaurante_id: str) -> list[Mesa]:
        return [m for m in self.mesas.values() if m.restaurante_id == restaurante_id]

    def regenerar_token(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        mesa = self.mesas.get(mesa_id)
        if mesa is None or mesa.restaurante_id != restaurante_id:
            return None
        nueva = mesa.model_copy(update={"token_qr": secrets.token_urlsafe(20)})
        self.mesas[mesa_id] = nueva
        return nueva

    def mesa_por_token(self, token_qr: str) -> Mesa | None:
        return next((m for m in self.mesas.values() if m.token_qr == token_qr), None)

    def sesion_abierta_de(self, restaurante_id: str, mesa_id: str) -> SesionMesa | None:
        return next(
            (s for s in self.sesiones.values() if s.mesa_id == mesa_id and s.estado != "cerrada"),
            None,
        )

    def crear_sesion(self, restaurante_id: str, mesa_id: str) -> SesionMesa:
        if self.sesion_abierta_de(restaurante_id, mesa_id) is not None:
            raise SesionYaAbiertaError()
        sesion = SesionMesa(id=_id("sesion"), restaurante_id=restaurante_id, mesa_id=mesa_id)
        self.sesiones[sesion.id] = sesion
        self.comensales[sesion.id] = []
        return sesion

    def contar_comensales(self, sesion_id: str) -> int:
        return len(self.comensales.get(sesion_id, []))

    def anadir_comensal(
        self, sesion_id: str, nombre: str, rol: RolComensal, idioma: str
    ) -> Comensal:
        comensal = Comensal(
            id=_id("comensal"), sesion_id=sesion_id, nombre=nombre, rol=rol, idioma=idioma
        )
        self.comensales.setdefault(sesion_id, []).append(comensal)
        return comensal


_CREAR_MESA = """
INSERT INTO mesas (restaurante_id, id, nombre, token_qr) VALUES (%s, %s, %s, %s)
"""

_LISTAR_MESAS = """
SELECT id, nombre, token_qr, activa FROM mesas
WHERE restaurante_id = %s ORDER BY nombre
"""

_REGENERAR_TOKEN = """
UPDATE mesas SET token_qr = %s WHERE restaurante_id = %s AND id = %s
RETURNING nombre, activa
"""

_MESA_POR_TOKEN = """
SELECT restaurante_id, id, nombre, token_qr, activa FROM mesas WHERE token_qr = %s
"""

_SESION_ABIERTA = """
SELECT id, estado FROM sesiones_mesa
WHERE restaurante_id = %s AND mesa_id = %s AND estado != 'cerrada'
"""

_CREAR_SESION = """
INSERT INTO sesiones_mesa (id, restaurante_id, mesa_id, estado) VALUES (%s, %s, %s, 'abierta')
"""

_CONTAR_COMENSALES = "SELECT COUNT(*) FROM comensales WHERE sesion_id = %s"

_ANADIR_COMENSAL = """
INSERT INTO comensales (id, sesion_id, nombre, rol, idioma) VALUES (%s, %s, %s, %s, %s)
"""


class RepositorioMesasPostgres:
    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def crear_mesa(self, restaurante_id: str, nombre: str) -> Mesa:
        mesa = Mesa(
            id=_id("mesa"),
            restaurante_id=restaurante_id,
            nombre=nombre,
            token_qr=secrets.token_urlsafe(20),
        )
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_CREAR_MESA, (restaurante_id, mesa.id, mesa.nombre, mesa.token_qr))
        return mesa

    def listar_mesas(self, restaurante_id: str) -> list[Mesa]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_LISTAR_MESAS, (restaurante_id,))
            filas = cur.fetchall()
        return [
            Mesa(restaurante_id=restaurante_id, id=f[0], nombre=f[1], token_qr=f[2], activa=f[3])
            for f in filas
        ]

    def regenerar_token(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        token = secrets.token_urlsafe(20)
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_REGENERAR_TOKEN, (token, restaurante_id, mesa_id))
            fila = cur.fetchone()
        if fila is None:
            return None
        return Mesa(
            restaurante_id=restaurante_id,
            id=mesa_id,
            nombre=fila[0],
            token_qr=token,
            activa=fila[1],
        )

    def mesa_por_token(self, token_qr: str) -> Mesa | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_MESA_POR_TOKEN, (token_qr,))
            fila = cur.fetchone()
        if fila is None:
            return None
        return Mesa(
            restaurante_id=fila[0], id=fila[1], nombre=fila[2], token_qr=fila[3], activa=fila[4]
        )

    def sesion_abierta_de(self, restaurante_id: str, mesa_id: str) -> SesionMesa | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_SESION_ABIERTA, (restaurante_id, mesa_id))
            fila = cur.fetchone()
        if fila is None:
            return None
        return SesionMesa(
            id=fila[0], restaurante_id=restaurante_id, mesa_id=mesa_id, estado=fila[1]
        )

    def crear_sesion(self, restaurante_id: str, mesa_id: str) -> SesionMesa:
        sesion = SesionMesa(id=_id("sesion"), restaurante_id=restaurante_id, mesa_id=mesa_id)
        try:
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute(_CREAR_SESION, (sesion.id, restaurante_id, mesa_id))
        except psycopg.errors.UniqueViolation as e:
            raise SesionYaAbiertaError() from e
        return sesion

    def contar_comensales(self, sesion_id: str) -> int:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_CONTAR_COMENSALES, (sesion_id,))
            fila = cur.fetchone()
            return int(fila[0]) if fila else 0

    def anadir_comensal(
        self, sesion_id: str, nombre: str, rol: RolComensal, idioma: str
    ) -> Comensal:
        comensal = Comensal(
            id=_id("comensal"), sesion_id=sesion_id, nombre=nombre, rol=rol, idioma=idioma
        )
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                _ANADIR_COMENSAL,
                (comensal.id, sesion_id, comensal.nombre, comensal.rol, comensal.idioma),
            )
        return comensal


def entrar_por_qr(
    repo: RepositorioMesas, token_qr: str, nombre: str | None, idioma: str
) -> tuple[SesionMesa, Comensal] | None:
    """None si el token no corresponde a ninguna mesa activa."""
    mesa = repo.mesa_por_token(token_qr)
    if mesa is None or not mesa.activa:
        return None

    sesion = repo.sesion_abierta_de(mesa.restaurante_id, mesa.id)
    rol: RolComensal = "invitado"
    if sesion is None:
        try:
            sesion = repo.crear_sesion(mesa.restaurante_id, mesa.id)
            rol = "anfitrion"
        except SesionYaAbiertaError:
            # Otra peticion se adelanto entre el "sesion_abierta_de" de arriba
            # y este intento de crearla: se entra como invitado a la suya.
            sesion = repo.sesion_abierta_de(mesa.restaurante_id, mesa.id)
            if sesion is None:  # pragma: no cover - no deberia pasar
                raise

    numero = repo.contar_comensales(sesion.id)
    nombre_final = (nombre or "").strip() or f"Comensal {numero + 1}"
    comensal = repo.anadir_comensal(sesion.id, nombre_final, rol, idioma)
    return sesion, comensal


def crear_repositorio_mesas() -> RepositorioMesas:
    """Postgres si hay credenciales; memoria si no, igual que uso.crear_repositorio."""
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")

    if not (usuario and clave and base):
        log.warning(
            "mesas_sin_persistencia",
            motivo="faltan credenciales de POSTGRES en el entorno",
            efecto="las mesas y sesiones se pierden al reiniciar",
        )
        return RepositorioMesasMemoria()

    conninfo = f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"
    try:
        repo = RepositorioMesasPostgres(conninfo)
        log.info("mesas_persistente", destino=f"{host}:{puerto}/{base}")
        return repo
    except (psycopg.Error, OSError) as e:
        log.error("mesas_sin_persistencia", motivo=str(e), efecto="se usan en memoria")
        return RepositorioMesasMemoria()
