import pytest
from sentence_transformers import SentenceTransformer

from carta_bar.embeddings import cargar_modelo, similitud


@pytest.fixture(scope="module")
def modelo() -> SentenceTransformer:
    return cargar_modelo()


def test_temas_distintos_tienen_similitud_baja(modelo: SentenceTransformer) -> None:
    resultado = similitud(
        "El contrato entra en vigor el 1 de enero.",
        "La pizza estaba deliciosa.",
        modelo,
    )
    assert resultado < 0.3


def test_la_negacion_no_baja_la_similitud(modelo: SentenceTransformer) -> None:
    resultado = similitud(
        "El contrato entra en vigor el 1 de enero.",
        "El contrato NO entra en vigor el 1 de enero.",
        modelo,
    )
    assert resultado > 0.7
