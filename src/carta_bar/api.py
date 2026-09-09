from fastapi import FastAPI
from pydantic import BaseModel

from carta_bar.agente import responder_cliente
from carta_bar.busqueda import indexar
from carta_bar.embeddings import cargar_modelo
from carta_bar.modelos import Plato

app = FastAPI()

modelo = cargar_modelo()
carta, vectores = indexar(modelo)


class Pregunta(BaseModel):
    texto: str


@app.get("/carta")
def obtener_carta() -> list[Plato]:
    return carta


@app.post("/preguntar")
def preguntar(pregunta: Pregunta) -> dict[str, str]:
    respuesta = responder_cliente(pregunta.texto, modelo, carta, vectores)
    return {"respuesta": respuesta}
