"""Metricas de uso por restaurante: visitas a la carta, preguntas al chat y coste.

Son contadores por dia, no una fila por evento: la tabla no crece con el
trafico y no se guarda nada de quien visita (ni IP ni texto de las preguntas,
que pueden contener datos de salud, como una alergia).

Los dias se cuentan en hora de España: con UTC, la cena de un bar caeria a
caballo entre dos dias.

Ninguna funcion de registro puede romper la carta ni el chat: si la base de
datos falla, se avisa en el log y se sigue.
"""

from collections import defaultdict
from typing import Protocol

import structlog
from pydantic import BaseModel, Field, computed_field

from carta_bar.uso import RepositorioPostgres, RepositorioUso

log = structlog.get_logger()

# Robots que abren enlaces sin ser un cliente: vistas previas de WhatsApp o
# Telegram al compartir el enlace, buscadores, monitores. Contarlos inflaria
# las visitas justo el dia que el gerente comparte el enlace con alguien.
_MARCAS_DE_ROBOT = (
    "bot",
    "crawler",
    "spider",
    "preview",
    "facebookexternalhit",
    "whatsapp",
    "telegram",
    "slack",
    "curl",
    "python-requests",
    "headless",
    "uptime",
)


def es_robot(user_agent: str | None) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(marca in ua for marca in _MARCAS_DE_ROBOT)


# Ultimos N dias, contando hoy (en hora de España).
_HOY = "(now() AT TIME ZONE 'Europe/Madrid')::date"

_SUMAR_VISITA = f"""
INSERT INTO visitas_diarias (restaurante_id, dia, visitas)
VALUES (%s, {_HOY}, 1)
ON CONFLICT (restaurante_id, dia)
DO UPDATE SET visitas = visitas_diarias.visitas + 1
"""

_SUMAR_PREGUNTA = f"""
INSERT INTO preguntas_diarias
    (restaurante_id, dia, idioma, preguntas, conversaciones, rechazadas)
VALUES (%s, {_HOY}, %s, %s, %s, %s)
ON CONFLICT (restaurante_id, dia, idioma) DO UPDATE SET
    preguntas = preguntas_diarias.preguntas + EXCLUDED.preguntas,
    conversaciones = preguntas_diarias.conversaciones + EXCLUDED.conversaciones,
    rechazadas = preguntas_diarias.rechazadas + EXCLUDED.rechazadas
"""

_LEER_VISITAS = f"""
SELECT restaurante_id, COALESCE(SUM(visitas), 0)
FROM visitas_diarias
WHERE dia >= {_HOY} - (%s::int - 1)
GROUP BY restaurante_id
"""

_LEER_PREGUNTAS = f"""
SELECT restaurante_id, idioma,
       COALESCE(SUM(preguntas), 0),
       COALESCE(SUM(conversaciones), 0),
       COALESCE(SUM(rechazadas), 0)
FROM preguntas_diarias
WHERE dia >= {_HOY} - (%s::int - 1)
GROUP BY restaurante_id, idioma
"""

# Las traducciones las paga el restaurante al editar la carta, no un cliente
# al preguntar: se separan para que el coste por pregunta no se contamine.
_LEER_COSTES = f"""
SELECT restaurante_id,
       COALESCE(SUM(coste_usd) FILTER (WHERE llamada LIKE 'traduccion:%%'), 0),
       COALESCE(SUM(coste_usd) FILTER (WHERE llamada NOT LIKE 'traduccion:%%'), 0)
FROM uso_llm
WHERE creado_en >= (({_HOY} - (%s::int - 1))::timestamp AT TIME ZONE 'Europe/Madrid')
GROUP BY restaurante_id
"""


class MetricasRestaurante(BaseModel):
    restaurante_id: str
    visitas: int = 0
    preguntas: int = 0
    conversaciones: int = 0
    rechazadas: int = 0
    preguntas_por_idioma: dict[str, int] = Field(default_factory=dict)
    coste_chat_usd: float = 0.0
    coste_traducciones_usd: float = 0.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def coste_por_pregunta_usd(self) -> float | None:
        return self.coste_chat_usd / self.preguntas if self.preguntas else None


class RepositorioMetricas(Protocol):
    def registrar_visita(self, restaurante_id: str) -> None: ...

    def registrar_pregunta(
        self, restaurante_id: str, idioma: str, *, conversacion_nueva: bool, rechazada: bool
    ) -> None: ...

    def resumen(self, dias: int) -> list[MetricasRestaurante]: ...


class RepositorioMetricasMemoria:
    """Para tests y para arrancar sin base de datos: se pierde al reiniciar."""

    def __init__(self) -> None:
        self.visitas: dict[str, int] = defaultdict(int)
        self.preguntas: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])

    def registrar_visita(self, restaurante_id: str) -> None:
        self.visitas[restaurante_id] += 1

    def registrar_pregunta(
        self, restaurante_id: str, idioma: str, *, conversacion_nueva: bool, rechazada: bool
    ) -> None:
        fila = self.preguntas[(restaurante_id, idioma)]
        if rechazada:
            fila[2] += 1
            return
        fila[0] += 1
        fila[1] += int(conversacion_nueva)

    def resumen(self, dias: int) -> list[MetricasRestaurante]:
        # En memoria no hay historico por dia: "dias" no filtra nada.
        ids = set(self.visitas) | {rid for rid, _ in self.preguntas}
        filas = []
        for rid in sorted(ids):
            fila = MetricasRestaurante(restaurante_id=rid, visitas=self.visitas.get(rid, 0))
            for (r, idioma), (n, conv, rech) in self.preguntas.items():
                if r != rid:
                    continue
                fila.preguntas += n
                fila.conversaciones += conv
                fila.rechazadas += rech
                if n:
                    fila.preguntas_por_idioma[idioma] = n
            filas.append(fila)
        return filas


class RepositorioMetricasPostgres:
    """Comparte el pool del repositorio de uso: otro pool propio gastaria
    conexiones de Supabase, que son pocas."""

    def __init__(self, uso: RepositorioPostgres) -> None:
        self.pool = uso.pool

    def registrar_visita(self, restaurante_id: str) -> None:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_SUMAR_VISITA, (restaurante_id,))

    def registrar_pregunta(
        self, restaurante_id: str, idioma: str, *, conversacion_nueva: bool, rechazada: bool
    ) -> None:
        preguntas = 0 if rechazada else 1
        conversaciones = 1 if conversacion_nueva and not rechazada else 0
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                _SUMAR_PREGUNTA,
                (restaurante_id, idioma, preguntas, conversaciones, int(rechazada)),
            )

    def resumen(self, dias: int) -> list[MetricasRestaurante]:
        filas: dict[str, MetricasRestaurante] = {}

        def de(rid: str) -> MetricasRestaurante:
            return filas.setdefault(rid, MetricasRestaurante(restaurante_id=rid))

        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(_LEER_VISITAS, (dias,))
            for rid, visitas in cur.fetchall():
                de(rid).visitas = int(visitas)

            cur.execute(_LEER_PREGUNTAS, (dias,))
            for rid, idioma, n, conv, rech in cur.fetchall():
                fila = de(rid)
                fila.preguntas += int(n)
                fila.conversaciones += int(conv)
                fila.rechazadas += int(rech)
                if n:
                    fila.preguntas_por_idioma[idioma] = int(n)

            cur.execute(_LEER_COSTES, (dias,))
            for rid, traducciones, chat in cur.fetchall():
                fila = de(rid)
                fila.coste_traducciones_usd = float(traducciones)
                fila.coste_chat_usd = float(chat)
        return sorted(filas.values(), key=lambda f: f.restaurante_id)


def crear_repositorio_metricas(uso: RepositorioUso) -> RepositorioMetricas:
    """Postgres si el gasto ya se guarda ahi; memoria si no."""
    if isinstance(uso, RepositorioPostgres):
        return RepositorioMetricasPostgres(uso)
    return RepositorioMetricasMemoria()


def anotar_visita(repo: RepositorioMetricas, restaurante_id: str) -> None:
    try:
        repo.registrar_visita(restaurante_id)
    except Exception as e:
        log.warning("metrica_no_registrada", tipo="visita", motivo=str(e))


def anotar_pregunta(
    repo: RepositorioMetricas,
    restaurante_id: str,
    idioma: str,
    *,
    conversacion_nueva: bool,
    rechazada: bool = False,
) -> None:
    try:
        repo.registrar_pregunta(
            restaurante_id, idioma, conversacion_nueva=conversacion_nueva, rechazada=rechazada
        )
    except Exception as e:
        log.warning("metrica_no_registrada", tipo="pregunta", motivo=str(e))
