"""Si estas cuentas fallan, se factura mal. Van clavadas a la tarifa publicada."""

from anthropic.types import Usage

from carta_bar.costes import (
    Consumo,
    ConsumoTotal,
    calcular_coste,
    medir,
)


def test_un_millon_de_tokens_de_entrada_cuesta_un_dolar() -> None:
    assert calcular_coste(tokens_entrada=1_000_000, tokens_salida=0) == 1.00


def test_un_millon_de_tokens_de_salida_cuesta_cinco_dolares() -> None:
    assert calcular_coste(tokens_entrada=0, tokens_salida=1_000_000) == 5.00


def test_la_lectura_de_cache_es_una_decima_parte_de_la_entrada() -> None:
    entrada = calcular_coste(tokens_entrada=1_000_000, tokens_salida=0)
    cache = calcular_coste(tokens_entrada=0, tokens_salida=0, tokens_cache_lectura=1_000_000)
    assert cache * 10 == entrada


def test_sin_consumo_no_hay_coste() -> None:
    assert calcular_coste(tokens_entrada=0, tokens_salida=0) == 0.0


def test_medir_traduce_el_usage_de_la_api() -> None:
    uso = Usage(input_tokens=1000, output_tokens=500)
    consumo = medir("interprete", uso)

    assert consumo.llamada == "interprete"
    assert consumo.tokens_entrada == 1000
    assert consumo.tokens_salida == 500
    # 1000 * 1$/M + 500 * 5$/M
    assert consumo.coste_usd == 0.001 + 0.0025


def test_medir_tolera_los_campos_de_cache_vacios() -> None:
    # La API devuelve None, no 0, cuando no se usa cache.
    consumo = medir("respuesta", Usage(input_tokens=10, output_tokens=10))
    assert consumo.tokens_cache_lectura == 0
    assert consumo.tokens_cache_escritura == 0


def test_el_total_suma_todas_las_llamadas_de_una_pregunta() -> None:
    total = ConsumoTotal(
        consumos=[
            Consumo(llamada="interprete", tokens_entrada=300, tokens_salida=80, coste_usd=0.0007),
            Consumo(llamada="respuesta", tokens_entrada=900, tokens_salida=400, coste_usd=0.0029),
        ]
    )
    assert total.tokens_entrada == 1200
    assert total.tokens_salida == 480
    assert total.coste_usd == 0.0036


def test_un_total_vacio_no_cuesta_nada() -> None:
    assert ConsumoTotal().coste_usd == 0.0
