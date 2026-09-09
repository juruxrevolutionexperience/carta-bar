from enum import Enum

from pydantic import BaseModel, field_validator, model_validator


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
    precio: float
    categoria: str
    ingredientes: list[str]
    alergenos: list[Alergeno]
    vegano: bool = False
    vegetariano: bool = False
    sin_gluten: bool = False
    sin_lactosa: bool = False
    disponible: bool = True
    etiqueta: Etiqueta | None = None

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, precio: float) -> float:
        if precio <= 0:
            raise ValueError("El precio debe ser mayor que cero")
        return precio

    @model_validator(mode="after")
    def validar_coherencia_gluten(self) -> "Plato":
        if self.sin_gluten and Alergeno.GLUTEN in self.alergenos:
            raise ValueError("Un plato sin_gluten no puede listar GLUTEN entre sus alergenos")
        return self


class RestriccionesCliente(BaseModel):
    vegano: bool = False
    vegetariano: bool = False
    sin_gluten: bool = False
    sin_lactosa: bool = False
    alergenos_excluir: list[Alergeno] = []
    ingredientes_excluir: list[str] = []
    intencion_busqueda: str = ""
    categoria_pedida: str = ""


class Categoria(BaseModel):
    id: str
    nombre: str
    orden: int
