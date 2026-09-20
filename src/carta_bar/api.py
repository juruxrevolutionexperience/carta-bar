import json
import os
import re
import time
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
import psycopg
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
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
    crear_categoria,
    crear_plato,
    crear_plato_especial,
    crear_restaurante,
    eliminar_categoria,
    eliminar_plato,
    eliminar_plato_especial,
    guardar_clave_hash,
    listar_restaurantes,
    obtener_clave_hash,
    ordenar_categorias,
    renombrar_categoria,
    slug_categoria,
)
from carta_bar.embeddings import cargar_modelo
from carta_bar.limites import LIMITE_LOGIN, LIMITE_PREGUNTAR, limite_superado, limiter
from carta_bar.llm import MODELO
from carta_bar.logging_config import configurar_logging
from carta_bar.modelos import Alergeno, Categoria, Etiqueta, MensajeChat, Plato, ResumenRestaurante
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

# Bundle de las pantallas ya migradas a React (Vite).
DIR_FRONTEND = Path("web/dist")
# check_dir=False: la carpeta no existe hasta el primer "npm run build" (o en
# los tests, donde nunca se pide un asset), y sin esto el montaje fallaria al
# arrancar.
app.mount("/assets", StaticFiles(directory=DIR_FRONTEND / "assets", check_dir=False), name="assets")

RESTAURANTE_ID = os.getenv("RESTAURANTE_ID", "la-catedral")

# Contraseña del dueño de la plataforma, no de ningun restaurante: vive en
# .env, nunca en la base de datos de restaurantes.
SUPERADMIN_CLAVE_HASH = os.getenv("SUPERADMIN_CLAVE_HASH")
COOKIE_SESION_SUPERADMIN = "sesion_superadmin"
TOKEN_SUPERADMIN = "__superadmin__"

# "cartia" es el subdominio historico de La CatedRal; nuevos restaurantes
# usan directamente su id como subdominio, sin hacer falta alias.
ALIAS_SUBDOMINIO = {"cartia": "la-catedral"}


def _restaurante_existe(restaurante_id: str) -> bool:
    try:
        cargar_config(restaurante_id)
        return True
    except (ValueError, FileNotFoundError):
        return False


# Hosts desde los que se trabaja en local (TestClient usa "testserver" por
# defecto). Aqui, y solo aqui, cae al restaurante fijo: no son subdominios
# de verdad, no tiene sentido pedirles que sean un restaurante real.
_HOSTS_DESARROLLO_LOCAL = {"localhost", "127.0.0.1", "testserver"}


def _resolver_restaurante(request: Request) -> str:
    """Que restaurante sirve esta peticion, segun el subdominio del Host.

    Sin esto, todo el sitio serviria siempre el mismo restaurante fijo -
    es lo que separa `bar2.jurux.app` de `la-catedral.jurux.app` en el
    mismo servidor, sin desplegar nada aparte por cliente.
    """
    host = request.headers.get("host", "").split(":")[0]
    if host in _HOSTS_DESARROLLO_LOCAL:
        return RESTAURANTE_ID

    subdominio = host.split(".")[0]
    restaurante_id = ALIAS_SUBDOMINIO.get(subdominio, subdominio)
    try:
        _validar_slug(restaurante_id, "restaurante_id")
    except ValueError:
        raise HTTPException(status_code=404, detail="Esta carta no existe") from None
    if _restaurante_existe(restaurante_id):
        return restaurante_id
    # Con el DNS en comodin (*.jurux.app), cualquier subdominio inventado
    # llega hasta aqui: sin este error, enseñaria el restaurante fijo de
    # otro cliente en vez de decir que este no existe.
    raise HTTPException(status_code=404, detail="Esta carta no existe")


RestauranteActual = Annotated[str, Depends(_resolver_restaurante)]

modelo = cargar_modelo()
control = ControlGasto(crear_repositorio())

# Indice de busqueda del chat: uno por restaurante, calculado la primera vez
# que se le pregunta algo (no todos de golpe al arrancar). Se vacia para un
# restaurante en concreto cuando se edita un plato suyo, para que el chat no
# acabe respondiendo con datos viejos.
_indices: dict[str, tuple[list[Plato], np.ndarray]] = {}


def _indice_de(restaurante_id: str) -> tuple[list[Plato], np.ndarray]:
    if restaurante_id not in _indices:
        _indices[restaurante_id] = indexar(modelo, restaurante_id)
    return _indices[restaurante_id]


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
def obtener_carta(
    restaurante_id: RestauranteActual, idioma: Idioma = "es"
) -> list[dict[str, object]]:
    return cargar_carta_traducida(restaurante_id, idioma)


@app.get("/categorias")
def obtener_categorias(restaurante_id: RestauranteActual) -> list[Categoria]:
    return cargar_categorias(restaurante_id)


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
def obtener_config(restaurante_id: RestauranteActual) -> dict[str, object]:
    datos = cargar_config(restaurante_id)
    return {k: v for k, v in datos.items() if k in CAMPOS_CONFIG_PUBLICOS}


@app.post("/preguntar")
@limiter.limit(LIMITE_PREGUNTAR)
def preguntar(
    request: Request, pregunta: Pregunta, restaurante_id: RestauranteActual
) -> dict[str, str]:
    # El corte va ANTES de llamar al LLM: comprobarlo despues no ahorraria nada.
    if not control.hay_presupuesto(restaurante_id):
        aviso = AVISO_SIN_PRESUPUESTO.get(pregunta.idioma, AVISO_SIN_PRESUPUESTO["es"])
        return {"respuesta": aviso}

    carta, vectores = _indice_de(restaurante_id)
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
def inicio() -> HTMLResponse:
    # Migrada a React (Vite), igual que /admin/login y /admin: el bundle es
    # un <script> externo del mismo origen, ya permitido por el CSP con 'self'.
    return HTMLResponse((DIR_FRONTEND / "index.html").read_text(encoding="utf-8"))


COOKIE_SESION = "sesion_admin"


def _sesion_activa(request: Request, restaurante_id: str) -> bool:
    # Compara contra el restaurante de ESTA peticion (por subdominio), no
    # contra uno fijo: una sesion de bar2.jurux.app no debe valer en
    # la-catedral.jurux.app aunque el token en si sea valido.
    token = request.cookies.get(COOKIE_SESION)
    if token is None:
        return False
    return verificar_token_sesion(token) == restaurante_id


class LoginPeticion(BaseModel):
    clave: str = Field(min_length=1, max_length=200)


class CambiarClavePeticion(BaseModel):
    clave_actual: str = Field(min_length=1, max_length=200)
    clave_nueva: str = Field(min_length=8, max_length=200)


@app.get("/admin/login")
def admin_login_pagina() -> HTMLResponse:
    # Migrada a React (Vite): el bundle es un <script> externo del mismo
    # origen, ya permitido por el CSP con 'self' sin necesitar el nonce.
    return HTMLResponse((DIR_FRONTEND / "admin-login.html").read_text(encoding="utf-8"))


@app.post("/admin/login")
@limiter.limit(LIMITE_LOGIN)
def admin_login(
    request: Request, peticion: LoginPeticion, restaurante_id: RestauranteActual
) -> Response:
    hash_guardado = obtener_clave_hash(restaurante_id)
    if hash_guardado is None or not verificar_clave(peticion.clave, hash_guardado):
        return Response(status_code=401, content="Contraseña incorrecta")

    token = crear_token_sesion(restaurante_id)
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
def admin_panel(request: Request, restaurante_id: RestauranteActual) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return RedirectResponse("/admin/login", status_code=303)
    # Migrado a React (Vite), igual que /admin/login: el bundle es un
    # <script> externo del mismo origen, ya permitido por el CSP con 'self'.
    return HTMLResponse((DIR_FRONTEND / "admin.html").read_text(encoding="utf-8"))


@app.post("/admin/cambiar-clave")
def admin_cambiar_clave(
    request: Request, peticion: CambiarClavePeticion, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")

    hash_guardado = obtener_clave_hash(restaurante_id)
    if hash_guardado is None or not verificar_clave(peticion.clave_actual, hash_guardado):
        return Response(status_code=401, content="Contraseña actual incorrecta")

    guardar_clave_hash(restaurante_id, hash_clave(peticion.clave_nueva))
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
    plato_id: str,
    peticion: ActualizarPlatoPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = actualizar_plato_editable(
        restaurante_id,
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
    _indices.pop(restaurante_id, None)
    return Response(status_code=204)


class ActualizarDisponibilidadPeticion(BaseModel):
    disponible: bool


@app.post("/admin/api/platos/{plato_id}/disponibilidad")
def admin_actualizar_disponibilidad(
    plato_id: str,
    peticion: ActualizarDisponibilidadPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = actualizar_disponibilidad(restaurante_id, plato_id, peticion.disponible)
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    _indices.pop(restaurante_id, None)
    return Response(status_code=204)


class CrearPlatoEspecialPeticion(BaseModel):
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
    def validar_coherencia_gluten(self) -> "CrearPlatoEspecialPeticion":
        if self.sin_gluten and Alergeno.GLUTEN in self.alergenos:
            raise ValueError("Un plato sin_gluten no puede listar GLUTEN entre sus alergenos")
        return self


@app.post("/admin/api/platos/especiales", status_code=201, response_model=None)
def admin_crear_especial(
    peticion: CrearPlatoEspecialPeticion, request: Request, restaurante_id: RestauranteActual
) -> Plato | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    creado = crear_plato_especial(
        restaurante_id,
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
    _indices.pop(restaurante_id, None)
    return creado


@app.delete("/admin/api/platos/especiales/{plato_id}")
def admin_eliminar_especial(
    plato_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = eliminar_plato_especial(restaurante_id, plato_id)
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    _ruta_foto(restaurante_id, plato_id).unlink(missing_ok=True)
    _indices.pop(restaurante_id, None)
    return Response(status_code=204)


@app.delete("/admin/api/platos/{plato_id}")
def admin_eliminar_plato(
    plato_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not eliminar_plato(restaurante_id, plato_id):
        return Response(status_code=404, content="Plato no encontrado")
    _ruta_foto(restaurante_id, plato_id).unlink(missing_ok=True)
    _indices.pop(restaurante_id, None)
    return Response(status_code=204)


class CrearPlatoPeticion(CrearPlatoEspecialPeticion):
    categoria: str = Field(min_length=1, max_length=100)


@app.post("/admin/api/platos", status_code=201, response_model=None)
def admin_crear_plato(
    peticion: CrearPlatoPeticion, request: Request, restaurante_id: RestauranteActual
) -> Plato | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    creado = crear_plato(
        restaurante_id,
        peticion.categoria,
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
    if creado is None:
        return Response(status_code=404, content="Categoría no encontrada")
    _indices.pop(restaurante_id, None)
    return creado


class NombreCategoriaPeticion(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, nombre: str) -> str:
        # Espacios de sobra fuera, y al menos una letra o cifra: el id de la
        # categoria se deriva del nombre y no puede salir vacio.
        limpio = " ".join(nombre.split())
        if not slug_categoria(limpio):
            raise ValueError("El nombre necesita al menos una letra o una cifra")
        return limpio


class OrdenCategoriasPeticion(BaseModel):
    ids: list[str] = Field(max_length=200)


@app.post("/admin/api/categorias", status_code=201, response_model=None)
def admin_crear_categoria(
    peticion: NombreCategoriaPeticion, request: Request, restaurante_id: RestauranteActual
) -> Categoria | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return crear_categoria(restaurante_id, peticion.nombre)


@app.put("/admin/api/categorias/{categoria_id}", response_model=None)
def admin_renombrar_categoria(
    categoria_id: str,
    peticion: NombreCategoriaPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Categoria | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    renombrada = renombrar_categoria(restaurante_id, categoria_id, peticion.nombre)
    if renombrada is None:
        return Response(status_code=404, content="Categoría no encontrada")
    return renombrada


# Ruta propia y no /categorias/orden: chocaria con /categorias/{categoria_id}.
@app.put("/admin/api/orden-categorias", response_model=None)
def admin_ordenar_categorias(
    peticion: OrdenCategoriasPeticion, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not ordenar_categorias(restaurante_id, peticion.ids):
        return Response(status_code=400, content="La lista no coincide con las categorías actuales")
    return Response(status_code=204)


@app.delete("/admin/api/categorias/{categoria_id}")
def admin_eliminar_categoria(
    categoria_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = eliminar_categoria(restaurante_id, categoria_id)
    if resultado == "no_existe":
        return Response(status_code=404, content="Categoría no encontrada")
    if resultado == "con_platos":
        return Response(
            status_code=409,
            content="La categoría tiene platos: muévelos o elimínalos antes de borrarla",
        )
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
async def admin_subir_foto(
    plato_id: str, request: Request, foto: UploadFile, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")

    contenido = await foto.read(TAMANO_MAX_FOTO + 1)
    if len(contenido) > TAMANO_MAX_FOTO:
        return Response(status_code=413, content="La foto pesa demasiado")
    if not contenido.startswith(_CABECERA_JPEG):
        return Response(status_code=400, content="Solo se aceptan imagenes JPEG")

    ruta = _ruta_foto(restaurante_id, plato_id)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)

    url = f"/fotos/{restaurante_id}/{plato_id}.jpg?v={int(time.time())}"
    encontrado = actualizar_foto_plato(restaurante_id, plato_id, url)
    if not encontrado:
        ruta.unlink(missing_ok=True)
        return Response(status_code=404, content="Plato no encontrado")
    return Response(content=json.dumps({"foto": url}), media_type="application/json")


@app.delete("/admin/api/platos/{plato_id}/foto")
def admin_borrar_foto(
    plato_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    encontrado = actualizar_foto_plato(restaurante_id, plato_id, None)
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    _ruta_foto(restaurante_id, plato_id).unlink(missing_ok=True)
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


# ------------------------------------------------------ panel superadmin
#
# No es de ningun restaurante: es el panel del dueño de la plataforma, para
# dar de alta restaurantes nuevos sin tocar la base de datos a mano. Sesion
# y cookie completamente aparte de las de /admin.


def _sesion_superadmin_activa(request: Request) -> bool:
    token = request.cookies.get(COOKIE_SESION_SUPERADMIN)
    return token is not None and verificar_token_sesion(token) == TOKEN_SUPERADMIN


class SuperadminLoginPeticion(BaseModel):
    clave: str = Field(min_length=1, max_length=200)


@app.get("/superadmin/login")
def superadmin_login_pagina() -> HTMLResponse:
    return HTMLResponse((DIR_FRONTEND / "superadmin-login.html").read_text(encoding="utf-8"))


@app.post("/superadmin/login")
@limiter.limit(LIMITE_LOGIN)
def superadmin_login(request: Request, peticion: SuperadminLoginPeticion) -> Response:
    if SUPERADMIN_CLAVE_HASH is None or not verificar_clave(peticion.clave, SUPERADMIN_CLAVE_HASH):
        return Response(status_code=401, content="Contraseña incorrecta")

    token = crear_token_sesion(TOKEN_SUPERADMIN)
    respuesta = Response(status_code=204)
    respuesta.set_cookie(
        COOKIE_SESION_SUPERADMIN,
        token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=12 * 60 * 60,
    )
    return respuesta


@app.get("/superadmin")
def superadmin_panel(request: Request) -> Response:
    if not _sesion_superadmin_activa(request):
        return RedirectResponse("/superadmin/login", status_code=303)
    return HTMLResponse((DIR_FRONTEND / "superadmin.html").read_text(encoding="utf-8"))


@app.post("/superadmin/logout")
def superadmin_logout() -> Response:
    respuesta = Response(status_code=204)
    respuesta.delete_cookie(COOKIE_SESION_SUPERADMIN)
    return respuesta


@app.get("/superadmin/api/restaurantes", response_model=None)
def superadmin_listar_restaurantes(request: Request) -> list[ResumenRestaurante] | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    return listar_restaurantes()


class CrearRestaurantePeticion(BaseModel):
    restaurante_id: str = Field(min_length=1, max_length=100)
    nombre: str = Field(min_length=1, max_length=200)
    clave: str = Field(min_length=8, max_length=200)

    @field_validator("restaurante_id")
    @classmethod
    def validar_restaurante_id(cls, valor: str) -> str:
        return _validar_slug(valor, "restaurante_id")


@app.post("/superadmin/api/restaurantes", status_code=201, response_model=None)
def superadmin_crear_restaurante(
    peticion: CrearRestaurantePeticion, request: Request
) -> ResumenRestaurante | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    try:
        crear_restaurante(peticion.restaurante_id, peticion.nombre, hash_clave(peticion.clave))
    except psycopg.errors.UniqueViolation:
        return Response(status_code=409, content="Ese subdominio ya está en uso")
    return ResumenRestaurante(id=peticion.restaurante_id, nombre=peticion.nombre, num_platos=0)
