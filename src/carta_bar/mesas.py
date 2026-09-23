"""Mesas y sesiones del pedido en mesa (docs/PEDIDO-EN-MESA.md).

Primer bloque de la Fase A: dar de alta mesas, entrar por su QR (crea sesion
o se une a la que ya este abierta) y quien es el anfitrion. Propuestas,
comandas y cocina llegan en el siguiente bloque, encima de esto.

El acceso a datos vive detras de un Protocol, igual que en uso.py: la logica
de "quien es anfitrion" se puede probar entera sin levantar Postgres.
"""

import os
import secrets
from typing import Any, Literal, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

log = structlog.get_logger()

EstadoSesion = Literal["abierta", "cuenta_pedida", "cerrada"]
RolComensal = Literal["anfitrion", "invitado"]
FormaMesa = Literal["redonda", "cuadrada", "rectangular", "barril", "taburete"]
ResultadoEliminar = Literal["ok", "no_existe", "sesion_abierta"]

# Tamano (en casillas del plano) y aforo con los que nace cada forma. El
# editor del panel usa los mismos valores al soltar una mesa nueva.
DISENO_POR_FORMA: dict[str, tuple[float, float, int]] = {
    "redonda": (2, 2, 4),
    "cuadrada": (2, 2, 4),
    "rectangular": (4, 2, 6),
    "barril": (1, 1, 2),
    "taburete": (1, 1, 1),
}

# Campos de la mesa que el gerente puede cambiar desde el plano.
CAMPOS_EDITABLES = frozenset(
    {"nombre", "zona_id", "forma", "x", "y", "ancho", "alto", "rotacion", "capacidad"}
)


class Zona(BaseModel):
    id: str
    restaurante_id: str
    nombre: str
    orden: int


class Mesa(BaseModel):
    id: str
    restaurante_id: str
    nombre: str
    token_qr: str
    activa: bool = True
    zona_id: str | None = None
    forma: FormaMesa = "cuadrada"
    x: float = 0
    y: float = 0
    ancho: float = 2
    alto: float = 2
    rotacion: int = 0
    capacidad: int = 4


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


class ZonaNoExisteError(Exception):
    """Se pidio poner una mesa en una zona que no existe en ese restaurante."""


class SesionYaAbiertaError(Exception):
    """Dos personas escanearon la mesa a la vez: ya existe una sesion abierta."""


class RepositorioMesas(Protocol):
    def listar_zonas(self, restaurante_id: str) -> list[Zona]:
        """Siempre devuelve alguna: si el bar no tiene ninguna, crea "Sala" y le
        pasa las mesas que aun no tuvieran zona."""
        ...

    def crear_zona(self, restaurante_id: str, nombre: str) -> Zona: ...

    def renombrar_zona(self, restaurante_id: str, zona_id: str, nombre: str) -> Zona | None: ...

    def ordenar_zonas(self, restaurante_id: str, ids: list[str]) -> bool:
        """False si `ids` no es exactamente el conjunto de zonas del bar."""
        ...

    def eliminar_zona(self, restaurante_id: str, zona_id: str) -> ResultadoEliminar:
        """Borra la zona y sus mesas. "sesion_abierta" si alguna mesa esta en uso."""
        ...

    def crear_mesa(
        self, restaurante_id: str, nombre: str, zona_id: str | None = None, **diseno: Any
    ) -> Mesa:
        """Lanza ZonaNoExisteError si la zona indicada no es de ese restaurante."""
        ...

    def actualizar_mesa(
        self, restaurante_id: str, mesa_id: str, cambios: dict[str, Any]
    ) -> Mesa | None:
        """None si la mesa no existe. Lanza ZonaNoExisteError si la zona no es valida."""
        ...

    def eliminar_mesa(self, restaurante_id: str, mesa_id: str) -> ResultadoEliminar:
        """Sin historial se borra del todo; con historial se archiva (activa = false)."""
        ...

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
        self.zonas: dict[str, Zona] = {}
        self.mesas: dict[str, Mesa] = {}
        self.sesiones: dict[str, SesionMesa] = {}
        self.comensales: dict[str, list[Comensal]] = {}

    # -- zonas

    def listar_zonas(self, restaurante_id: str) -> list[Zona]:
        propias = sorted(
            (z for z in self.zonas.values() if z.restaurante_id == restaurante_id),
            key=lambda z: z.orden,
        )
        if not propias:
            propias = [self.crear_zona(restaurante_id, "Sala")]
        ids = {z.id for z in propias}
        for mesa in list(self.mesas.values()):
            if mesa.restaurante_id == restaurante_id and mesa.zona_id not in ids:
                self.mesas[mesa.id] = mesa.model_copy(update={"zona_id": propias[0].id})
        return propias

    def crear_zona(self, restaurante_id: str, nombre: str) -> Zona:
        orden = max(
            (z.orden for z in self.zonas.values() if z.restaurante_id == restaurante_id),
            default=0,
        )
        zona = Zona(id=_id("zona"), restaurante_id=restaurante_id, nombre=nombre, orden=orden + 1)
        self.zonas[zona.id] = zona
        return zona

    def _zona_de(self, restaurante_id: str, zona_id: str) -> Zona | None:
        zona = self.zonas.get(zona_id)
        return zona if zona is not None and zona.restaurante_id == restaurante_id else None

    def renombrar_zona(self, restaurante_id: str, zona_id: str, nombre: str) -> Zona | None:
        zona = self._zona_de(restaurante_id, zona_id)
        if zona is None:
            return None
        nueva = zona.model_copy(update={"nombre": nombre})
        self.zonas[zona_id] = nueva
        return nueva

    def ordenar_zonas(self, restaurante_id: str, ids: list[str]) -> bool:
        propias = {z.id for z in self.zonas.values() if z.restaurante_id == restaurante_id}
        if len(ids) != len(set(ids)) or set(ids) != propias:
            return False
        for orden, zona_id in enumerate(ids, start=1):
            self.zonas[zona_id] = self.zonas[zona_id].model_copy(update={"orden": orden})
        return True

    def _tiene_sesion_abierta(self, mesa_id: str) -> bool:
        return any(s.mesa_id == mesa_id and s.estado != "cerrada" for s in self.sesiones.values())

    def _quitar_mesa(self, mesa_id: str) -> None:
        if any(s.mesa_id == mesa_id for s in self.sesiones.values()):
            self.mesas[mesa_id] = self.mesas[mesa_id].model_copy(
                update={"activa": False, "zona_id": None}
            )
        else:
            del self.mesas[mesa_id]

    def eliminar_zona(self, restaurante_id: str, zona_id: str) -> ResultadoEliminar:
        if self._zona_de(restaurante_id, zona_id) is None:
            return "no_existe"
        de_la_zona = [
            m.id
            for m in self.mesas.values()
            if m.restaurante_id == restaurante_id and m.zona_id == zona_id and m.activa
        ]
        if any(self._tiene_sesion_abierta(m) for m in de_la_zona):
            return "sesion_abierta"
        for mesa_id in de_la_zona:
            self._quitar_mesa(mesa_id)
        del self.zonas[zona_id]
        return "ok"

    # -- mesas

    def crear_mesa(
        self, restaurante_id: str, nombre: str, zona_id: str | None = None, **diseno: Any
    ) -> Mesa:
        if zona_id is None:
            zona_id = self.listar_zonas(restaurante_id)[0].id
        elif self._zona_de(restaurante_id, zona_id) is None:
            raise ZonaNoExisteError()
        mesa = Mesa(
            id=_id("mesa"),
            restaurante_id=restaurante_id,
            nombre=nombre,
            token_qr=secrets.token_urlsafe(20),
            zona_id=zona_id,
            **diseno,
        )
        self.mesas[mesa.id] = mesa
        return mesa

    def actualizar_mesa(
        self, restaurante_id: str, mesa_id: str, cambios: dict[str, Any]
    ) -> Mesa | None:
        mesa = self.mesas.get(mesa_id)
        if mesa is None or mesa.restaurante_id != restaurante_id or not mesa.activa:
            return None
        cambios = {k: v for k, v in cambios.items() if k in CAMPOS_EDITABLES}
        zona = cambios.get("zona_id")
        if zona is not None and self._zona_de(restaurante_id, zona) is None:
            raise ZonaNoExisteError()
        nueva = Mesa.model_validate({**mesa.model_dump(), **cambios})
        self.mesas[mesa_id] = nueva
        return nueva

    def eliminar_mesa(self, restaurante_id: str, mesa_id: str) -> ResultadoEliminar:
        mesa = self.mesas.get(mesa_id)
        if mesa is None or mesa.restaurante_id != restaurante_id or not mesa.activa:
            return "no_existe"
        if self._tiene_sesion_abierta(mesa_id):
            return "sesion_abierta"
        self._quitar_mesa(mesa_id)
        return "ok"

    def listar_mesas(self, restaurante_id: str) -> list[Mesa]:
        self.listar_zonas(restaurante_id)
        return [m for m in self.mesas.values() if m.restaurante_id == restaurante_id and m.activa]

    def regenerar_token(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        mesa = self.mesas.get(mesa_id)
        if mesa is None or mesa.restaurante_id != restaurante_id or not mesa.activa:
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


_COLUMNAS_MESA = (
    "id, nombre, token_qr, activa, zona_id, forma, x, y, ancho, alto, rotacion, capacidad"
)

_ZONAS_DEL_BAR = "SELECT id, nombre, orden FROM zonas WHERE restaurante_id = %s ORDER BY orden"

_INSERTAR_ZONA = """
INSERT INTO zonas (restaurante_id, id, nombre, orden)
VALUES (%s, %s, %s, (SELECT COALESCE(MAX(orden), 0) + 1 FROM zonas WHERE restaurante_id = %s))
RETURNING orden
"""

# Una mesa sin zona (o con una que ya no existe) cae en la primera del bar.
_MESAS_HUERFANAS_A_ZONA = """
UPDATE mesas SET zona_id = %s
WHERE restaurante_id = %s AND activa
  AND (zona_id IS NULL OR zona_id NOT IN (SELECT id FROM zonas WHERE restaurante_id = %s))
"""

_CREAR_MESA = f"""
INSERT INTO mesas (restaurante_id, {_COLUMNAS_MESA})
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_LISTAR_MESAS = f"""
SELECT {_COLUMNAS_MESA} FROM mesas WHERE restaurante_id = %s AND activa ORDER BY nombre
"""

_MESA_POR_ID_BLOQUEADA = f"""
SELECT {_COLUMNAS_MESA} FROM mesas
WHERE restaurante_id = %s AND id = %s AND activa FOR UPDATE
"""

_ACTUALIZAR_MESA = """
UPDATE mesas SET nombre = %s, zona_id = %s, forma = %s, x = %s, y = %s, ancho = %s,
    alto = %s, rotacion = %s, capacidad = %s
WHERE restaurante_id = %s AND id = %s
"""

_REGENERAR_TOKEN = f"""
UPDATE mesas SET token_qr = %s WHERE restaurante_id = %s AND id = %s AND activa
RETURNING {_COLUMNAS_MESA}
"""

_MESA_POR_TOKEN = f"""
SELECT restaurante_id, {_COLUMNAS_MESA} FROM mesas WHERE token_qr = %s
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


def _mesa_de_fila(restaurante_id: str, f: tuple[Any, ...]) -> Mesa:
    return Mesa(
        restaurante_id=restaurante_id,
        id=f[0],
        nombre=f[1],
        token_qr=f[2],
        activa=f[3],
        zona_id=f[4],
        forma=f[5],
        x=f[6],
        y=f[7],
        ancho=f[8],
        alto=f[9],
        rotacion=f[10],
        capacidad=f[11],
    )


class RepositorioMesasPostgres:
    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    # -- zonas

    def _asegurar_zonas(self, cur: psycopg.Cursor[Any], restaurante_id: str) -> list[Zona]:
        """Las zonas del bar; si no tiene ninguna crea "Sala", y recoge las mesas
        sueltas. El candado evita que dos peticiones a la vez creen dos "Sala"."""
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"zonas:{restaurante_id}",))
        cur.execute(_ZONAS_DEL_BAR, (restaurante_id,))
        zonas = [
            Zona(id=f[0], restaurante_id=restaurante_id, nombre=f[1], orden=f[2])
            for f in cur.fetchall()
        ]
        if not zonas:
            zonas = [self._insertar_zona(cur, restaurante_id, "Sala")]
        cur.execute(_MESAS_HUERFANAS_A_ZONA, (zonas[0].id, restaurante_id, restaurante_id))
        return zonas

    def _insertar_zona(self, cur: psycopg.Cursor[Any], restaurante_id: str, nombre: str) -> Zona:
        zona_id = _id("zona")
        cur.execute(_INSERTAR_ZONA, (restaurante_id, zona_id, nombre, restaurante_id))
        fila = cur.fetchone()
        assert fila is not None
        return Zona(id=zona_id, restaurante_id=restaurante_id, nombre=nombre, orden=fila[0])

    def listar_zonas(self, restaurante_id: str) -> list[Zona]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            return self._asegurar_zonas(cur, restaurante_id)

    def crear_zona(self, restaurante_id: str, nombre: str) -> Zona:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"zonas:{restaurante_id}",))
            return self._insertar_zona(cur, restaurante_id, nombre)

    def renombrar_zona(self, restaurante_id: str, zona_id: str, nombre: str) -> Zona | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE zonas SET nombre = %s WHERE restaurante_id = %s AND id = %s "
                "RETURNING orden",
                (nombre, restaurante_id, zona_id),
            )
            fila = cur.fetchone()
        if fila is None:
            return None
        return Zona(id=zona_id, restaurante_id=restaurante_id, nombre=nombre, orden=fila[0])

    def ordenar_zonas(self, restaurante_id: str, ids: list[str]) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM zonas WHERE restaurante_id = %s FOR UPDATE", (restaurante_id,)
            )
            existentes = {f[0] for f in cur.fetchall()}
            if len(ids) != len(set(ids)) or set(ids) != existentes:
                return False
            for orden, zona_id in enumerate(ids, start=1):
                cur.execute(
                    "UPDATE zonas SET orden = %s WHERE restaurante_id = %s AND id = %s",
                    (orden, restaurante_id, zona_id),
                )
        return True

    def eliminar_zona(self, restaurante_id: str, zona_id: str) -> ResultadoEliminar:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM zonas WHERE restaurante_id = %s AND id = %s FOR UPDATE",
                (restaurante_id, zona_id),
            )
            if cur.fetchone() is None:
                return "no_existe"
            cur.execute(
                "SELECT id FROM mesas WHERE restaurante_id = %s AND zona_id = %s AND activa "
                "FOR UPDATE",
                (restaurante_id, zona_id),
            )
            mesas_ids = [f[0] for f in cur.fetchall()]
            if mesas_ids:
                cur.execute(
                    "SELECT 1 FROM sesiones_mesa WHERE restaurante_id = %s "
                    "AND mesa_id = ANY(%s) AND estado != 'cerrada' LIMIT 1",
                    (restaurante_id, mesas_ids),
                )
                if cur.fetchone() is not None:
                    return "sesion_abierta"
                # Las que nunca se usaron se borran; las que tienen historial se
                # archivan (nada se borra si ya hay sesiones colgando de ellas).
                cur.execute(
                    "DELETE FROM mesas WHERE restaurante_id = %s AND id = ANY(%s) "
                    "AND NOT EXISTS (SELECT 1 FROM sesiones_mesa s "
                    "WHERE s.restaurante_id = mesas.restaurante_id AND s.mesa_id = mesas.id)",
                    (restaurante_id, mesas_ids),
                )
                cur.execute(
                    "UPDATE mesas SET activa = false, zona_id = NULL "
                    "WHERE restaurante_id = %s AND id = ANY(%s)",
                    (restaurante_id, mesas_ids),
                )
            cur.execute(
                "DELETE FROM zonas WHERE restaurante_id = %s AND id = %s",
                (restaurante_id, zona_id),
            )
        return "ok"

    # -- mesas

    def crear_mesa(
        self, restaurante_id: str, nombre: str, zona_id: str | None = None, **diseno: Any
    ) -> Mesa:
        with self.pool.connection() as conn, conn.cursor() as cur:
            zonas = self._asegurar_zonas(cur, restaurante_id)
            if zona_id is None:
                zona_id = zonas[0].id
            elif zona_id not in {z.id for z in zonas}:
                raise ZonaNoExisteError()
            mesa = Mesa(
                id=_id("mesa"),
                restaurante_id=restaurante_id,
                nombre=nombre,
                token_qr=secrets.token_urlsafe(20),
                zona_id=zona_id,
                **diseno,
            )
            cur.execute(
                _CREAR_MESA,
                (
                    restaurante_id,
                    mesa.id,
                    mesa.nombre,
                    mesa.token_qr,
                    mesa.activa,
                    mesa.zona_id,
                    mesa.forma,
                    mesa.x,
                    mesa.y,
                    mesa.ancho,
                    mesa.alto,
                    mesa.rotacion,
                    mesa.capacidad,
                ),
            )
        return mesa

    def actualizar_mesa(
        self, restaurante_id: str, mesa_id: str, cambios: dict[str, Any]
    ) -> Mesa | None:
        cambios = {k: v for k, v in cambios.items() if k in CAMPOS_EDITABLES}
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_MESA_POR_ID_BLOQUEADA, (restaurante_id, mesa_id))
            fila = cur.fetchone()
            if fila is None:
                return None
            actual = _mesa_de_fila(restaurante_id, fila)
            zona = cambios.get("zona_id")
            if zona is not None:
                cur.execute(
                    "SELECT 1 FROM zonas WHERE restaurante_id = %s AND id = %s",
                    (restaurante_id, zona),
                )
                if cur.fetchone() is None:
                    raise ZonaNoExisteError()
            nueva = Mesa.model_validate({**actual.model_dump(), **cambios})
            cur.execute(
                _ACTUALIZAR_MESA,
                (
                    nueva.nombre,
                    nueva.zona_id,
                    nueva.forma,
                    nueva.x,
                    nueva.y,
                    nueva.ancho,
                    nueva.alto,
                    nueva.rotacion,
                    nueva.capacidad,
                    restaurante_id,
                    mesa_id,
                ),
            )
        return nueva

    def eliminar_mesa(self, restaurante_id: str, mesa_id: str) -> ResultadoEliminar:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_MESA_POR_ID_BLOQUEADA, (restaurante_id, mesa_id))
            if cur.fetchone() is None:
                return "no_existe"
            cur.execute(
                "SELECT estado != 'cerrada' FROM sesiones_mesa "
                "WHERE restaurante_id = %s AND mesa_id = %s",
                (restaurante_id, mesa_id),
            )
            estados = [f[0] for f in cur.fetchall()]
            if any(estados):
                return "sesion_abierta"
            if estados:
                cur.execute(
                    "UPDATE mesas SET activa = false, zona_id = NULL "
                    "WHERE restaurante_id = %s AND id = %s",
                    (restaurante_id, mesa_id),
                )
            else:
                cur.execute(
                    "DELETE FROM mesas WHERE restaurante_id = %s AND id = %s",
                    (restaurante_id, mesa_id),
                )
        return "ok"

    def listar_mesas(self, restaurante_id: str) -> list[Mesa]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            self._asegurar_zonas(cur, restaurante_id)
            cur.execute(_LISTAR_MESAS, (restaurante_id,))
            filas = cur.fetchall()
        return [_mesa_de_fila(restaurante_id, f) for f in filas]

    def regenerar_token(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_REGENERAR_TOKEN, (secrets.token_urlsafe(20), restaurante_id, mesa_id))
            fila = cur.fetchone()
        return None if fila is None else _mesa_de_fila(restaurante_id, fila)

    def mesa_por_token(self, token_qr: str) -> Mesa | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_MESA_POR_TOKEN, (token_qr,))
            fila = cur.fetchone()
        return None if fila is None else _mesa_de_fila(fila[0], fila[1:])

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
