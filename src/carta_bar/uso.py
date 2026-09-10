"""Registro de uso del LLM: cuanto se ha gastado, quien y cuando.

El acceso a datos vive detras de un Protocol a proposito. Asi el corte por
presupuesto se puede probar entero sin levantar una base de datos, y cambiar
Postgres por otra cosa no obliga a tocar la logica de negocio.
"""

import os
from typing import Protocol

import psycopg
import structlog
from psycopg_pool import ConnectionPool

from carta_bar.costes import ConsumoTotal

log = structlog.get_logger()

_INSERTAR = """
INSERT INTO uso_llm (
    restaurante_id, llamada, modelo,
    tokens_entrada, tokens_salida,
    tokens_cache_escritura, tokens_cache_lectura, coste_usd
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""

_GASTO_DEL_DIA = """
SELECT COALESCE(SUM(coste_usd), 0)
FROM uso_llm
WHERE restaurante_id = %s
  AND creado_en >= date_trunc('day', now())
"""


class RepositorioUso(Protocol):
    """Lo minimo que necesita el control de gasto para hacer su trabajo."""

    def registrar(self, restaurante_id: str, modelo: str, consumo: ConsumoTotal) -> None: ...

    def gasto_del_dia(self, restaurante_id: str) -> float: ...


class RepositorioMemoria:
    """Guarda el uso en memoria. Para tests y para arrancar sin base de datos."""

    def __init__(self) -> None:
        self.gastos: dict[str, float] = {}
        self.filas: list[tuple[str, str, float]] = []

    def registrar(self, restaurante_id: str, modelo: str, consumo: ConsumoTotal) -> None:
        for c in consumo.consumos:
            self.filas.append((restaurante_id, c.llamada, c.coste_usd))
        self.gastos[restaurante_id] = self.gastos.get(restaurante_id, 0.0) + consumo.coste_usd

    def gasto_del_dia(self, restaurante_id: str) -> float:
        return self.gastos.get(restaurante_id, 0.0)


class RepositorioPostgres:
    """Persiste el uso en la tabla uso_llm (ver sql/esquema.sql)."""

    def __init__(self, conninfo: str) -> None:
        # El pool importa: gasto_del_dia se consulta en CADA pregunta, y abrir
        # una conexion nueva contra un Postgres remoto costaria mas que la query.
        self.pool = ConnectionPool(conninfo, min_size=1, max_size=4, open=True)

    def registrar(self, restaurante_id: str, modelo: str, consumo: ConsumoTotal) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            for c in consumo.consumos:
                cur.execute(
                    _INSERTAR,
                    (
                        restaurante_id,
                        c.llamada,
                        modelo,
                        c.tokens_entrada,
                        c.tokens_salida,
                        c.tokens_cache_escritura,
                        c.tokens_cache_lectura,
                        c.coste_usd,
                    ),
                )

    def gasto_del_dia(self, restaurante_id: str) -> float:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_GASTO_DEL_DIA, (restaurante_id,))
            fila = cur.fetchone()
            return float(fila[0]) if fila else 0.0

    def aplicar_esquema(self, ruta: str = "sql/esquema.sql") -> None:
        with open(ruta, encoding="utf-8") as f:
            sql = f.read()
        with self.pool.connection() as conn:
            conn.execute(sql)


def crear_repositorio() -> RepositorioUso:
    """Postgres si hay credenciales; memoria si no, para no bloquear el arranque."""
    usuario = os.getenv("POSTGRES_USER", "")
    clave = os.getenv("POSTGRES_PASSWORD", "")
    base = os.getenv("POSTGRES_DB", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    puerto = os.getenv("POSTGRES_PORT", "5432")

    if not (usuario and clave and base):
        log.warning(
            "uso_sin_persistencia",
            motivo="faltan credenciales de POSTGRES en el entorno",
            efecto="el gasto se contabiliza en memoria y se pierde al reiniciar",
        )
        return RepositorioMemoria()

    conninfo = f"postgresql://{usuario}:{clave}@{host}:{puerto}/{base}"
    try:
        repo = RepositorioPostgres(conninfo)
        repo.aplicar_esquema()
        log.info("uso_persistente", destino=f"{host}:{puerto}/{base}")
        return repo
    except (psycopg.Error, OSError) as e:
        log.error("uso_sin_persistencia", motivo=str(e), efecto="se contabiliza en memoria")
        return RepositorioMemoria()
