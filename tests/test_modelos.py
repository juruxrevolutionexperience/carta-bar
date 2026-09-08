import pytest
from pydantic import ValidationError

from carta_bar.modelos import Alergeno, Plato


def plato_base(**overrides: object) -> Plato:
    datos: dict[str, object] = dict(
        id="p001",
        nombre="Croquetas",
        descripcion="De jamón",
        precio=8.5,
        categoria="entrantes",
        ingredientes=["jamón", "leche"],
        alergenos=[Alergeno.GLUTEN, Alergeno.LACTEOS],
    )
    datos.update(overrides)
    return Plato(**datos)  # type: ignore[arg-type]


def test_plato_valido() -> None:
    plato = plato_base()
    assert plato.precio == 8.5


def test_precio_cero_falla() -> None:
    with pytest.raises(ValidationError):
        plato_base(precio=0)


def test_sin_gluten_con_gluten_falla() -> None:
    with pytest.raises(ValidationError):
        plato_base(sin_gluten=True, alergenos=[Alergeno.GLUTEN])


def test_alergeno_invalido_falla() -> None:
    with pytest.raises(ValidationError):
        plato_base(alergenos=["Gluten"])
