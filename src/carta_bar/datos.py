"""Acceso a la carta: quien la pide (busqueda.py, traductor.py, api.py) no
sabe ni le importa si viene de ficheros o de Postgres.

El interruptor es CARTA_BD_ACTIVA, no solo la presencia de POSTGRES_*: el
servidor ya tiene esas credenciales para el gasto del LLM (uso.py) antes de
que la carta este migrada, y auto-detectar solo por eso serviria una tabla
`platos` vacia el dia que se despliegue este codigo. Se activa a mano una
vez comprobada la migracion (ver scripts/migrar_carta_a_bd.py).
"""

import json
import os
import re
from pathlib import Path
from typing import Protocol

import psycopg
import structlog
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from carta_bar.modelos import Categoria, Plato

log = structlog.get_logger()

_SLUG = re.compile(r"^[a-z0-9-]+$")


def _validar_slug(valor: str, campo: str) -> str:
    """Impide que un valor externo se convierta en travesía de rutas."""
    if not _SLUG.match(valor):
        raise ValueError(f"{campo} no válido: {valor!r}")
    return valor


class RepositorioCarta(Protocol):
    """Lo minimo que necesitan busqueda.py, traductor.py y api.py."""

    def cargar_categorias(self, restaurante_id: str) -> list[Categoria]: ...

    def cargar_carta(self, restaurante_id: str) -> list[Plato]: ...

    def cargar_carta_traducida(
        self, restaurante_id: str, idioma: str
    ) -> list[dict[str, object]]: ...

    def cargar_config(self, restaurante_id: str) -> dict[str, object]: ...

    def cargar_traducciones(
        self, restaurante_id: str, idioma: str
    ) -> dict[str, dict[str, object]]: ...

    def guardar_traducciones(
        self, restaurante_id: str, idioma: str, filas: list[dict[str, object]]
    ) -> None: ...


class RepositorioCartaFicheros:
    """Lee/escribe datos/<restaurante_id>/*.json.

    Es el comportamiento de siempre: lo usan los tests (para no depender de
    una base de datos) y sirve de red de seguridad si Postgres no responde.
    """

    def _ruta_carta(self, restaurante_id: str) -> Path:
        _validar_slug(restaurante_id, "restaurante_id")
        return Path(f"datos/{restaurante_id}/carta.json")

    def _ruta_categorias(self, restaurante_id: str) -> Path:
        _validar_slug(restaurante_id, "restaurante_id")
        return Path(f"datos/{restaurante_id}/categorias.json")

    def _ruta_config(self, restaurante_id: str) -> Path:
        _validar_slug(restaurante_id, "restaurante_id")
        return Path(f"datos/{restaurante_id}/config.json")

    def _ruta_traduccion(self, restaurante_id: str, idioma: str) -> Path:
        _validar_slug(restaurante_id, "restaurante_id")
        _validar_slug(idioma, "idioma")
        return Path(f"datos/{restaurante_id}/carta.{idioma}.json")

    def cargar_categorias(self, restaurante_id: str) -> list[Categoria]:
        datos = json.loads(self._ruta_categorias(restaurante_id).read_text(encoding="utf-8"))
        return [Categoria.model_validate(c) for c in datos]

    def cargar_carta(self, restaurante_id: str) -> list[Plato]:
        categorias_validas = {c.id for c in self.cargar_categorias(restaurante_id)}
        datos = json.loads(self._ruta_carta(restaurante_id).read_text(encoding="utf-8"))
        platos = [Plato.model_validate(p) for p in datos]

        for plato in platos:
            if plato.categoria not in categorias_validas:
                raise ValueError(
                    f"El plato '{plato.nombre}' tiene categoria '{plato.categoria}' "
                    f"que no existe en categorias.json"
                )
        return platos

    def cargar_carta_traducida(
        self, restaurante_id: str, idioma: str
    ) -> list[dict[str, object]]:
        carta = self.cargar_carta(restaurante_id)
        base = [p.model_dump() for p in carta]

        if idioma == "es":
            return base

        trad = self.cargar_traducciones(restaurante_id, idioma)
        for plato in base:
            t = trad.get(plato["id"])
            if t:
                plato["nombre"] = t["nombre"]
                plato["descripcion"] = t["descripcion"]
                plato["ingredientes"] = t["ingredientes"]
        return base

    def cargar_config(self, restaurante_id: str) -> dict[str, object]:
        ruta = self._ruta_config(restaurante_id)
        datos: dict[str, object] = json.loads(ruta.read_text(encoding="utf-8"))
        return datos

    def cargar_traducciones(
        self, restaurante_id: str, idioma: str
    ) -> dict[str, dict[str, object]]:
        ruta = self._ruta_traduccion(restaurante_id, idioma)
        if not ruta.exists():
            return {}
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return {d["id"]: d for d in datos}

    def guardar_traducciones(
        self, restaurante_id: str, idioma: str, filas: list[dict[str, object]]
    ) -> None:
        ruta = self._ruta_traduccion(restaurante_id, idioma)
        ruta.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")


class RepositorioCartaPostgres:
    """Persiste la carta en restaurantes/categorias/platos/traducciones_platos
    (ver sql/esquema.sql)."""

    def __init__(self, conninfo: str) -> None:
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def cargar_categorias(self, restaurante_id: str) -> list[Categoria]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, nombre_i18n, orden FROM categorias "
                "WHERE restaurante_id = %s ORDER BY orden",
                (restaurante_id,),
            )
            filas = cur.fetchall()
        return [
            Categoria(id=f[0], nombre=f[1], nombre_i18n=f[2] or {}, orden=f[3]) for f in filas
        ]

    def cargar_carta(self, restaurante_id: str) -> list[Plato]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, categoria_id, nombre, descripcion, precio, ingredientes, "
                "alergenos, vegano, vegetariano, sin_gluten, sin_lactosa, disponible, "
                "etiqueta, foto FROM platos WHERE restaurante_id = %s ORDER BY id",
                (restaurante_id,),
            )
            filas = cur.fetchall()
        return [
            Plato(
                id=f[0],
                categoria=f[1],
                nombre=f[2],
                descripcion=f[3],
                precio=float(f[4]) if f[4] is not None else None,
                ingredientes=f[5] or [],
                alergenos=f[6] or [],
                vegano=f[7],
                vegetariano=f[8],
                sin_gluten=f[9],
                sin_lactosa=f[10],
                disponible=f[11],
                etiqueta=f[12],
                foto=f[13],
            )
            for f in filas
        ]

    def cargar_carta_traducida(
        self, restaurante_id: str, idioma: str
    ) -> list[dict[str, object]]:
        carta = self.cargar_carta(restaurante_id)
        base = [p.model_dump() for p in carta]

        if idioma == "es":
            return base

        trad = self.cargar_traducciones(restaurante_id, idioma)
        for plato in base:
            t = trad.get(plato["id"])
            if t:
                plato["nombre"] = t["nombre"]
                plato["descripcion"] = t["descripcion"]
                plato["ingredientes"] = t["ingredientes"]
        return base

    def cargar_config(self, restaurante_id: str) -> dict[str, object]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT nombre, subtitulo, color_marca, moneda, foto_portada, logo, "
                "aviso_alergenos, aviso_alergenos_i18n FROM restaurantes WHERE id = %s",
                (restaurante_id,),
            )
            fila = cur.fetchone()
        if fila is None:
            raise ValueError(f"Restaurante '{restaurante_id}' no encontrado en la base de datos")
        return {
            "nombre": fila[0],
            "subtitulo": fila[1],
            "color_marca": fila[2],
            "moneda": fila[3],
            "foto_portada": fila[4],
            "logo": fila[5],
            "aviso_alergenos": fila[6],
            "aviso_alergenos_i18n": fila[7] or {},
        }

    def cargar_traducciones(
        self, restaurante_id: str, idioma: str
    ) -> dict[str, dict[str, object]]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT plato_id, hash, nombre, descripcion, ingredientes "
                "FROM traducciones_platos WHERE restaurante_id = %s AND idioma = %s",
                (restaurante_id, idioma),
            )
            filas = cur.fetchall()
        return {
            f[0]: {
                "id": f[0],
                "hash": f[1],
                "nombre": f[2],
                "descripcion": f[3],
                "ingredientes": f[4] or [],
            }
            for f in filas
        }

    def guardar_traducciones(
        self, restaurante_id: str, idioma: str, filas: list[dict[str, object]]
    ) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            for f in filas:
                cur.execute(
                    """
                    INSERT INTO traducciones_platos
                        (restaurante_id, plato_id, idioma, hash, nombre, descripcion, ingredientes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (restaurante_id, plato_id, idioma) DO UPDATE SET
                        hash = EXCLUDED.hash,
                        nombre = EXCLUDED.nombre,
                        descripcion = EXCLUDED.descripcion,
                        ingredientes = EXCLUDED.ingredientes
                    """,
                    (
                        restaurante_id,
                        f["id"],
                        idioma,
                        f["hash"],
                        f["nombre"],
                        f["descripcion"],
                        Jsonb(f["ingredientes"]),
                    ),
                )

    def aplicar_esquema(self, ruta: str = "sql/esquema.sql") -> None:
        with open(ruta, encoding="utf-8") as f:
            sql = f.read()
        with self.pool.connection() as conn:
            conn.execute(sql)


def _conninfo() -> str | None:
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")
    if not (usuario and clave and base):
        return None
    return f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"


_repositorio: RepositorioCarta | None = None


def obtener_repositorio_carta() -> RepositorioCarta:
    """Postgres solo si CARTA_BD_ACTIVA=true Y hay credenciales; ficheros si no.

    CARTA_BD_ACTIVA es un interruptor aparte de POSTGRES_*: esas credenciales
    ya existen para el gasto del LLM antes de migrar la carta, y confundir
    "hay credenciales" con "la carta ya esta migrada" serviria una tabla
    `platos` vacia el dia que se despliegue este codigo sin haber migrado.
    """
    global _repositorio
    if _repositorio is not None:
        return _repositorio

    if os.getenv("CARTA_BD_ACTIVA", "false").lower() != "true":
        _repositorio = RepositorioCartaFicheros()
        return _repositorio

    conninfo = _conninfo()
    if conninfo is None:
        log.warning(
            "carta_sin_bd",
            motivo="CARTA_BD_ACTIVA=true pero faltan credenciales de POSTGRES",
            efecto="se lee de datos/<restaurante>/*.json",
        )
        _repositorio = RepositorioCartaFicheros()
        return _repositorio

    try:
        repo = RepositorioCartaPostgres(conninfo)
        # Aplica el esquema (IF NOT EXISTS) antes de darlo por bueno: si las
        # tablas no existieran, una consulta fallaria a medias en vez de caer
        # aqui, donde el except ya sabe volver a ficheros.
        repo.aplicar_esquema()
        host = os.getenv("POSTGRES_HOST", "localhost")
        puerto = os.getenv("POSTGRES_PORT", "5432")
        base = os.getenv("POSTGRES_DB", "")
        log.info("carta_persistente", destino=f"{host}:{puerto}/{base}")
        _repositorio = repo
        return _repositorio
    except (psycopg.Error, OSError) as e:
        log.error("carta_sin_bd", motivo=str(e), efecto="se lee de datos/<restaurante>/*.json")
        _repositorio = RepositorioCartaFicheros()
        return _repositorio


def cargar_categorias(restaurante_id: str) -> list[Categoria]:
    return obtener_repositorio_carta().cargar_categorias(restaurante_id)


def cargar_carta(restaurante_id: str) -> list[Plato]:
    return obtener_repositorio_carta().cargar_carta(restaurante_id)


def cargar_carta_traducida(restaurante_id: str, idioma: str) -> list[dict[str, object]]:
    return obtener_repositorio_carta().cargar_carta_traducida(restaurante_id, idioma)


def cargar_config(restaurante_id: str) -> dict[str, object]:
    return obtener_repositorio_carta().cargar_config(restaurante_id)


def cargar_traducciones(restaurante_id: str, idioma: str) -> dict[str, dict[str, object]]:
    return obtener_repositorio_carta().cargar_traducciones(restaurante_id, idioma)


def guardar_traducciones(
    restaurante_id: str, idioma: str, filas: list[dict[str, object]]
) -> None:
    obtener_repositorio_carta().guardar_traducciones(restaurante_id, idioma, filas)
