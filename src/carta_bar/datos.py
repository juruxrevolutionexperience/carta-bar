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
import secrets
import time
import unicodedata
from pathlib import Path
from typing import Any, Literal, Protocol

import psycopg
import structlog
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from carta_bar.modelos import (
    Alergeno,
    Categoria,
    Etiqueta,
    Plato,
    ResumenRestaurante,
    huella_texto,
)

log = structlog.get_logger()

_SLUG = re.compile(r"^[a-z0-9-]+$")

CATEGORIA_ESPECIALES = "especial-de-hoy"


CampoImagenMarca = Literal["logo", "foto_portada"]

_SQL_IMAGEN_MARCA: dict[str, str] = {
    "logo": "UPDATE restaurantes SET logo = %s WHERE id = %s",
    "foto_portada": "UPDATE restaurantes SET foto_portada = %s WHERE id = %s",
}


def _con_traducciones(
    carta: list[Plato], traducciones: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    """La carta con cada plato en su idioma.

    Una traduccion solo vale si su hash coincide con el texto actual del plato.
    Si el plato se edito y la traduccion aun no se ha rehecho (o fallo), es
    mejor enseñarlo en español que con ingredientes de la version anterior:
    en una carta con alergenos, un texto viejo puede ser un texto falso."""
    resultado = []
    for plato in carta:
        fila = plato.model_dump()
        t = traducciones.get(plato.id)
        if t and t.get("hash") == huella_texto(plato):
            fila["nombre"] = t["nombre"]
            fila["descripcion"] = t["descripcion"]
            fila["ingredientes"] = t["ingredientes"]
        resultado.append(fila)
    return resultado


def _validar_slug(valor: str, campo: str) -> str:
    """Impide que un valor externo se convierta en travesía de rutas."""
    if not _SLUG.match(valor):
        raise ValueError(f"{campo} no válido: {valor!r}")
    return valor


ResultadoEliminarCategoria = Literal["ok", "no_existe", "con_platos"]


def slug_categoria(nombre: str) -> str:
    """Id estable a partir del nombre: 'Postres y Café' -> 'postres_y_cafe'.

    Vacio si el nombre no tiene ni una letra o cifra ('???'): quien llama
    debe rechazarlo, no inventarse un id.
    """
    sin_acentos = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", sin_acentos.lower()).strip("_")


def id_categoria_libre(base: str, existentes: set[str]) -> str:
    """base, o base_2, base_3... si ya esta cogido por otra categoria."""
    if base not in existentes:
        return base
    n = 2
    while f"{base}_{n}" in existentes:
        n += 1
    return f"{base}_{n}"


def id_plato_nuevo() -> str:
    """Empieza por la hora de creacion: los platos se leen ORDER BY id, asi
    los nuevos salen al final de su categoria, en el orden en que se crearon
    (con hex aleatorio solo, saldrian en orden arbitrario)."""
    return f"plato-{int(time.time()):010d}-{secrets.token_hex(2)}"


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

    def obtener_clave_hash(self, restaurante_id: str) -> str | None: ...

    def guardar_clave_hash(self, restaurante_id: str, clave_hash: str) -> None: ...

    def actualizar_plato_editable(
        self,
        restaurante_id: str,
        plato_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> bool: ...

    def actualizar_disponibilidad(
        self, restaurante_id: str, plato_id: str, disponible: bool
    ) -> bool: ...

    def actualizar_foto_plato(
        self, restaurante_id: str, plato_id: str, foto: str | None
    ) -> bool: ...

    def actualizar_nombre_restaurante(self, restaurante_id: str, nombre: str) -> bool: ...

    def actualizar_imagen_marca(
        self, restaurante_id: str, campo: CampoImagenMarca, url: str
    ) -> bool: ...

    def crear_plato_especial(
        self,
        restaurante_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato: ...

    def eliminar_plato_especial(self, restaurante_id: str, plato_id: str) -> bool: ...

    def eliminar_plato(self, restaurante_id: str, plato_id: str) -> bool: ...

    def crear_categoria(self, restaurante_id: str, nombre: str) -> Categoria: ...

    def renombrar_categoria(
        self, restaurante_id: str, categoria_id: str, nombre: str
    ) -> Categoria | None: ...

    def ordenar_categorias(self, restaurante_id: str, ids: list[str]) -> bool: ...

    def eliminar_categoria(
        self, restaurante_id: str, categoria_id: str
    ) -> ResultadoEliminarCategoria: ...

    def crear_plato(
        self,
        restaurante_id: str,
        categoria_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato | None: ...

    def listar_restaurantes(self) -> list[ResumenRestaurante]: ...

    def crear_restaurante(self, restaurante_id: str, nombre: str, clave_hash: str) -> None: ...


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
        if idioma == "es":
            return [p.model_dump() for p in carta]
        return _con_traducciones(carta, self.cargar_traducciones(restaurante_id, idioma))

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

    def obtener_clave_hash(self, restaurante_id: str) -> str | None:
        raise NotImplementedError("El login del panel requiere CARTA_BD_ACTIVA=true")

    def guardar_clave_hash(self, restaurante_id: str, clave_hash: str) -> None:
        raise NotImplementedError("El login del panel requiere CARTA_BD_ACTIVA=true")

    def actualizar_plato_editable(
        self,
        restaurante_id: str,
        plato_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> bool:
        raise NotImplementedError("Editar platos requiere CARTA_BD_ACTIVA=true")

    def actualizar_disponibilidad(
        self, restaurante_id: str, plato_id: str, disponible: bool
    ) -> bool:
        raise NotImplementedError("Editar platos requiere CARTA_BD_ACTIVA=true")

    def actualizar_foto_plato(
        self, restaurante_id: str, plato_id: str, foto: str | None
    ) -> bool:
        raise NotImplementedError("Editar platos requiere CARTA_BD_ACTIVA=true")

    def actualizar_nombre_restaurante(self, restaurante_id: str, nombre: str) -> bool:
        raise NotImplementedError("Editar la marca requiere CARTA_BD_ACTIVA=true")

    def actualizar_imagen_marca(
        self, restaurante_id: str, campo: CampoImagenMarca, url: str
    ) -> bool:
        raise NotImplementedError("Editar la marca requiere CARTA_BD_ACTIVA=true")

    def crear_plato_especial(
        self,
        restaurante_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato:
        raise NotImplementedError("Los especiales requieren CARTA_BD_ACTIVA=true")

    def eliminar_plato_especial(self, restaurante_id: str, plato_id: str) -> bool:
        raise NotImplementedError("Los especiales requieren CARTA_BD_ACTIVA=true")

    def eliminar_plato(self, restaurante_id: str, plato_id: str) -> bool:
        raise NotImplementedError("Eliminar platos requiere CARTA_BD_ACTIVA=true")

    def crear_categoria(self, restaurante_id: str, nombre: str) -> Categoria:
        raise NotImplementedError("Editar categorias requiere CARTA_BD_ACTIVA=true")

    def renombrar_categoria(
        self, restaurante_id: str, categoria_id: str, nombre: str
    ) -> Categoria | None:
        raise NotImplementedError("Editar categorias requiere CARTA_BD_ACTIVA=true")

    def ordenar_categorias(self, restaurante_id: str, ids: list[str]) -> bool:
        raise NotImplementedError("Editar categorias requiere CARTA_BD_ACTIVA=true")

    def eliminar_categoria(
        self, restaurante_id: str, categoria_id: str
    ) -> ResultadoEliminarCategoria:
        raise NotImplementedError("Editar categorias requiere CARTA_BD_ACTIVA=true")

    def crear_plato(
        self,
        restaurante_id: str,
        categoria_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato | None:
        raise NotImplementedError("Crear platos requiere CARTA_BD_ACTIVA=true")

    def listar_restaurantes(self) -> list[ResumenRestaurante]:
        raise NotImplementedError("El panel superadmin requiere CARTA_BD_ACTIVA=true")

    def crear_restaurante(self, restaurante_id: str, nombre: str, clave_hash: str) -> None:
        raise NotImplementedError("El panel superadmin requiere CARTA_BD_ACTIVA=true")


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
        if idioma == "es":
            return [p.model_dump() for p in carta]
        return _con_traducciones(carta, self.cargar_traducciones(restaurante_id, idioma))

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

    def obtener_clave_hash(self, restaurante_id: str) -> str | None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT clave_hash FROM restaurantes WHERE id = %s",
                (restaurante_id,),
            )
            fila = cur.fetchone()
        return fila[0] if fila else None

    def guardar_clave_hash(self, restaurante_id: str, clave_hash: str) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE restaurantes SET clave_hash = %s WHERE id = %s",
                (clave_hash, restaurante_id),
            )

    def actualizar_plato_editable(
        self,
        restaurante_id: str,
        plato_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE platos SET nombre = %s, descripcion = %s, precio = %s, "
                "ingredientes = %s, alergenos = %s, etiqueta = %s, vegano = %s, "
                "vegetariano = %s, sin_gluten = %s, sin_lactosa = %s "
                "WHERE restaurante_id = %s AND id = %s",
                (
                    nombre,
                    descripcion,
                    precio,
                    Jsonb(ingredientes),
                    Jsonb([a.value for a in alergenos]),
                    etiqueta.value if etiqueta else None,
                    vegano,
                    vegetariano,
                    sin_gluten,
                    sin_lactosa,
                    restaurante_id,
                    plato_id,
                ),
            )
            return cur.rowcount > 0

    def actualizar_disponibilidad(
        self, restaurante_id: str, plato_id: str, disponible: bool
    ) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE platos SET disponible = %s WHERE restaurante_id = %s AND id = %s",
                (disponible, restaurante_id, plato_id),
            )
            return cur.rowcount > 0

    def actualizar_foto_plato(
        self, restaurante_id: str, plato_id: str, foto: str | None
    ) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE platos SET foto = %s WHERE restaurante_id = %s AND id = %s",
                (foto, restaurante_id, plato_id),
            )
            return cur.rowcount > 0

    def actualizar_nombre_restaurante(self, restaurante_id: str, nombre: str) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE restaurantes SET nombre = %s WHERE id = %s", (nombre, restaurante_id)
            )
            return cur.rowcount > 0

    def actualizar_imagen_marca(
        self, restaurante_id: str, campo: CampoImagenMarca, url: str
    ) -> bool:
        # El nombre de la columna no se puede pasar como parametro: por eso
        # se elige entre dos consultas fijas, nunca se interpola el valor.
        consulta = _SQL_IMAGEN_MARCA[campo]
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(consulta, (url, restaurante_id))
            return cur.rowcount > 0

    def _insertar_plato(
        self,
        cur: psycopg.Cursor[Any],
        restaurante_id: str,
        plato_id: str,
        categoria_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato:
        cur.execute(
            "INSERT INTO platos (restaurante_id, id, categoria_id, nombre, descripcion, "
            "precio, ingredientes, alergenos, vegano, vegetariano, sin_gluten, "
            "sin_lactosa, disponible, etiqueta) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s)",
            (
                restaurante_id,
                plato_id,
                categoria_id,
                nombre,
                descripcion,
                precio,
                Jsonb(ingredientes),
                Jsonb([a.value for a in alergenos]),
                vegano,
                vegetariano,
                sin_gluten,
                sin_lactosa,
                etiqueta.value if etiqueta else None,
            ),
        )
        return Plato(
            id=plato_id,
            categoria=categoria_id,
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            ingredientes=ingredientes,
            alergenos=alergenos,
            vegano=vegano,
            vegetariano=vegetariano,
            sin_gluten=sin_gluten,
            sin_lactosa=sin_lactosa,
            disponible=True,
            etiqueta=etiqueta,
            foto=None,
        )

    def crear_plato_especial(
        self,
        restaurante_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato:
        plato_id = f"especial-{secrets.token_hex(4)}"
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO categorias (restaurante_id, id, nombre, nombre_i18n, orden) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (restaurante_id, id) DO NOTHING",
                (restaurante_id, CATEGORIA_ESPECIALES, "Especial de hoy", Jsonb({}), -1),
            )
            return self._insertar_plato(
                cur,
                restaurante_id,
                plato_id,
                CATEGORIA_ESPECIALES,
                nombre,
                descripcion,
                precio,
                ingredientes,
                alergenos,
                etiqueta,
                vegano,
                vegetariano,
                sin_gluten,
                sin_lactosa,
            )

    def eliminar_plato_especial(self, restaurante_id: str, plato_id: str) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM platos WHERE restaurante_id = %s AND id = %s "
                "AND categoria_id = %s",
                (restaurante_id, plato_id, CATEGORIA_ESPECIALES),
            )
            return cur.rowcount > 0

    def eliminar_plato(self, restaurante_id: str, plato_id: str) -> bool:
        # Las traducciones caen en cascada (ON DELETE CASCADE en el esquema).
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM platos WHERE restaurante_id = %s AND id = %s",
                (restaurante_id, plato_id),
            )
            return cur.rowcount > 0

    def crear_categoria(self, restaurante_id: str, nombre: str) -> Categoria:
        base = slug_categoria(nombre)
        if not base:
            raise ValueError("El nombre de la categoria necesita al menos una letra o cifra")
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM categorias WHERE restaurante_id = %s", (restaurante_id,))
            categoria_id = id_categoria_libre(base, {f[0] for f in cur.fetchall()})
            # Al final de las demas. El especial de hoy vive en orden -1 y no
            # cuenta: si es la unica, MAX = -1 y la nueva sale con orden 0.
            cur.execute(
                "INSERT INTO categorias (restaurante_id, id, nombre, nombre_i18n, orden) "
                "VALUES (%s, %s, %s, %s, "
                "(SELECT COALESCE(MAX(orden), 0) + 1 FROM categorias WHERE restaurante_id = %s)) "
                "RETURNING orden",
                (restaurante_id, categoria_id, nombre, Jsonb({}), restaurante_id),
            )
            fila = cur.fetchone()
            assert fila is not None
        return Categoria(id=categoria_id, nombre=nombre, nombre_i18n={}, orden=fila[0])

    def renombrar_categoria(
        self, restaurante_id: str, categoria_id: str, nombre: str
    ) -> Categoria | None:
        if categoria_id == CATEGORIA_ESPECIALES:
            return None
        with self.pool.connection() as conn, conn.cursor() as cur:
            # nombre_i18n se vacia: una traduccion del nombre viejo mostraria en
            # otros idiomas un nombre que ya no es el de la categoria.
            cur.execute(
                "UPDATE categorias SET nombre = %s, nombre_i18n = %s "
                "WHERE restaurante_id = %s AND id = %s RETURNING orden",
                (nombre, Jsonb({}), restaurante_id, categoria_id),
            )
            fila = cur.fetchone()
        if fila is None:
            return None
        return Categoria(id=categoria_id, nombre=nombre, nombre_i18n={}, orden=fila[0])

    def ordenar_categorias(self, restaurante_id: str, ids: list[str]) -> bool:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM categorias WHERE restaurante_id = %s AND id <> %s",
                (restaurante_id, CATEGORIA_ESPECIALES),
            )
            actuales = {f[0] for f in cur.fetchall()}
            # Tiene que ser exactamente el conjunto actual: una lista a medias
            # o con ids ajenos dejaria ordenes duplicados o categorias sin mover.
            if len(ids) != len(set(ids)) or set(ids) != actuales:
                return False
            for posicion, categoria_id in enumerate(ids, start=1):
                cur.execute(
                    "UPDATE categorias SET orden = %s WHERE restaurante_id = %s AND id = %s",
                    (posicion, restaurante_id, categoria_id),
                )
        return True

    def eliminar_categoria(
        self, restaurante_id: str, categoria_id: str
    ) -> ResultadoEliminarCategoria:
        if categoria_id == CATEGORIA_ESPECIALES:
            return "no_existe"
        with self.pool.connection() as conn, conn.cursor() as cur:
            # Un solo DELETE condicionado a que no tenga platos: comprobar antes
            # y borrar despues dejaria una ventana en la que entra un plato.
            cur.execute(
                "DELETE FROM categorias c WHERE c.restaurante_id = %s AND c.id = %s "
                "AND NOT EXISTS (SELECT 1 FROM platos p "
                "WHERE p.restaurante_id = c.restaurante_id AND p.categoria_id = c.id)",
                (restaurante_id, categoria_id),
            )
            if cur.rowcount > 0:
                return "ok"
            cur.execute(
                "SELECT 1 FROM categorias WHERE restaurante_id = %s AND id = %s",
                (restaurante_id, categoria_id),
            )
            return "con_platos" if cur.fetchone() else "no_existe"

    def crear_plato(
        self,
        restaurante_id: str,
        categoria_id: str,
        nombre: str,
        descripcion: str,
        precio: float | None,
        ingredientes: list[str],
        alergenos: list[Alergeno],
        etiqueta: Etiqueta | None,
        vegano: bool,
        vegetariano: bool,
        sin_gluten: bool,
        sin_lactosa: bool,
    ) -> Plato | None:
        # El especial de hoy tiene su propio flujo (crear_plato_especial).
        if categoria_id == CATEGORIA_ESPECIALES:
            return None
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM categorias WHERE restaurante_id = %s AND id = %s",
                (restaurante_id, categoria_id),
            )
            if cur.fetchone() is None:
                return None
            return self._insertar_plato(
                cur,
                restaurante_id,
                id_plato_nuevo(),
                categoria_id,
                nombre,
                descripcion,
                precio,
                ingredientes,
                alergenos,
                etiqueta,
                vegano,
                vegetariano,
                sin_gluten,
                sin_lactosa,
            )

    def listar_restaurantes(self) -> list[ResumenRestaurante]:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT r.id, r.nombre, COUNT(p.id) "
                "FROM restaurantes r LEFT JOIN platos p ON p.restaurante_id = r.id "
                "GROUP BY r.id, r.nombre ORDER BY r.id"
            )
            filas = cur.fetchall()
        return [ResumenRestaurante(id=f[0], nombre=f[1], num_platos=f[2]) for f in filas]

    def crear_restaurante(self, restaurante_id: str, nombre: str, clave_hash: str) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO restaurantes (id, nombre, clave_hash) VALUES (%s, %s, %s)",
                (restaurante_id, nombre, clave_hash),
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


def obtener_clave_hash(restaurante_id: str) -> str | None:
    return obtener_repositorio_carta().obtener_clave_hash(restaurante_id)


def guardar_clave_hash(restaurante_id: str, clave_hash: str) -> None:
    obtener_repositorio_carta().guardar_clave_hash(restaurante_id, clave_hash)


def actualizar_plato_editable(
    restaurante_id: str,
    plato_id: str,
    nombre: str,
    descripcion: str,
    precio: float | None,
    ingredientes: list[str],
    alergenos: list[Alergeno],
    etiqueta: Etiqueta | None,
    vegano: bool,
    vegetariano: bool,
    sin_gluten: bool,
    sin_lactosa: bool,
) -> bool:
    return obtener_repositorio_carta().actualizar_plato_editable(
        restaurante_id,
        plato_id,
        nombre,
        descripcion,
        precio,
        ingredientes,
        alergenos,
        etiqueta,
        vegano,
        vegetariano,
        sin_gluten,
        sin_lactosa,
    )


def actualizar_disponibilidad(restaurante_id: str, plato_id: str, disponible: bool) -> bool:
    return obtener_repositorio_carta().actualizar_disponibilidad(
        restaurante_id, plato_id, disponible
    )


def actualizar_foto_plato(restaurante_id: str, plato_id: str, foto: str | None) -> bool:
    return obtener_repositorio_carta().actualizar_foto_plato(restaurante_id, plato_id, foto)


def actualizar_nombre_restaurante(restaurante_id: str, nombre: str) -> bool:
    return obtener_repositorio_carta().actualizar_nombre_restaurante(restaurante_id, nombre)


def actualizar_imagen_marca(restaurante_id: str, campo: CampoImagenMarca, url: str) -> bool:
    return obtener_repositorio_carta().actualizar_imagen_marca(restaurante_id, campo, url)


def crear_plato_especial(
    restaurante_id: str,
    nombre: str,
    descripcion: str,
    precio: float | None,
    ingredientes: list[str],
    alergenos: list[Alergeno],
    etiqueta: Etiqueta | None,
    vegano: bool,
    vegetariano: bool,
    sin_gluten: bool,
    sin_lactosa: bool,
) -> Plato:
    return obtener_repositorio_carta().crear_plato_especial(
        restaurante_id,
        nombre,
        descripcion,
        precio,
        ingredientes,
        alergenos,
        etiqueta,
        vegano,
        vegetariano,
        sin_gluten,
        sin_lactosa,
    )


def eliminar_plato_especial(restaurante_id: str, plato_id: str) -> bool:
    return obtener_repositorio_carta().eliminar_plato_especial(restaurante_id, plato_id)


def eliminar_plato(restaurante_id: str, plato_id: str) -> bool:
    return obtener_repositorio_carta().eliminar_plato(restaurante_id, plato_id)


def crear_categoria(restaurante_id: str, nombre: str) -> Categoria:
    return obtener_repositorio_carta().crear_categoria(restaurante_id, nombre)


def renombrar_categoria(restaurante_id: str, categoria_id: str, nombre: str) -> Categoria | None:
    return obtener_repositorio_carta().renombrar_categoria(restaurante_id, categoria_id, nombre)


def ordenar_categorias(restaurante_id: str, ids: list[str]) -> bool:
    return obtener_repositorio_carta().ordenar_categorias(restaurante_id, ids)


def eliminar_categoria(restaurante_id: str, categoria_id: str) -> ResultadoEliminarCategoria:
    return obtener_repositorio_carta().eliminar_categoria(restaurante_id, categoria_id)


def crear_plato(
    restaurante_id: str,
    categoria_id: str,
    nombre: str,
    descripcion: str,
    precio: float | None,
    ingredientes: list[str],
    alergenos: list[Alergeno],
    etiqueta: Etiqueta | None,
    vegano: bool,
    vegetariano: bool,
    sin_gluten: bool,
    sin_lactosa: bool,
) -> Plato | None:
    return obtener_repositorio_carta().crear_plato(
        restaurante_id,
        categoria_id,
        nombre,
        descripcion,
        precio,
        ingredientes,
        alergenos,
        etiqueta,
        vegano,
        vegetariano,
        sin_gluten,
        sin_lactosa,
    )


def listar_restaurantes() -> list[ResumenRestaurante]:
    return obtener_repositorio_carta().listar_restaurantes()


def crear_restaurante(restaurante_id: str, nombre: str, clave_hash: str) -> None:
    obtener_repositorio_carta().crear_restaurante(restaurante_id, nombre, clave_hash)
