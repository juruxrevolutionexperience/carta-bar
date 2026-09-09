from fastapi import FastAPI
from pydantic import BaseModel

from carta_bar.agente import responder_cliente
from carta_bar.busqueda import indexar
from carta_bar.embeddings import cargar_modelo

app = FastAPI()

modelo = cargar_modelo()
carta, vectores = indexar(modelo)


class Pregunta(BaseModel):
    texto: str


@app.get("/carta")
def obtener_carta():
    return carta


@app.post("/preguntar")
def preguntar(pregunta: Pregunta):
    respuesta = responder_cliente(pregunta.texto, modelo, carta, vectores)
    return {"respuesta": respuesta}