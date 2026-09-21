"""Una traduccion vieja no se enseña: un plato editado sale en español hasta
que se rehace, en vez de con los ingredientes de la version anterior."""

from carta_bar.datos import _con_traducciones
from carta_bar.modelos import Plato, huella_texto


def plato(**cambios: object) -> Plato:
    datos: dict[str, object] = {
        "id": "p1",
        "categoria": "postres",
        "nombre": "Flan",
        "descripcion": "Con caramelo",
        "ingredientes": ["huevo", "leche"],
        "alergenos": [],
    }
    return Plato.model_validate({**datos, **cambios})


def traduccion(p: Plato) -> dict[str, dict[str, object]]:
    return {
        p.id: {
            "id": p.id,
            "hash": huella_texto(p),
            "nombre": "Custard",
            "descripcion": "With caramel",
            "ingredientes": ["egg", "milk"],
        }
    }


def test_traduccion_vigente_se_aplica() -> None:
    p = plato()
    fila = _con_traducciones([p], traduccion(p))[0]
    assert fila["nombre"] == "Custard"
    assert fila["ingredientes"] == ["egg", "milk"]


def test_traduccion_vieja_se_descarta_y_sale_en_español() -> None:
    editado = plato(ingredientes=["huevo", "leche", "almendra"])
    vieja = traduccion(plato())
    fila = _con_traducciones([editado], vieja)[0]
    assert fila["nombre"] == "Flan"
    assert fila["ingredientes"] == ["huevo", "leche", "almendra"]


def test_sin_traduccion_sale_en_español() -> None:
    assert _con_traducciones([plato()], {})[0]["nombre"] == "Flan"


def test_precio_y_alergenos_no_dependen_de_la_traduccion() -> None:
    p = plato(precio=4.5, alergenos=["huevos", "lacteos"])
    fila = _con_traducciones([p], traduccion(p))[0]
    assert fila["precio"] == 4.5
    assert fila["alergenos"] == ["huevos", "lacteos"]
