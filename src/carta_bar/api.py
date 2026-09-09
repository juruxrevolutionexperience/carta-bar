import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from carta_bar.agente import responder_cliente
from carta_bar.busqueda import indexar
from carta_bar.datos import cargar_carta_traducida, cargar_categorias
from carta_bar.embeddings import cargar_modelo
from carta_bar.modelos import Categoria

app = FastAPI()

modelo = cargar_modelo()
carta, vectores = indexar(modelo, "la-catedral")


class Pregunta(BaseModel):
    texto: str


@app.get("/carta")
def obtener_carta(idioma: str = "es") -> list[dict[str, object]]:
    return cargar_carta_traducida("la-catedral", idioma)



@app.get("/categorias")
def obtener_categorias() -> list[Categoria]:
    return cargar_categorias("la-catedral")


@app.get("/config")
def obtener_config() -> dict[str, object]:
    ruta = Path("datos/la-catedral/config.json")
    datos: dict[str, object] = json.loads(ruta.read_text(encoding="utf-8"))
    return datos


@app.post("/preguntar")
def preguntar(pregunta: Pregunta) -> dict[str, str]:
    respuesta = responder_cliente(pregunta.texto, modelo, carta, vectores, "la-catedral")
    return {"respuesta": respuesta}



@app.get("/idiomas")
def obtener_idiomas() -> dict[str, object]:
    datos: dict[str, object] = json.loads(Path("datos/idiomas.json").read_text(encoding="utf-8"))
    return datos


@app.get("/")
def inicio() -> FileResponse:
    return FileResponse("web/index.html")
