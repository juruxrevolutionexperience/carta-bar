"""Mesas y sesiones del pedido en mesa (docs/PEDIDO-EN-MESA.md).

Bloque 1 del flujo de mesa: estados de la mesa (libre, por confirmar,
abierta, pidiendo cuenta), entrar por su QR, que el personal abra, confirme o
libere la mesa, expulsar a un comensal y el cierre automatico de mesas
olvidadas. Propuestas, comandas y cocina llegan en el bloque 2, encima de esto.

El acceso a datos vive detras de un Protocol, igual que en uso.py: la logica
de "quien es anfitrion" se puede probar entera sin levantar Postgres.
"""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

log = structlog.get_logger()

# por_confirmar: la abrio un cliente con el QR y el camarero aun no ha salido a
# la mesa a aceptarla. Hasta que la acepte, nada de esa mesa llega a cocina.
EstadoSesion = Literal["por_confirmar", "abierta", "cuenta_pedida", "cerrada"]
# Lo que se ve de una mesa en el panel: "libre" es no tener sesion sin cerrar.
EstadoMesa = Literal["libre", "por_confirmar", "abierta", "cuenta_pedida"]
AbiertaPor = Literal["cliente", "personal"]
MotivoCierre = Literal["cobrada", "liberada", "automatica"]
RolComensal = Literal["anfitrion", "invitado"]
FormaMesa = Literal["redonda", "cuadrada", "rectangular", "barril", "taburete"]
ResultadoEliminar = Literal["ok", "no_existe", "sesion_abierta"]

# Tamano (en unidades del plano, que mide 48 x 30) y aforo con los que nace
# cada forma. El editor del panel usa los mismos valores al soltar una mesa
# nueva (DISENO en frontend/src/admin/planoUtil.ts). Una mesa de 4 mide 3 de
# 48 unidades, como en un TPV: caben decenas en la misma pantalla.
DISENO_POR_FORMA: dict[str, tuple[float, float, int]] = {
    "redonda": (3, 3, 4),
    "cuadrada": (3, 3, 4),
    "rectangular": (6, 3, 6),
    "barril": (2, 2, 2),
    "taburete": (1, 1, 1),
}

# Cierre automatico de mesas olvidadas (acordado el 2026-09-26). Se aplica al
# leer, sin procesos aparte: cada consulta de mesas cierra antes las caducadas.
CADUCA_POR_CONFIRMAR = timedelta(minutes=30)
CADUCA_SIN_ACTIVIDAD = timedelta(hours=4)

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
    ancho: float = 3
    alto: float = 3
    rotacion: int = 0
    capacidad: int = 4
    # Hay clientes sentados (sesion sin cerrar). No se guarda en la mesa: se
    # calcula al listarlas, y es lo que pinta la mesa en rojo en el plano.
    ocupada: bool = False
    # Igual que `ocupada`, calculado al listar: estado de su sesion, comensales
    # dentro (sin contar expulsados) y desde cuando esta abierta.
    estado: EstadoMesa = "libre"
    comensales: int = 0
    abierta_en: datetime | None = None


class SesionMesa(BaseModel):
    id: str
    restaurante_id: str
    mesa_id: str
    estado: EstadoSesion = "abierta"
    abierta_por: AbiertaPor = "cliente"
    # Lo que dice el camarero al abrir ("somos 4"); los que escanean van aparte.
    comensales_declarados: int | None = None
    abierta_en: datetime | None = None
    confirmada_en: datetime | None = None
    ultima_actividad: datetime | None = None
    cerrada_en: datetime | None = None
    motivo_cierre: MotivoCierre | None = None


class Comensal(BaseModel):
    id: str
    sesion_id: str
    nombre: str
    rol: RolComensal
    idioma: str = "es"
    creado_en: datetime | None = None
    # Un comensal expulsado pierde el acceso aunque conserve la cookie.
    expulsado_en: datetime | None = None


class ZonaNoExisteError(Exception):
    """Se pidio poner una mesa en una zona que no existe en ese restaurante."""


class SesionYaAbiertaError(Exception):
    """Dos personas escanearon la mesa a la vez: ya existe una sesion abierta."""


class ComensalExpulsadoError(Exception):
    """Quien vuelve a escanear el QR fue expulsado de la sesion que sigue abierta."""


class SesionCambiadaError(Exception):
    """La sesion se cerro mientras se trabajaba con ella (otro la libero a la vez)."""


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

    def obtener_mesa(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        """La mesa activa de ese restaurante, o None."""
        ...

    # -- sesiones

    def cerrar_caducadas(
        self,
        restaurante_id: str,
        por_confirmar_antes: datetime,
        inactivas_antes: datetime,
        ahora: datetime,
    ) -> int:
        """Cierra con motivo "automatica" las por confirmar abiertas antes de
        `por_confirmar_antes` y cualquiera sin actividad desde `inactivas_antes`."""
        ...

    def sesion_abierta_de(self, restaurante_id: str, mesa_id: str) -> SesionMesa | None: ...

    def crear_sesion(
        self,
        restaurante_id: str,
        mesa_id: str,
        estado: EstadoSesion,
        abierta_por: AbiertaPor,
        ahora: datetime,
        comensales_declarados: int | None = None,
    ) -> SesionMesa:
        """Lanza SesionYaAbiertaError si otra peticion se adelanto creandola."""
        ...

    def actualizar_sesion(self, sesion_id: str, cambios: dict[str, Any]) -> SesionMesa | None:
        """Solo toca sesiones sin cerrar: None si ya estaba cerrada o no existe."""
        ...

    def listar_comensales(self, sesion_id: str) -> list[Comensal]:
        """Todos, expulsados incluidos, por orden de llegada."""
        ...

    def anadir_comensal(
        self, sesion_id: str, nombre: str, idioma: str, ahora: datetime
    ) -> Comensal:
        """Entra como anfitrion si la sesion no tiene ya uno sin expulsar; si no,
        como invitado. Lo decide el repositorio para que dos entradas a la vez
        no acaben con dos anfitriones."""
        ...

    def comensal_con_sesion(self, comensal_id: str) -> tuple[Comensal, SesionMesa] | None: ...

    def expulsar_comensal(self, comensal_id: str, ahora: datetime) -> Comensal | None:
        """Si era el anfitrion, pasa a serlo el invitado mas antiguo que quede."""
        ...


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
        abiertas = {s.mesa_id: s for s in self.sesiones.values() if s.estado != "cerrada"}
        resultado = []
        for m in self.mesas.values():
            if m.restaurante_id != restaurante_id or not m.activa:
                continue
            sesion = abiertas.get(m.id)
            if sesion is not None:
                dentro = [c for c in self.comensales.get(sesion.id, []) if c.expulsado_en is None]
                m = m.model_copy(
                    update={
                        "ocupada": True,
                        "estado": sesion.estado,
                        "comensales": len(dentro),
                        "abierta_en": sesion.abierta_en,
                    }
                )
            resultado.append(m)
        return resultado

    def regenerar_token(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        mesa = self.mesas.get(mesa_id)
        if mesa is None or mesa.restaurante_id != restaurante_id or not mesa.activa:
            return None
        nueva = mesa.model_copy(update={"token_qr": secrets.token_urlsafe(20)})
        self.mesas[mesa_id] = nueva
        return nueva

    def mesa_por_token(self, token_qr: str) -> Mesa | None:
        return next((m for m in self.mesas.values() if m.token_qr == token_qr), None)

    def obtener_mesa(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        mesa = self.mesas.get(mesa_id)
        if mesa is None or mesa.restaurante_id != restaurante_id or not mesa.activa:
            return None
        return mesa

    # -- sesiones

    def cerrar_caducadas(
        self,
        restaurante_id: str,
        por_confirmar_antes: datetime,
        inactivas_antes: datetime,
        ahora: datetime,
    ) -> int:
        cerradas = 0
        for sesion in list(self.sesiones.values()):
            if sesion.restaurante_id != restaurante_id or sesion.estado == "cerrada":
                continue
            olvidada = sesion.estado == "por_confirmar" and _antes(
                sesion.abierta_en, por_confirmar_antes
            )
            if olvidada or _antes(sesion.ultima_actividad, inactivas_antes):
                self.sesiones[sesion.id] = sesion.model_copy(
                    update={"estado": "cerrada", "motivo_cierre": "automatica", "cerrada_en": ahora}
                )
                cerradas += 1
        return cerradas

    def sesion_abierta_de(self, restaurante_id: str, mesa_id: str) -> SesionMesa | None:
        return next(
            (
                s
                for s in self.sesiones.values()
                if s.restaurante_id == restaurante_id
                and s.mesa_id == mesa_id
                and s.estado != "cerrada"
            ),
            None,
        )

    def crear_sesion(
        self,
        restaurante_id: str,
        mesa_id: str,
        estado: EstadoSesion,
        abierta_por: AbiertaPor,
        ahora: datetime,
        comensales_declarados: int | None = None,
    ) -> SesionMesa:
        if self.sesion_abierta_de(restaurante_id, mesa_id) is not None:
            raise SesionYaAbiertaError()
        sesion = _sesion_nueva(
            restaurante_id, mesa_id, estado, abierta_por, ahora, comensales_declarados
        )
        self.sesiones[sesion.id] = sesion
        self.comensales[sesion.id] = []
        return sesion

    def actualizar_sesion(self, sesion_id: str, cambios: dict[str, Any]) -> SesionMesa | None:
        sesion = self.sesiones.get(sesion_id)
        if sesion is None or sesion.estado == "cerrada":
            return None
        cambios = {k: v for k, v in cambios.items() if k in _CAMPOS_SESION_EDITABLES}
        nueva = SesionMesa.model_validate({**sesion.model_dump(), **cambios})
        self.sesiones[sesion_id] = nueva
        return nueva

    def listar_comensales(self, sesion_id: str) -> list[Comensal]:
        return list(self.comensales.get(sesion_id, []))

    def anadir_comensal(
        self, sesion_id: str, nombre: str, idioma: str, ahora: datetime
    ) -> Comensal:
        presentes = self.comensales.setdefault(sesion_id, [])
        hay_anfitrion = any(c.rol == "anfitrion" and c.expulsado_en is None for c in presentes)
        comensal = Comensal(
            id=_id("comensal"),
            sesion_id=sesion_id,
            nombre=nombre,
            rol="invitado" if hay_anfitrion else "anfitrion",
            idioma=idioma,
            creado_en=ahora,
        )
        presentes.append(comensal)
        return comensal

    def comensal_con_sesion(self, comensal_id: str) -> tuple[Comensal, SesionMesa] | None:
        for sesion_id, lista in self.comensales.items():
            for comensal in lista:
                if comensal.id == comensal_id:
                    return comensal, self.sesiones[sesion_id]
        return None

    def expulsar_comensal(self, comensal_id: str, ahora: datetime) -> Comensal | None:
        encontrado = self.comensal_con_sesion(comensal_id)
        if encontrado is None:
            return None
        comensal, sesion = encontrado
        if comensal.expulsado_en is not None:
            return comensal
        lista = self.comensales[sesion.id]
        # El expulsado deja de ser anfitrion: el puesto pasa al siguiente.
        expulsado = comensal.model_copy(update={"expulsado_en": ahora, "rol": "invitado"})
        lista[lista.index(comensal)] = expulsado
        if comensal.rol == "anfitrion":
            siguiente = next((c for c in lista if c.expulsado_en is None), None)
            if siguiente is not None:
                lista[lista.index(siguiente)] = siguiente.model_copy(update={"rol": "anfitrion"})
        return expulsado


def _antes(momento: datetime | None, limite: datetime) -> bool:
    return momento is not None and momento < limite


def _sesion_nueva(
    restaurante_id: str,
    mesa_id: str,
    estado: EstadoSesion,
    abierta_por: AbiertaPor,
    ahora: datetime,
    comensales_declarados: int | None,
) -> SesionMesa:
    return SesionMesa(
        id=_id("sesion"),
        restaurante_id=restaurante_id,
        mesa_id=mesa_id,
        estado=estado,
        abierta_por=abierta_por,
        comensales_declarados=comensales_declarados,
        abierta_en=ahora,
        # Si la abre el personal ya nace aceptada: no hay nada que confirmar.
        confirmada_en=ahora if estado == "abierta" else None,
        ultima_actividad=ahora,
    )


# Lo que la logica de mesas cambia de una sesion (actualizar_sesion ignora el
# resto: el id, la mesa o cuando se abrio no se reescriben nunca).
_CAMPOS_SESION_EDITABLES = frozenset(
    {
        "estado",
        "comensales_declarados",
        "confirmada_en",
        "ultima_actividad",
        "cerrada_en",
        "motivo_cierre",
    }
)


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

# Sesion sin cerrar de cada mesa, con los comensales que siguen dentro.
_SESIONES_DEL_LOCAL = """
SELECT s.mesa_id, s.estado, s.abierta_en,
    (SELECT COUNT(*) FROM comensales c WHERE c.sesion_id = s.id AND c.expulsado_en IS NULL)
FROM sesiones_mesa s WHERE s.restaurante_id = %s AND s.estado != 'cerrada'
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

_COLUMNAS_SESION = (
    "id, restaurante_id, mesa_id, estado, abierta_por, comensales_declarados, abierta_en, "
    "confirmada_en, ultima_actividad, cerrada_en, motivo_cierre"
)

_SESION_ABIERTA = f"""
SELECT {_COLUMNAS_SESION} FROM sesiones_mesa
WHERE restaurante_id = %s AND mesa_id = %s AND estado != 'cerrada'
"""

_CREAR_SESION = f"""
INSERT INTO sesiones_mesa ({_COLUMNAS_SESION})
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_CERRAR_CADUCADAS = """
UPDATE sesiones_mesa SET estado = 'cerrada', motivo_cierre = 'automatica', cerrada_en = %s
WHERE restaurante_id = %s AND estado != 'cerrada'
  AND ((estado = 'por_confirmar' AND abierta_en < %s) OR ultima_actividad < %s)
"""

_COLUMNAS_COMENSAL = "id, sesion_id, nombre, rol, idioma, creado_en, expulsado_en"

_COMENSALES_DE_SESION = f"""
SELECT {_COLUMNAS_COMENSAL} FROM comensales WHERE sesion_id = %s ORDER BY creado_en, id
"""

_ANADIR_COMENSAL = f"""
INSERT INTO comensales ({_COLUMNAS_COMENSAL}) VALUES (%s, %s, %s, %s, %s, %s, NULL)
"""

# Ambas cosas en la misma sesion de BD: el candado por sesion hace que dos
# entradas a la vez decidan el anfitrion una detras de otra.
_CANDADO_SESION = "SELECT pg_advisory_xact_lock(hashtext(%s))"


def _sesion_de_fila(f: tuple[Any, ...]) -> SesionMesa:
    return SesionMesa(
        id=f[0],
        restaurante_id=f[1],
        mesa_id=f[2],
        estado=f[3],
        abierta_por=f[4],
        comensales_declarados=f[5],
        abierta_en=f[6],
        confirmada_en=f[7],
        ultima_actividad=f[8],
        cerrada_en=f[9],
        motivo_cierre=f[10],
    )


def _comensal_de_fila(f: tuple[Any, ...]) -> Comensal:
    return Comensal(
        id=f[0],
        sesion_id=f[1],
        nombre=f[2],
        rol=f[3],
        idioma=f[4],
        creado_en=f[5],
        expulsado_en=f[6],
    )


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
            cur.execute(_SESIONES_DEL_LOCAL, (restaurante_id,))
            abiertas = {f[0]: f[1:] for f in cur.fetchall()}
        resultado = []
        for f in filas:
            mesa = _mesa_de_fila(restaurante_id, f)
            sesion = abiertas.get(mesa.id)
            if sesion is not None:
                estado, abierta_en, dentro = sesion
                mesa = mesa.model_copy(
                    update={
                        "ocupada": True,
                        "estado": estado,
                        "comensales": dentro,
                        "abierta_en": abierta_en,
                    }
                )
            resultado.append(mesa)
        return resultado

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

    def obtener_mesa(self, restaurante_id: str, mesa_id: str) -> Mesa | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNAS_MESA} FROM mesas WHERE restaurante_id = %s AND id = %s "
                "AND activa",
                (restaurante_id, mesa_id),
            )
            fila = cur.fetchone()
        return None if fila is None else _mesa_de_fila(restaurante_id, fila)

    # -- sesiones

    def cerrar_caducadas(
        self,
        restaurante_id: str,
        por_confirmar_antes: datetime,
        inactivas_antes: datetime,
        ahora: datetime,
    ) -> int:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                _CERRAR_CADUCADAS, (ahora, restaurante_id, por_confirmar_antes, inactivas_antes)
            )
            return cur.rowcount

    def sesion_abierta_de(self, restaurante_id: str, mesa_id: str) -> SesionMesa | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_SESION_ABIERTA, (restaurante_id, mesa_id))
            fila = cur.fetchone()
        return None if fila is None else _sesion_de_fila(fila)

    def crear_sesion(
        self,
        restaurante_id: str,
        mesa_id: str,
        estado: EstadoSesion,
        abierta_por: AbiertaPor,
        ahora: datetime,
        comensales_declarados: int | None = None,
    ) -> SesionMesa:
        sesion = _sesion_nueva(
            restaurante_id, mesa_id, estado, abierta_por, ahora, comensales_declarados
        )
        try:
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    _CREAR_SESION,
                    (
                        sesion.id,
                        sesion.restaurante_id,
                        sesion.mesa_id,
                        sesion.estado,
                        sesion.abierta_por,
                        sesion.comensales_declarados,
                        sesion.abierta_en,
                        sesion.confirmada_en,
                        sesion.ultima_actividad,
                        sesion.cerrada_en,
                        sesion.motivo_cierre,
                    ),
                )
        except psycopg.errors.UniqueViolation as e:
            raise SesionYaAbiertaError() from e
        return sesion

    def actualizar_sesion(self, sesion_id: str, cambios: dict[str, Any]) -> SesionMesa | None:
        cambios = {k: v for k, v in cambios.items() if k in _CAMPOS_SESION_EDITABLES}
        if not cambios:
            with self.pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    f"SELECT {_COLUMNAS_SESION} FROM sesiones_mesa "
                    "WHERE id = %s AND estado != 'cerrada'",
                    (sesion_id,),
                )
                fila = cur.fetchone()
            return None if fila is None else _sesion_de_fila(fila)
        # Los nombres de columna salen de _CAMPOS_SESION_EDITABLES, nunca de fuera.
        asignaciones = ", ".join(f"{campo} = %s" for campo in cambios)
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"UPDATE sesiones_mesa SET {asignaciones} "  # noqa: S608
                f"WHERE id = %s AND estado != 'cerrada' RETURNING {_COLUMNAS_SESION}",
                (*cambios.values(), sesion_id),
            )
            fila = cur.fetchone()
        return None if fila is None else _sesion_de_fila(fila)

    def listar_comensales(self, sesion_id: str) -> list[Comensal]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_COMENSALES_DE_SESION, (sesion_id,))
            return [_comensal_de_fila(f) for f in cur.fetchall()]

    def anadir_comensal(
        self, sesion_id: str, nombre: str, idioma: str, ahora: datetime
    ) -> Comensal:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_CANDADO_SESION, (f"comensales:{sesion_id}",))
            cur.execute(
                "SELECT 1 FROM comensales WHERE sesion_id = %s AND rol = 'anfitrion' "
                "AND expulsado_en IS NULL",
                (sesion_id,),
            )
            rol: RolComensal = "invitado" if cur.fetchone() is not None else "anfitrion"
            comensal = Comensal(
                id=_id("comensal"),
                sesion_id=sesion_id,
                nombre=nombre,
                rol=rol,
                idioma=idioma,
                creado_en=ahora,
            )
            cur.execute(
                _ANADIR_COMENSAL,
                (comensal.id, sesion_id, comensal.nombre, comensal.rol, comensal.idioma, ahora),
            )
        return comensal

    def comensal_con_sesion(self, comensal_id: str) -> tuple[Comensal, SesionMesa] | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNAS_COMENSAL} FROM comensales WHERE id = %s", (comensal_id,)
            )
            fila_c = cur.fetchone()
            if fila_c is None:
                return None
            cur.execute(f"SELECT {_COLUMNAS_SESION} FROM sesiones_mesa WHERE id = %s", (fila_c[1],))
            fila_s = cur.fetchone()
        if fila_s is None:
            return None
        return _comensal_de_fila(fila_c), _sesion_de_fila(fila_s)

    def expulsar_comensal(self, comensal_id: str, ahora: datetime) -> Comensal | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT sesion_id FROM comensales WHERE id = %s", (comensal_id,))
            fila = cur.fetchone()
            if fila is None:
                return None
            sesion_id = fila[0]
            cur.execute(_CANDADO_SESION, (f"comensales:{sesion_id}",))
            cur.execute(
                "UPDATE comensales SET expulsado_en = %s, rol = 'invitado' "
                "WHERE id = %s AND expulsado_en IS NULL RETURNING rol",
                (ahora, comensal_id),
            )
            if cur.fetchone() is not None:
                # Si se quedo sin anfitrion, lo pasa a ser el mas antiguo que quede.
                cur.execute(
                    "UPDATE comensales SET rol = 'anfitrion' WHERE id = ("
                    "  SELECT id FROM comensales WHERE sesion_id = %s AND expulsado_en IS NULL"
                    "  ORDER BY creado_en, id LIMIT 1"
                    ") AND NOT EXISTS ("
                    "  SELECT 1 FROM comensales WHERE sesion_id = %s AND rol = 'anfitrion'"
                    "  AND expulsado_en IS NULL"
                    ")",
                    (sesion_id, sesion_id),
                )
            cur.execute(
                f"SELECT {_COLUMNAS_COMENSAL} FROM comensales WHERE id = %s", (comensal_id,)
            )
            final = cur.fetchone()
        return None if final is None else _comensal_de_fila(final)


# ------------------------------------------------------------ logica de negocio
#
# Todo recibe `ahora` para poder probar los cierres automaticos con un reloj
# inyectado. Por defecto, la hora real en UTC.


def _ahora(ahora: datetime | None) -> datetime:
    return ahora if ahora is not None else datetime.now(UTC)


def cerrar_caducadas(repo: RepositorioMesas, restaurante_id: str, ahora: datetime) -> int:
    return repo.cerrar_caducadas(
        restaurante_id,
        por_confirmar_antes=ahora - CADUCA_POR_CONFIRMAR,
        inactivas_antes=ahora - CADUCA_SIN_ACTIVIDAD,
        ahora=ahora,
    )


def mesas_del_local(
    repo: RepositorioMesas, restaurante_id: str, ahora: datetime | None = None
) -> list[Mesa]:
    """Las mesas con su estado, despues de cerrar las que se quedaron olvidadas."""
    cerrar_caducadas(repo, restaurante_id, _ahora(ahora))
    return repo.listar_mesas(restaurante_id)


def entrar_por_qr(
    repo: RepositorioMesas,
    token_qr: str,
    nombre: str | None,
    idioma: str,
    ahora: datetime | None = None,
    comensal_actual: str | None = None,
) -> tuple[SesionMesa, Comensal] | None:
    """None si el token no corresponde a ninguna mesa activa.

    Sin codigo para unirse (decidido el 2026-09-26): quien escanea entra. La
    proteccion es que el camarero sale a la mesa y la acepta antes de que nada
    llegue a cocina. `comensal_actual` es el de la cookie: si ya esta en esta
    sesion (recargo la pagina, volvio a escanear) se le devuelve el mismo en vez
    de crear "Comensal 3"; si lo expulsaron, lanza ComensalExpulsadoError.
    """
    ahora = _ahora(ahora)
    mesa = repo.mesa_por_token(token_qr)
    if mesa is None or not mesa.activa:
        return None
    cerrar_caducadas(repo, mesa.restaurante_id, ahora)

    sesion = repo.sesion_abierta_de(mesa.restaurante_id, mesa.id)
    if sesion is None:
        try:
            sesion = repo.crear_sesion(
                mesa.restaurante_id, mesa.id, "por_confirmar", "cliente", ahora
            )
        except SesionYaAbiertaError:
            # Otra peticion se adelanto entre el "sesion_abierta_de" de arriba
            # y este intento de crearla: se entra a la suya.
            sesion = repo.sesion_abierta_de(mesa.restaurante_id, mesa.id)
            if sesion is None:  # pragma: no cover - no deberia pasar
                raise

    presentes = repo.listar_comensales(sesion.id)
    propio = next((c for c in presentes if c.id == comensal_actual), None)
    if propio is not None and propio.expulsado_en is not None:
        raise ComensalExpulsadoError()
    if propio is None:
        nombre_final = (nombre or "").strip() or f"Comensal {len(presentes) + 1}"
        propio = repo.anadir_comensal(sesion.id, nombre_final, idioma, ahora)
    sesion = repo.actualizar_sesion(sesion.id, {"ultima_actividad": ahora}) or sesion
    return sesion, propio


def abrir_mesa(
    repo: RepositorioMesas,
    restaurante_id: str,
    mesa_id: str,
    comensales: int | None = None,
    ahora: datetime | None = None,
) -> SesionMesa | None:
    """El personal abre la mesa. Si un cliente ya la habia abierto con el QR, la
    acepta en vez de crear otra (una sola sesion por mesa). None si la mesa no
    existe en ese restaurante."""
    ahora = _ahora(ahora)
    if repo.obtener_mesa(restaurante_id, mesa_id) is None:
        return None
    cerrar_caducadas(repo, restaurante_id, ahora)

    sesion = repo.sesion_abierta_de(restaurante_id, mesa_id)
    if sesion is None:
        try:
            return repo.crear_sesion(
                restaurante_id, mesa_id, "abierta", "personal", ahora, comensales
            )
        except SesionYaAbiertaError:
            sesion = repo.sesion_abierta_de(restaurante_id, mesa_id)
            if sesion is None:  # pragma: no cover - no deberia pasar
                raise
    cambios: dict[str, Any] = {"ultima_actividad": ahora}
    if sesion.estado == "por_confirmar":
        cambios |= {"estado": "abierta", "confirmada_en": ahora}
    if comensales is not None:
        cambios["comensales_declarados"] = comensales
    actualizada = repo.actualizar_sesion(sesion.id, cambios)
    if actualizada is None:
        raise SesionCambiadaError()
    return actualizada


def confirmar_mesa(
    repo: RepositorioMesas, restaurante_id: str, mesa_id: str, ahora: datetime | None = None
) -> SesionMesa | None:
    """El camarero acepta la mesa que abrio un cliente. None si la mesa no tiene
    sesion sin cerrar. Confirmar una ya abierta no cambia nada."""
    ahora = _ahora(ahora)
    cerrar_caducadas(repo, restaurante_id, ahora)
    sesion = repo.sesion_abierta_de(restaurante_id, mesa_id)
    if sesion is None:
        return None
    cambios: dict[str, Any] = {"ultima_actividad": ahora}
    if sesion.estado == "por_confirmar":
        cambios |= {"estado": "abierta", "confirmada_en": ahora}
    actualizada = repo.actualizar_sesion(sesion.id, cambios)
    if actualizada is None:
        raise SesionCambiadaError()
    return actualizada


def liberar_mesa(
    repo: RepositorioMesas, restaurante_id: str, mesa_id: str, ahora: datetime | None = None
) -> bool:
    """Cierra la sesion con motivo "liberada" y la mesa vuelve a estar libre.
    False si no habia nada que liberar."""
    ahora = _ahora(ahora)
    sesion = repo.sesion_abierta_de(restaurante_id, mesa_id)
    if sesion is None:
        return False
    cerrada = repo.actualizar_sesion(
        sesion.id, {"estado": "cerrada", "motivo_cierre": "liberada", "cerrada_en": ahora}
    )
    return cerrada is not None


def cobrar_mesa(
    repo: RepositorioMesas, restaurante_id: str, mesa_id: str, ahora: datetime | None = None
) -> bool:
    """El camarero cierra la mesa porque ha cobrado (motivo "cobrada", para
    distinguirla de una liberada sin cobrar). False si no habia nada que cerrar."""
    ahora = _ahora(ahora)
    sesion = repo.sesion_abierta_de(restaurante_id, mesa_id)
    if sesion is None:
        return False
    cerrada = repo.actualizar_sesion(
        sesion.id, {"estado": "cerrada", "motivo_cierre": "cobrada", "cerrada_en": ahora}
    )
    return cerrada is not None


def pedir_cuenta(
    repo: RepositorioMesas, restaurante_id: str, comensal_id: str, ahora: datetime | None = None
) -> SesionMesa | None:
    """Solo el anfitrion, y solo si la mesa ya esta abierta (no tiene sentido
    pedir la cuenta de una mesa que el camarero aun no ha aceptado). None si
    no se puede: comensal de otro restaurante, expulsado, sesion ya cerrada,
    sin aceptar, o no es el anfitrion."""
    ahora = _ahora(ahora)
    encontrado = repo.comensal_con_sesion(comensal_id)
    if encontrado is None:
        return None
    comensal, sesion = encontrado
    if sesion.restaurante_id != restaurante_id or comensal.expulsado_en is not None:
        return None
    if comensal.rol != "anfitrion" or sesion.estado != "abierta":
        return None
    return repo.actualizar_sesion(sesion.id, {"estado": "cuenta_pedida", "ultima_actividad": ahora})


def sesion_de_mesa(
    repo: RepositorioMesas, restaurante_id: str, mesa_id: str, ahora: datetime | None = None
) -> tuple[SesionMesa, list[Comensal]] | None:
    """La sesion sin cerrar de la mesa y todos sus comensales. None si esta libre."""
    cerrar_caducadas(repo, restaurante_id, _ahora(ahora))
    sesion = repo.sesion_abierta_de(restaurante_id, mesa_id)
    if sesion is None:
        return None
    return sesion, repo.listar_comensales(sesion.id)


def expulsar_comensal(
    repo: RepositorioMesas, restaurante_id: str, comensal_id: str, ahora: datetime | None = None
) -> Comensal | None:
    """None si el comensal no existe, es de otro restaurante o su mesa ya cerro."""
    encontrado = repo.comensal_con_sesion(comensal_id)
    if encontrado is None:
        return None
    _, sesion = encontrado
    if sesion.restaurante_id != restaurante_id or sesion.estado == "cerrada":
        return None
    return repo.expulsar_comensal(comensal_id, _ahora(ahora))


class MiSesion(BaseModel):
    """Lo que ve el cliente de su mesa (GET /api/mesa/yo)."""

    mesa: str
    estado: EstadoSesion
    rol: RolComensal
    comensal_id: str
    nombre: str
    comensales: list[str]


def mi_sesion(
    repo: RepositorioMesas,
    restaurante_id: str,
    comensal_id: str,
    ahora: datetime | None = None,
) -> MiSesion | None:
    """None si la sesion se cerro (liberada, cobrada o caducada), si el
    comensal fue expulsado o si es de otro restaurante: la carta debe olvidar
    la mesa."""
    encontrado = repo.comensal_con_sesion(comensal_id)
    if encontrado is None or encontrado[1].restaurante_id != restaurante_id:
        return None
    _, sesion = encontrado
    cerrar_caducadas(repo, sesion.restaurante_id, _ahora(ahora))
    encontrado = repo.comensal_con_sesion(comensal_id)
    if encontrado is None:  # pragma: no cover - no deberia pasar
        return None
    comensal, sesion = encontrado
    if sesion.estado == "cerrada" or comensal.expulsado_en is not None:
        return None
    mesa = repo.obtener_mesa(sesion.restaurante_id, sesion.mesa_id)
    if mesa is None:
        return None
    dentro = [c.nombre for c in repo.listar_comensales(sesion.id) if c.expulsado_en is None]
    return MiSesion(
        mesa=mesa.nombre,
        estado=sesion.estado,
        rol=comensal.rol,
        comensal_id=comensal.id,
        nombre=comensal.nombre,
        comensales=dentro,
    )


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
