"""Contabilidad de lo que cuesta cada llamada al LLM.

Los tokens no se estiman: la propia API los devuelve contados en `usage`.
Aqui solo se traducen a dinero y se dejan en un formato que se pueda registrar,
sumar y, mas adelante, facturar por restaurante.
"""

from anthropic.types import Usage
from pydantic import BaseModel, Field

# Precios de Claude Haiku 4.5 en USD por millon de tokens.
PRECIO_ENTRADA = 1.00
PRECIO_SALIDA = 5.00
# La escritura en cache cuesta 1.25x la entrada; la lectura, 0.1x.
PRECIO_CACHE_ESCRITURA = PRECIO_ENTRADA * 1.25
PRECIO_CACHE_LECTURA = PRECIO_ENTRADA * 0.10

_MILLON = 1_000_000


class Consumo(BaseModel):
    """Lo que ha costado una unica llamada al modelo."""

    llamada: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    tokens_cache_escritura: int = 0
    tokens_cache_lectura: int = 0
    coste_usd: float = 0.0

    @property
    def tokens_totales(self) -> int:
        return (
            self.tokens_entrada
            + self.tokens_salida
            + self.tokens_cache_escritura
            + self.tokens_cache_lectura
        )


class ConsumoTotal(BaseModel):
    """La suma de todas las llamadas hechas para responder a un cliente."""

    consumos: list[Consumo] = Field(default_factory=list)

    @property
    def coste_usd(self) -> float:
        return sum(c.coste_usd for c in self.consumos)

    @property
    def tokens_entrada(self) -> int:
        return sum(c.tokens_entrada for c in self.consumos)

    @property
    def tokens_salida(self) -> int:
        return sum(c.tokens_salida for c in self.consumos)


def calcular_coste(
    tokens_entrada: int,
    tokens_salida: int,
    tokens_cache_escritura: int = 0,
    tokens_cache_lectura: int = 0,
) -> float:
    """Convierte tokens en dolares segun la tarifa del modelo."""
    return (
        tokens_entrada * PRECIO_ENTRADA
        + tokens_salida * PRECIO_SALIDA
        + tokens_cache_escritura * PRECIO_CACHE_ESCRITURA
        + tokens_cache_lectura * PRECIO_CACHE_LECTURA
    ) / _MILLON


def medir(llamada: str, uso: Usage) -> Consumo:
    """Traduce el `usage` que devuelve la API a un Consumo con su coste."""
    escritura = uso.cache_creation_input_tokens or 0
    lectura = uso.cache_read_input_tokens or 0
    return Consumo(
        llamada=llamada,
        tokens_entrada=uso.input_tokens,
        tokens_salida=uso.output_tokens,
        tokens_cache_escritura=escritura,
        tokens_cache_lectura=lectura,
        coste_usd=calcular_coste(uso.input_tokens, uso.output_tokens, escritura, lectura),
    )
