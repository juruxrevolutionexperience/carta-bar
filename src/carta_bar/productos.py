"""Lo que le falta a un plato para poder pedirlo (docs/PEDIDO-EN-MESA.md,
"Productos"): a que pantalla va (cocina o barra), en que formatos se sirve y a
que precio (tapa, media, racion), que extras u opciones admite y si lleva
alcohol.

Decidido con el usuario el 2026-09-27:
- El destino se fija por categoria ("Bebidas -> barra") y un plato suelto
  puede cambiarlo. Sin nada, cocina.
- Los extras van en grupos reutilizables ("Extras de hamburguesa", "Punto de
  la carne"), que se asignan a varios platos. Un grupo puede ser obligatorio.
- Los formatos y las opciones NO se traducen, igual que el nombre del plato:
  el cliente dice "una cana" o "media racion" al camarero.
- Los formatos se ven ya en la carta; los extras, solo al pedir (bloque 2).

Nada de esto toca la carta en si (categorias y platos son del restaurante): son
datos aparte, colgados del id del plato o de la categoria. Por eso vive fuera
de datos.py, con su propio repositorio, igual que mesas.py.
"""

import json
import os
import secrets
from typing import Annotated, Any, Literal, Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool
from pydantic import AfterValidator, BaseModel, Field, field_validator, model_validator

log = structlog.get_logger()

Destino = Literal["cocina", "barra"]
DESTINO_POR_DEFECTO: Destino = "cocina"

MAX_FORMATOS = 10
MAX_OPCIONES = 30
MAX_GRUPOS_POR_PLATO = 10


def _limpiar_nombre(v: str) -> str:
    limpio = " ".join(v.split())
    if not limpio:
        raise ValueError("el nombre no puede estar vacio")
    return limpio


# Espacios de sobra fuera; solo espacios no vale.
NombreCorto = Annotated[str, Field(min_length=1, max_length=40), AfterValidator(_limpiar_nombre)]
NombreGrupo = Annotated[str, Field(min_length=1, max_length=60), AfterValidator(_limpiar_nombre)]


def _nombres_repetidos(nombres: list[str]) -> bool:
    minusculas = [n.casefold() for n in nombres]
    return len(minusculas) != len(set(minusculas))


class Formato(BaseModel):
    """ "Tapa" a 3 euros, "Racion" a 10. Si un plato tiene formatos, se pide
    siempre en uno de ellos; si no, a su precio de siempre."""

    nombre: NombreCorto
    precio: float = Field(gt=0, le=10_000)

    @field_validator("precio")
    @classmethod
    def _dos_decimales(cls, v: float) -> float:
        return round(v, 2)


class Opcion(BaseModel):
    """Una opcion de un grupo: "Queso" +1 euro, "Poco hecha" gratis (precio 0)."""

    nombre: NombreCorto
    precio: float = Field(default=0, ge=0, le=1_000)

    @field_validator("precio")
    @classmethod
    def _dos_decimales(cls, v: float) -> float:
        return round(v, 2)


class DatosGrupo(BaseModel):
    """Lo que el gerente escribe de un grupo. `minimo` 0 = opcional ("Extras");
    `minimo` 1 y `maximo` 1 = elegir uno obligatorio ("Punto de la carne")."""

    nombre: NombreGrupo
    minimo: int = Field(default=0, ge=0, le=MAX_OPCIONES)
    maximo: int = Field(default=1, ge=1, le=MAX_OPCIONES)
    opciones: list[Opcion] = Field(min_length=1, max_length=MAX_OPCIONES)

    @model_validator(mode="after")
    def _coherente(self) -> "DatosGrupo":
        if self.minimo > self.maximo:
            raise ValueError("el minimo no puede ser mayor que el maximo")
        if self.maximo > len(self.opciones):
            raise ValueError("el maximo no puede ser mayor que el numero de opciones")
        if _nombres_repetidos([o.nombre for o in self.opciones]):
            raise ValueError("hay dos opciones con el mismo nombre")
        return self


class GrupoOpciones(DatosGrupo):
    id: str
    restaurante_id: str
    orden: int = 0


class DatosPedidoPlato(BaseModel):
    """Lo que el gerente elige para un plato en "Para pedir"."""

    # None = el de su categoria.
    destino: Destino | None = None
    alcohol: bool = False
    formatos: list[Formato] = Field(default_factory=list, max_length=MAX_FORMATOS)
    grupos: list[str] = Field(default_factory=list, max_length=MAX_GRUPOS_POR_PLATO)

    @model_validator(mode="after")
    def _sin_repetidos(self) -> "DatosPedidoPlato":
        if _nombres_repetidos([f.nombre for f in self.formatos]):
            raise ValueError("hay dos formatos con el mismo nombre")
        if len(self.grupos) != len(set(self.grupos)):
            raise ValueError("un grupo esta asignado dos veces")
        return self


class PedidoPlato(DatosPedidoPlato):
    plato_id: str


class GrupoNoExisteError(Exception):
    """Se asigno a un plato un grupo que no es de ese restaurante."""


class RepositorioProductos(Protocol):
    def destinos_categoria(self, restaurante_id: str) -> dict[str, Destino]: ...

    def fijar_destino_categoria(
        self, restaurante_id: str, categoria_id: str, destino: Destino
    ) -> None: ...

    def listar_pedido_platos(self, restaurante_id: str) -> dict[str, PedidoPlato]: ...

    def guardar_pedido_plato(
        self, restaurante_id: str, plato_id: str, datos: DatosPedidoPlato
    ) -> PedidoPlato:
        """Lanza GrupoNoExisteError si algun grupo no es de ese restaurante."""
        ...

    def listar_grupos(self, restaurante_id: str) -> list[GrupoOpciones]: ...

    def crear_grupo(self, restaurante_id: str, datos: DatosGrupo) -> GrupoOpciones: ...

    def actualizar_grupo(
        self, restaurante_id: str, grupo_id: str, datos: DatosGrupo
    ) -> GrupoOpciones | None: ...

    def eliminar_grupo(self, restaurante_id: str, grupo_id: str) -> bool:
        """Lo quita tambien de los platos que lo tenian asignado."""
        ...


def _id_grupo() -> str:
    return f"grupo-{secrets.token_hex(6)}"


class RepositorioProductosMemoria:
    """Para tests y para arrancar sin base de datos."""

    def __init__(self) -> None:
        self.destinos: dict[tuple[str, str], Destino] = {}
        self.pedido: dict[tuple[str, str], PedidoPlato] = {}
        self.grupos: dict[tuple[str, str], GrupoOpciones] = {}

    def destinos_categoria(self, restaurante_id: str) -> dict[str, Destino]:
        return {c: d for (r, c), d in self.destinos.items() if r == restaurante_id}

    def fijar_destino_categoria(
        self, restaurante_id: str, categoria_id: str, destino: Destino
    ) -> None:
        self.destinos[(restaurante_id, categoria_id)] = destino

    def listar_pedido_platos(self, restaurante_id: str) -> dict[str, PedidoPlato]:
        return {p: v for (r, p), v in self.pedido.items() if r == restaurante_id}

    def guardar_pedido_plato(
        self, restaurante_id: str, plato_id: str, datos: DatosPedidoPlato
    ) -> PedidoPlato:
        if any((restaurante_id, g) not in self.grupos for g in datos.grupos):
            raise GrupoNoExisteError()
        guardado = PedidoPlato(plato_id=plato_id, **datos.model_dump())
        self.pedido[(restaurante_id, plato_id)] = guardado
        return guardado

    def listar_grupos(self, restaurante_id: str) -> list[GrupoOpciones]:
        propios = [g for (r, _), g in self.grupos.items() if r == restaurante_id]
        return sorted(propios, key=lambda g: g.orden)

    def crear_grupo(self, restaurante_id: str, datos: DatosGrupo) -> GrupoOpciones:
        orden = max((g.orden for g in self.listar_grupos(restaurante_id)), default=0) + 1
        grupo = GrupoOpciones(
            id=_id_grupo(), restaurante_id=restaurante_id, orden=orden, **datos.model_dump()
        )
        self.grupos[(restaurante_id, grupo.id)] = grupo
        return grupo

    def actualizar_grupo(
        self, restaurante_id: str, grupo_id: str, datos: DatosGrupo
    ) -> GrupoOpciones | None:
        actual = self.grupos.get((restaurante_id, grupo_id))
        if actual is None:
            return None
        nuevo = GrupoOpciones(
            id=grupo_id, restaurante_id=restaurante_id, orden=actual.orden, **datos.model_dump()
        )
        self.grupos[(restaurante_id, grupo_id)] = nuevo
        return nuevo

    def eliminar_grupo(self, restaurante_id: str, grupo_id: str) -> bool:
        if self.grupos.pop((restaurante_id, grupo_id), None) is None:
            return False
        for clave, plato in list(self.pedido.items()):
            if clave[0] == restaurante_id and grupo_id in plato.grupos:
                self.pedido[clave] = plato.model_copy(
                    update={"grupos": [g for g in plato.grupos if g != grupo_id]}
                )
        return True


_COLUMNAS_GRUPO = "id, nombre, minimo, maximo, opciones, orden"


def _grupo_de_fila(restaurante_id: str, f: tuple[Any, ...]) -> GrupoOpciones:
    return GrupoOpciones(
        restaurante_id=restaurante_id,
        id=f[0],
        nombre=f[1],
        minimo=f[2],
        maximo=f[3],
        opciones=f[4],
        orden=f[5],
    )


_GUARDAR_DESTINO_CATEGORIA = """
INSERT INTO destinos_categoria (restaurante_id, categoria_id, destino) VALUES (%s, %s, %s)
ON CONFLICT (restaurante_id, categoria_id) DO UPDATE SET destino = EXCLUDED.destino
"""

_GUARDAR_PEDIDO_PLATO = """
INSERT INTO pedido_platos (restaurante_id, plato_id, destino, alcohol, formatos, grupos)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (restaurante_id, plato_id) DO UPDATE SET
    destino = EXCLUDED.destino, alcohol = EXCLUDED.alcohol,
    formatos = EXCLUDED.formatos, grupos = EXCLUDED.grupos
"""

_CREAR_GRUPO = f"""
INSERT INTO grupos_opciones (restaurante_id, {_COLUMNAS_GRUPO})
VALUES (%s, %s, %s, %s, %s, %s,
    (SELECT COALESCE(MAX(orden), 0) + 1 FROM grupos_opciones WHERE restaurante_id = %s))
RETURNING orden
"""

# `grupos - %s` quita ese id del array JSON de cada plato que lo tuviera.
_QUITAR_GRUPO_DE_PLATOS = """
UPDATE pedido_platos SET grupos = grupos - %s
WHERE restaurante_id = %s AND grupos ? %s
"""


class RepositorioProductosPostgres:
    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def destinos_categoria(self, restaurante_id: str) -> dict[str, Destino]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT categoria_id, destino FROM destinos_categoria WHERE restaurante_id = %s",
                (restaurante_id,),
            )
            return {f[0]: f[1] for f in cur.fetchall()}

    def fijar_destino_categoria(
        self, restaurante_id: str, categoria_id: str, destino: Destino
    ) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_GUARDAR_DESTINO_CATEGORIA, (restaurante_id, categoria_id, destino))

    def listar_pedido_platos(self, restaurante_id: str) -> dict[str, PedidoPlato]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT plato_id, destino, alcohol, formatos, grupos FROM pedido_platos "
                "WHERE restaurante_id = %s",
                (restaurante_id,),
            )
            filas = cur.fetchall()
        return {
            f[0]: PedidoPlato(plato_id=f[0], destino=f[1], alcohol=f[2], formatos=f[3], grupos=f[4])
            for f in filas
        }

    def guardar_pedido_plato(
        self, restaurante_id: str, plato_id: str, datos: DatosPedidoPlato
    ) -> PedidoPlato:
        with self.pool.connection() as conn, conn.cursor() as cur:
            if datos.grupos:
                cur.execute(
                    "SELECT COUNT(*) FROM grupos_opciones WHERE restaurante_id = %s "
                    "AND id = ANY(%s)",
                    (restaurante_id, datos.grupos),
                )
                fila = cur.fetchone()
                if fila is None or fila[0] != len(datos.grupos):
                    raise GrupoNoExisteError()
            cur.execute(
                _GUARDAR_PEDIDO_PLATO,
                (
                    restaurante_id,
                    plato_id,
                    datos.destino,
                    datos.alcohol,
                    json.dumps([f.model_dump() for f in datos.formatos], ensure_ascii=False),
                    json.dumps(datos.grupos),
                ),
            )
        return PedidoPlato(plato_id=plato_id, **datos.model_dump())

    def listar_grupos(self, restaurante_id: str) -> list[GrupoOpciones]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNAS_GRUPO} FROM grupos_opciones WHERE restaurante_id = %s "
                "ORDER BY orden",
                (restaurante_id,),
            )
            return [_grupo_de_fila(restaurante_id, f) for f in cur.fetchall()]

    def crear_grupo(self, restaurante_id: str, datos: DatosGrupo) -> GrupoOpciones:
        grupo_id = _id_grupo()
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"grupos:{restaurante_id}",))
            cur.execute(
                _CREAR_GRUPO,
                (
                    restaurante_id,
                    grupo_id,
                    datos.nombre,
                    datos.minimo,
                    datos.maximo,
                    _opciones_json(datos),
                    restaurante_id,
                ),
            )
            fila = cur.fetchone()
        assert fila is not None
        return GrupoOpciones(
            id=grupo_id, restaurante_id=restaurante_id, orden=fila[0], **datos.model_dump()
        )

    def actualizar_grupo(
        self, restaurante_id: str, grupo_id: str, datos: DatosGrupo
    ) -> GrupoOpciones | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE grupos_opciones SET nombre = %s, minimo = %s, maximo = %s, opciones = %s "
                "WHERE restaurante_id = %s AND id = %s RETURNING orden",
                (
                    datos.nombre,
                    datos.minimo,
                    datos.maximo,
                    _opciones_json(datos),
                    restaurante_id,
                    grupo_id,
                ),
            )
            fila = cur.fetchone()
        if fila is None:
            return None
        return GrupoOpciones(
            id=grupo_id, restaurante_id=restaurante_id, orden=fila[0], **datos.model_dump()
        )

    def eliminar_grupo(self, restaurante_id: str, grupo_id: str) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM grupos_opciones WHERE restaurante_id = %s AND id = %s",
                (restaurante_id, grupo_id),
            )
            if cur.rowcount == 0:
                return False
            cur.execute(_QUITAR_GRUPO_DE_PLATOS, (grupo_id, restaurante_id, grupo_id))
        return True


def _opciones_json(datos: DatosGrupo) -> str:
    return json.dumps([o.model_dump() for o in datos.opciones], ensure_ascii=False)


# ------------------------------------------------------------ logica de negocio


def destino_de(
    categoria_id: str,
    pedido: PedidoPlato | None,
    destinos_categoria: dict[str, Destino],
) -> Destino:
    """El del plato si lo tiene; si no, el de su categoria; si no, cocina."""
    if pedido is not None and pedido.destino is not None:
        return pedido.destino
    return destinos_categoria.get(categoria_id, DESTINO_POR_DEFECTO)


class ConfigProductos(BaseModel):
    """Todo lo de "para pedir" de un restaurante, de una vez, para el panel."""

    destinos_categoria: dict[str, Destino]
    platos: dict[str, PedidoPlato]
    grupos: list[GrupoOpciones]


def config_productos(repo: RepositorioProductos, restaurante_id: str) -> ConfigProductos:
    return ConfigProductos(
        destinos_categoria=repo.destinos_categoria(restaurante_id),
        platos=repo.listar_pedido_platos(restaurante_id),
        grupos=repo.listar_grupos(restaurante_id),
    )


def grupos_de_plato(
    repo: RepositorioProductos, restaurante_id: str, plato_id: str
) -> list[GrupoOpciones]:
    """Los grupos de extras de un plato, con sus opciones y precios. Aparte de
    con_formatos: los extras solo se piden al proponer un plato concreto, no
    se cargan con la carta entera (ver el modulo docstring)."""
    pedido = repo.listar_pedido_platos(restaurante_id).get(plato_id)
    if pedido is None or not pedido.grupos:
        return []
    todos = {g.id: g for g in repo.listar_grupos(restaurante_id)}
    return [todos[g] for g in pedido.grupos if g in todos]


def con_formatos(
    repo: RepositorioProductos, restaurante_id: str, carta: list[dict[str, object]]
) -> list[dict[str, object]]:
    """La carta publica con los formatos de cada plato ("formatos": [] si no
    tiene). Sin traducir: se piden por su nombre, como el plato."""
    pedido = repo.listar_pedido_platos(restaurante_id)
    resultado = []
    for plato in carta:
        config = pedido.get(str(plato.get("id")))
        formatos = [f.model_dump() for f in config.formatos] if config else []
        resultado.append({**plato, "formatos": formatos})
    return resultado


def crear_repositorio_productos() -> RepositorioProductos:
    """Postgres si hay credenciales; memoria si no, igual que mesas."""
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")

    if not (usuario and clave and base):
        log.warning(
            "productos_sin_persistencia",
            motivo="faltan credenciales de POSTGRES en el entorno",
            efecto="formatos, extras y destinos se pierden al reiniciar",
        )
        return RepositorioProductosMemoria()

    conninfo = f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"
    try:
        repo = RepositorioProductosPostgres(conninfo)
        log.info("productos_persistente", destino=f"{host}:{puerto}/{base}")
        return repo
    except (psycopg.Error, OSError) as e:
        log.error("productos_sin_persistencia", motivo=str(e), efecto="se usan en memoria")
        return RepositorioProductosMemoria()
