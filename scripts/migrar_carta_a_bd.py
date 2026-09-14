"""Migra la carta de datos/<restaurante_id>/*.json a Postgres.

Uso de un solo golpe, pero idempotente: se puede ejecutar mas de una vez sin
duplicar nada (todo son UPSERT). Aplica sql/esquema.sql antes de insertar,
por si las tablas nuevas todavia no existen.

Uso:
    python scripts/migrar_carta_a_bd.py [restaurante_id]

Si no se pasa restaurante_id, usa RESTAURANTE_ID del entorno o "la-catedral".
"""

import json
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()


def _conninfo() -> str:
    usuario = os.environ["POSTGRES_USER"]
    clave = os.environ["POSTGRES_PASSWORD"]
    base = os.environ["POSTGRES_DB"]
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"


def migrar(restaurante_id: str) -> None:
    base_dir = Path(f"datos/{restaurante_id}")
    config = json.loads((base_dir / "config.json").read_text(encoding="utf-8"))
    categorias = json.loads((base_dir / "categorias.json").read_text(encoding="utf-8"))
    carta = json.loads((base_dir / "carta.json").read_text(encoding="utf-8"))

    with psycopg.connect(_conninfo()) as conn:
        conn.execute(Path("sql/esquema.sql").read_text(encoding="utf-8"))

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO restaurantes
                    (id, nombre, subtitulo, color_marca, moneda, foto_portada, logo,
                     aviso_alergenos, aviso_alergenos_i18n)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    nombre = EXCLUDED.nombre, subtitulo = EXCLUDED.subtitulo,
                    color_marca = EXCLUDED.color_marca, moneda = EXCLUDED.moneda,
                    foto_portada = EXCLUDED.foto_portada, logo = EXCLUDED.logo,
                    aviso_alergenos = EXCLUDED.aviso_alergenos,
                    aviso_alergenos_i18n = EXCLUDED.aviso_alergenos_i18n
                """,
                (
                    restaurante_id,
                    config.get("nombre", ""),
                    config.get("subtitulo", ""),
                    config.get("color_marca", "#000000"),
                    config.get("moneda", "€"),
                    config.get("foto_portada", ""),
                    config.get("logo", ""),
                    config.get("aviso_alergenos", ""),
                    Jsonb(config.get("aviso_alergenos_i18n", {})),
                ),
            )
            print(f"restaurantes: 1 fila ({restaurante_id})")

            for c in categorias:
                cur.execute(
                    """
                    INSERT INTO categorias (restaurante_id, id, nombre, nombre_i18n, orden)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (restaurante_id, id) DO UPDATE SET
                        nombre = EXCLUDED.nombre, nombre_i18n = EXCLUDED.nombre_i18n,
                        orden = EXCLUDED.orden
                    """,
                    (
                        restaurante_id,
                        c["id"],
                        c["nombre"],
                        Jsonb(c.get("nombre_i18n", {})),
                        c["orden"],
                    ),
                )
            print(f"categorias: {len(categorias)} filas")

            for p in carta:
                cur.execute(
                    """
                    INSERT INTO platos
                        (restaurante_id, id, categoria_id, nombre, descripcion, precio,
                         ingredientes, alergenos, vegano, vegetariano, sin_gluten,
                         sin_lactosa, disponible, etiqueta, foto)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (restaurante_id, id) DO UPDATE SET
                        categoria_id = EXCLUDED.categoria_id, nombre = EXCLUDED.nombre,
                        descripcion = EXCLUDED.descripcion, precio = EXCLUDED.precio,
                        ingredientes = EXCLUDED.ingredientes, alergenos = EXCLUDED.alergenos,
                        vegano = EXCLUDED.vegano, vegetariano = EXCLUDED.vegetariano,
                        sin_gluten = EXCLUDED.sin_gluten, sin_lactosa = EXCLUDED.sin_lactosa,
                        disponible = EXCLUDED.disponible, etiqueta = EXCLUDED.etiqueta,
                        foto = EXCLUDED.foto
                    """,
                    (
                        restaurante_id,
                        p["id"],
                        p["categoria"],
                        p["nombre"],
                        p["descripcion"],
                        p.get("precio"),
                        Jsonb(p.get("ingredientes", [])),
                        Jsonb(p.get("alergenos", [])),
                        p.get("vegano", False),
                        p.get("vegetariano", False),
                        p.get("sin_gluten", False),
                        p.get("sin_lactosa", False),
                        p.get("disponible", True),
                        p.get("etiqueta"),
                        p.get("foto"),
                    ),
                )
            print(f"platos: {len(carta)} filas")

            total_traducciones = 0
            for idioma in ("en", "de", "fr"):
                ruta = base_dir / f"carta.{idioma}.json"
                if not ruta.exists():
                    continue
                traducciones = json.loads(ruta.read_text(encoding="utf-8"))
                for t in traducciones:
                    cur.execute(
                        """
                        INSERT INTO traducciones_platos
                            (restaurante_id, plato_id, idioma, hash, nombre, descripcion,
                             ingredientes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (restaurante_id, plato_id, idioma) DO UPDATE SET
                            hash = EXCLUDED.hash, nombre = EXCLUDED.nombre,
                            descripcion = EXCLUDED.descripcion,
                            ingredientes = EXCLUDED.ingredientes
                        """,
                        (
                            restaurante_id,
                            t["id"],
                            idioma,
                            t["hash"],
                            t["nombre"],
                            t["descripcion"],
                            Jsonb(t.get("ingredientes", [])),
                        ),
                    )
                total_traducciones += len(traducciones)
            print(f"traducciones_platos: {total_traducciones} filas")

        conn.commit()
    print("Migracion completada.")


if __name__ == "__main__":
    _por_defecto = os.getenv("RESTAURANTE_ID", "la-catedral")
    _restaurante_id = sys.argv[1] if len(sys.argv) > 1 else _por_defecto
    migrar(_restaurante_id)
