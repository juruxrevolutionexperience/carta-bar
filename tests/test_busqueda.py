import pytest
from sentence_transformers import SentenceTransformer

from carta_bar.busqueda import filtrar_por_restricciones_cliente, indexar
from carta_bar.modelos import Alergeno, RestriccionesCliente


@pytest.fixture(scope="module")
def modelo() -> SentenceTransformer:
    from carta_bar.embeddings import cargar_modelo

    return cargar_modelo()


def test_filtro_vegano_excluye_no_veganos(modelo: SentenceTransformer) -> None:
    carta, _ = indexar(modelo)
    r = RestriccionesCliente(vegano=True)
    resultado = filtrar_por_restricciones_cliente(carta, r)
    assert all(p.vegano for p in resultado)


def test_filtro_alergeno_excluye_platos_con_ese_alergeno(modelo: SentenceTransformer) -> None:
    carta, _ = indexar(modelo)
    r = RestriccionesCliente(alergenos_excluir=[Alergeno.LACTEOS])
    resultado = filtrar_por_restricciones_cliente(carta, r)
    assert all(Alergeno.LACTEOS not in p.alergenos for p in resultado)


def test_filtro_ingrediente_excluye_platos_con_ese_ingrediente(
    modelo: SentenceTransformer,
) -> None:
    carta, _ = indexar(modelo)
    r = RestriccionesCliente(ingredientes_excluir=["gamba"])
    resultado = filtrar_por_restricciones_cliente(carta, r)
    assert all("gamba" not in ing.lower() for p in resultado for ing in p.ingredientes)
