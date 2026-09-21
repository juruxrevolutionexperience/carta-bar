import hashlib
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from carta_bar.costes import ConsumoTotal


class Alergeno(str, Enum):
    GLUTEN = "gluten"
    CRUSTACEOS = "crustaceos"
    HUEVOS = "huevos"
    PESCADO = "pescado"
    CACAHUETES = "cacahuetes"
    SOJA = "soja"
    LACTEOS = "lacteos"
    FRUTOS_CASCARA = "frutos_cascara"
    APIO = "apio"
    MOSTAZA = "mostaza"
    SESAMO = "sesamo"
    SULFITOS = "sulfitos"
    ALTRAMUCES = "altramuces"
    MOLUSCOS = "moluscos"


class Etiqueta(str, Enum):
    MAS_VENDIDO = "mas_vendido"
    RECOMENDACION_CHEF = "recomendacion_chef"
    NUEVO = "nuevo"
    PICANTE = "picante"
    PARA_COMPARTIR = "para_compartir"
    TEMPORADA = "temporada"


class Plato(BaseModel):
    id: str
    nombre: str
    descripcion: str
    precio: float | None = None
    categoria: str
    ingredientes: list[str]
    alergenos: list[Alergeno]
    vegano: bool = False
    vegetariano: bool = False
    sin_gluten: bool = False
    sin_lactosa: bool = False
    disponible: bool = True
    etiqueta: Etiqueta | None = None
    # El restaurante ha revisado los alergenos y la dieta de este plato. Sin
    # eso (p. ej. un plato importado de una foto, con alergenos adivinados por
    # el LLM) nunca se presenta como apto ni se recomienda ante una restriccion.
    alergenos_confirmados: bool = True
    # Sin foto, la tarjeta pinta un degradado con un icono. El frontend solo
    # acepta http(s), rutas propias y data: de imagen, y descarta el resto.
    foto: str | None = None

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, precio: float | None) -> float | None:
        if precio is not None and precio <= 0:
            raise ValueError("El precio debe ser mayor que cero")
        return precio

    @model_validator(mode="after")
    def validar_coherencia_gluten(self) -> "Plato":
        if self.sin_gluten and Alergeno.GLUTEN in self.alergenos:
            raise ValueError("Un plato sin_gluten no puede listar GLUTEN entre sus alergenos")
        return self


def huella_texto(plato: Plato) -> str:
    """Identifica el texto traducible de un plato: si cambia, su traduccion
    guardada deja de valer."""
    base = plato.nombre + "|" + plato.descripcion + "|" + "|".join(plato.ingredientes)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


class RestriccionesCliente(BaseModel):
    vegano: bool = False
    vegetariano: bool = False
    sin_gluten: bool = False
    sin_lactosa: bool = False
    alergenos_excluir: list[Alergeno] = []
    ingredientes_excluir: list[str] = []
    intencion_busqueda: str = ""
    categoria_pedida: str = ""
    # El cliente ya ha elegido y no quiere mas sugerencias. Sin esto, el bot
    # sigue ofreciendo platos despues de un "con esto voy servido".
    pedido_cerrado: bool = False


class MensajeChat(BaseModel):
    """Un turno de la conversacion, tal y como lo manda el navegador."""

    rol: Literal["cliente", "asistente"]
    texto: str = Field(min_length=1, max_length=1000)


class Categoria(BaseModel):
    id: str
    nombre: str
    nombre_i18n: dict[str, str] = {}
    orden: int


class ResumenRestaurante(BaseModel):
    """Una fila del panel superadmin: lo minimo para ver que restaurantes hay."""

    id: str
    nombre: str
    num_platos: int


class RespuestaAgente(BaseModel):
    """Lo que el agente responde y lo que ha costado producirlo."""

    texto: str
    consumo: ConsumoTotal
