import json
import os
from pathlib import Path
from typing import Literal

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded

from carta_bar.agente import responder_cliente
from carta_bar.busqueda import indexar
from carta_bar.datos import cargar_carta_traducida, cargar_categorias
from carta_bar.embeddings import cargar_modelo
from carta_bar.limites import LIMITE_PREGUNTAR, limite_superado, limiter
from carta_bar.llm import MODELO
from carta_bar.logging_config import configurar_logging
from carta_bar.modelos import Categoria, MensajeChat
from carta_bar.presupuesto import AVISO_SIN_PRESUPUESTO, ControlGasto
from carta_bar.uso import crear_repositorio

# En produccion conviene JSON: es lo que sabe agregar cualquier gestor de logs.
configurar_logging(json_logs=os.getenv("LOGS_JSON", "false").lower() == "true")
log = structlog.get_logger()

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, limite_superado)

modelo = cargar_modelo()
carta, vectores = indexar(modelo, "la-catedral")
control = ControlGasto(crear_repositorio())


Idioma = Literal["es", "en", "de", "fr"]

# El historial lo manda el navegador, así que es entrada no fiable y además
# entra en el prompt: cada mensaje son tokens que se pagan. Ocho turnos cubren
# de sobra una conversación de mesa y ponen techo al coste por petición.
MAX_HISTORIAL = 8


class Pregunta(BaseModel):
    texto: str = Field(min_length=1, max_length=500)
    idioma: Idioma = "es"
    historial: list[MensajeChat] = Field(default_factory=list, max_length=MAX_HISTORIAL)


@app.get("/carta")
def obtener_carta(idioma: Idioma = "es") -> list[dict[str, object]]:
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
@limiter.limit(LIMITE_PREGUNTAR)
def preguntar(request: Request, pregunta: Pregunta) -> dict[str, str]:
    restaurante_id = "la-catedral"

    # El corte va ANTES de llamar al LLM: comprobarlo despues no ahorraria nada.
    if not control.hay_presupuesto(restaurante_id):
        aviso = AVISO_SIN_PRESUPUESTO.get(pregunta.idioma, AVISO_SIN_PRESUPUESTO["es"])
        return {"respuesta": aviso}

    resultado = responder_cliente(
        pregunta.texto,
        modelo,
        carta,
        vectores,
        restaurante_id,
        pregunta.idioma,
        pregunta.historial,
    )
    control.registrar(restaurante_id, MODELO, resultado.consumo)

    # Una linea por pregunta atendida: es la materia prima para facturar y para
    # detectar un consumo anomalo antes de que llegue en la factura.
    log.info(
        "consulta_atendida",
        restaurante_id=restaurante_id,
        idioma=pregunta.idioma,
        llamadas=len(resultado.consumo.consumos),
        tokens_entrada=resultado.consumo.tokens_entrada,
        tokens_salida=resultado.consumo.tokens_salida,
        coste_usd=round(resultado.consumo.coste_usd, 6),
    )
    return {"respuesta": resultado.texto}


@app.get("/idiomas")
def obtener_idiomas() -> dict[str, object]:
    datos: dict[str, object] = json.loads(Path("datos/idiomas.json").read_text(encoding="utf-8"))
    return datos


@app.get("/")
def inicio() -> FileResponse:
    return FileResponse("web/index.html")
