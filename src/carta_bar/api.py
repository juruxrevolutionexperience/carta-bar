import json
import os
import re
import time
from pathlib import Path
from typing import Literal

import structlog
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field, field_validator, model_validator
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from carta_bar.agente import responder_cliente
from carta_bar.auth import crear_token_sesion, hash_clave, verificar_clave, verificar_token_sesion
from carta_bar.busqueda import indexar
from carta_bar.datos import (
    _validar_slug,
    actualizar_disponibilidad,
    actualizar_foto_plato,
    actualizar_plato_editable,
    cargar_carta_traducida,
    cargar_categorias,
    cargar_config,
    guardar_clave_hash,
    obtener_clave_hash,
)
from carta_bar.embeddings import cargar_modelo
from carta_bar.limites import LIMITE_LOGIN, LIMITE_PREGUNTAR, limite_superado, limiter
from carta_bar.llm import MODELO
from carta_bar.logging_config import configurar_logging
from carta_bar.modelos import Alergeno, Categoria, Etiqueta, MensajeChat
from carta_bar.presupuesto import AVISO_SIN_PRESUPUESTO, ControlGasto
from carta_bar.seguridad import CabecerasSeguridad
from carta_bar.uso import crear_repositorio

# En produccion conviene JSON: es lo que sabe agregar cualquier gestor de logs.
configurar_logging(json_logs=os.getenv("LOGS_JSON", "false").lower() == "true")
log = structlog.get_logger()

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, limite_superado)
# Sin este middleware, el limite general no se aplica a las rutas que no
# llevan decorador propio.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CabecerasSeguridad)

RESTAURANTE_ID = os.getenv("RESTAURANTE_ID", "la-catedral")

modelo = cargar_modelo()
carta, vectores = indexar(modelo, RESTAURANTE_ID)
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
    return cargar_carta_traducida(RESTAURANTE_ID, idioma)


@app.get("/categorias")
def obtener_categorias() -> list[Categoria]:
    return cargar_categorias(RESTAURANTE_ID)


# Lista blanca de lo que la carta publica puede ver. El fichero de configuracion
# acabara teniendo datos de facturacion, claves o webhooks del restaurante:
# devolverlo entero seria filtrarlos a cualquiera que abra la carta.
CAMPOS_CONFIG_PUBLICOS = frozenset(
    {
        "nombre",
        "subtitulo",
        "color_marca",
        "moneda",
        "foto_portada",
        "logo",
        "aviso_alergenos",
        "aviso_alergenos_i18n",
    }
)


@app.get("/config")
def obtener_config() -> dict[str, object]:
    datos = cargar_config(RESTAURANTE_ID)
    return {k: v for k, v in datos.items() if k in CAMPOS_CONFIG_PUBLICOS}


@app.post("/preguntar")
@limiter.limit(LIMITE_PREGUNTAR)
def preguntar(request: Request, pregunta: Pregunta) -> dict[str, str]:
    restaurante_id = RESTAURANTE_ID

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
def inicio(request: Request) -> HTMLResponse:
    # El <script> de la pagina lleva el nonce de esta peticion. Cualquier otro
    # script que apareciera en el HTML (inyectado) no lo tendria, y el navegador
    # se negaria a ejecutarlo.
    pagina = Path("web/index.html").read_text(encoding="utf-8")
    with_nonce = pagina.replace("<script>", f'<script nonce="{request.state.nonce}">', 1)
    return HTMLResponse(with_nonce)


COOKIE_SESION = "sesion_admin"


def _pagina_con_nonce(ruta: str, request: Request) -> HTMLResponse:
    pagina = Path(ruta).read_text(encoding="utf-8")
    with_nonce = pagina.replace("<script>", f'<script nonce="{request.state.nonce}">', 1)
    return HTMLResponse(with_nonce)


def _sesion_activa(request: Request) -> bool:
    token = request.cookies.get(COOKIE_SESION)
    if token is None:
        return False
    return verificar_token_sesion(token) == RESTAURANTE_ID


class LoginPeticion(BaseModel):
    clave: str = Field(min_length=1, max_length=200)


class CambiarClavePeticion(BaseModel):
    clave_actual: str = Field(min_length=1, max_length=200)
    clave_nueva: str = Field(min_length=8, max_length=200)


@app.get("/admin/login")
def admin_login_pagina(request: Request) -> HTMLResponse:
    return _pagina_con_nonce("web/admin_login.html", request)


@app.post("/admin/login")
@limiter.limit(LIMITE_LOGIN)
def admin_login(request: Request, peticion: LoginPeticion) -> Response:
    hash_guardado = obtener_clave_hash(RESTAURANTE_ID)
    if hash_guardado is None or not verificar_clave(peticion.clave, hash_guardado):
        return Response(status_code=401, content="Contraseña incorrecta")

    token = crear_token_sesion(RESTAURANTE_ID)
    respuesta = Response(status_code=204)
    respuesta.set_cookie(
        COOKIE_SESION,
        token,
        httponly=True,
        # "secure" exige HTTPS. En local (http://127.0.0.1) se prueba sin TLS;
        # en produccion, detras de nginx con HTTPS, el navegador la exige.
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=12 * 60 * 60,
    )
    return respuesta


@app.get("/admin")
def admin_panel(request: Request) -> Response:
    if not _sesion_activa(request):
        return RedirectResponse("/admin/login", status_code=303)
    return _pagina_con_nonce("web/admin.html", request)


@app.post("/admin/cambiar-clave")
def admin_cambiar_clave(request: Request, peticion: CambiarClavePeticion) -> Response:
    if not _sesion_activa(request):
        return Response(status_code=401, content="Sesión no válida")

    hash_guardado = obtener_clave_hash(RESTAURANTE_ID)
    if hash_guardado is None or not verificar_clave(peticion.clave_actual, hash_guardado):
        return Response(status_code=401, content="Contraseña actual incorrecta")

    guardar_clave_hash(RESTAURANTE_ID, hash_clave(peticion.clave_nueva))
    return Response(status_code=204)


@app.post("/admin/logout")
def admin_logout() -> Response:
    respuesta = Response(status_code=204)
    respuesta.delete_cookie(COOKIE_SESION)
    return respuesta


class ActualizarPlatoPeticion(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1, max_length=1000)
    precio: float | None = None
    ingredientes: list[str] = Field(default_factory=list, max_length=50)
    alergenos: list[Alergeno] = Field(default_factory=list)
    etiqueta: Etiqueta | None = None
    vegano: bool = False
    vegetariano: bool = False
    sin_gluten: bool = False
    sin_lactosa: bool = False

    @field_validator("precio")
    @classmethod
    def validar_precio(cls, precio: float | None) -> float | None:
        if precio is not None and precio <= 0:
            raise ValueError("El precio debe ser mayor que cero")
        return precio

    @model_validator(mode="after")
    def validar_coherencia_gluten(self) -> "ActualizarPlatoPeticion":
        if self.sin_gluten and Alergeno.GLUTEN in self.alergenos:
            raise ValueError("Un plato sin_gluten no puede listar GLUTEN entre sus alergenos")
        return self


@app.put("/admin/api/platos/{plato_id}")
def admin_actualizar_plato(
    plato_id: str, peticion: ActualizarPlatoPeticion, request: Request
) -> Response:
    if not _sesion_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = actualizar_plato_editable(
        RESTAURANTE_ID,
        plato_id,
        peticion.nombre,
        peticion.descripcion,
        peticion.precio,
        peticion.ingredientes,
        peticion.alergenos,
        peticion.etiqueta,
        peticion.vegano,
        peticion.vegetariano,
        peticion.sin_gluten,
        peticion.sin_lactosa,
    )
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    return Response(status_code=204)


class ActualizarDisponibilidadPeticion(BaseModel):
    disponible: bool


@app.post("/admin/api/platos/{plato_id}/disponibilidad")
def admin_actualizar_disponibilidad(
    plato_id: str, peticion: ActualizarDisponibilidadPeticion, request: Request
) -> Response:
    if not _sesion_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = actualizar_disponibilidad(RESTAURANTE_ID, plato_id, peticion.disponible)
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    return Response(status_code=204)


# Comprimida en el navegador (canvas, JPEG calidad 0.8) antes de llegar aqui:
# el servidor no hace procesado de imagen, solo valida y guarda.
DIR_FOTOS = Path("datos/fotos")
TAMANO_MAX_FOTO = 3 * 1024 * 1024
_CABECERA_JPEG = b"\xff\xd8\xff"
_NOMBRE_ARCHIVO_FOTO = re.compile(r"^[a-zA-Z0-9_-]+\.jpg$")


def _ruta_foto(restaurante_id: str, plato_id: str) -> Path:
    _validar_slug(restaurante_id, "restaurante_id")
    _validar_slug(plato_id, "plato_id")
    return DIR_FOTOS / restaurante_id / f"{plato_id}.jpg"


@app.post("/admin/api/platos/{plato_id}/foto")
async def admin_subir_foto(plato_id: str, request: Request, foto: UploadFile) -> Response:
    if not _sesion_activa(request):
        return Response(status_code=401, content="Sesión no válida")

    contenido = await foto.read(TAMANO_MAX_FOTO + 1)
    if len(contenido) > TAMANO_MAX_FOTO:
        return Response(status_code=413, content="La foto pesa demasiado")
    if not contenido.startswith(_CABECERA_JPEG):
        return Response(status_code=400, content="Solo se aceptan imagenes JPEG")

    ruta = _ruta_foto(RESTAURANTE_ID, plato_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)

    url = f"/fotos/{RESTAURANTE_ID}/{plato_id}.jpg?v={int(time.time())}"
    encontrado = actualizar_foto_plato(RESTAURANTE_ID, plato_id, url)
    if not encontrado:
        ruta.unlink(missing_ok=True)
        return Response(status_code=404, content="Plato no encontrado")
    return Response(content=json.dumps({"foto": url}), media_type="application/json")


@app.delete("/admin/api/platos/{plato_id}/foto")
def admin_borrar_foto(plato_id: str, request: Request) -> Response:
    if not _sesion_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = actualizar_foto_plato(RESTAURANTE_ID, plato_id, None)
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    _ruta_foto(RESTAURANTE_ID, plato_id).unlink(missing_ok=True)
    return Response(status_code=204)


@app.get("/fotos/{restaurante_id}/{archivo}")
def obtener_foto(restaurante_id: str, archivo: str) -> Response:
    _validar_slug(restaurante_id, "restaurante_id")
    if not _NOMBRE_ARCHIVO_FOTO.match(archivo):
        return Response(status_code=404)
    ruta = DIR_FOTOS / restaurante_id / archivo
    if not ruta.is_file():
        return Response(status_code=404)
    return Response(content=ruta.read_bytes(), media_type="image/jpeg")
