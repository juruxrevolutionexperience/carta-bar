from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Direccion(BaseModel):
    calle: str
    ciudad: str
    codigo_postal: str


class Cliente(BaseModel):
    nombre: str
    email: str
    direccion: Direccion


class Usuario(BaseModel):
    nombre: str
    edad: int
    email: str


class UsuarioEstricto(BaseModel):
    model_config = ConfigDict(strict=True)

    nombre: str
    edad: int
    email: str


class Persona(BaseModel):
    nombre: str
    edad: int

    @field_validator("edad")
    @classmethod
    def validar_edad(cls, edad: int) -> int:
        if edad < 0:
            raise ValueError("La edad no puede ser negativa")
        if edad > 120:
            raise ValueError("La edad no puede ser mayor a 120")
        return edad


class Reserva(BaseModel):
    fecha_inicio: date
    fecha_fin: date

    @model_validator(mode="after")
    def validar_fechas(self) -> "Reserva":
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("La fecha de fin debe ser posterior a la de inicio")
        return self


class Contacto(BaseModel):
    nombre: str
    email: str
    plan_interes: str
    quiere_demo: bool
