import json
import os
import re
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
import psycopg
import structlog
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from carta_bar.agente import responder_cliente
from carta_bar.auth import crear_token_sesion, hash_clave, verificar_clave, verificar_token_sesion
from carta_bar.busqueda import indexar
from carta_bar.comandas import (
    Linea as LineaTicket,
)
from carta_bar.comandas import (
    OpcionElegida as OpcionElegidaTicket,
)
from carta_bar.comandas import (
    ResumenComanda,
    Ticket,
    anular_linea,
    crear_comanda,
    crear_repositorio_comandas,
    resumen_comandas,
)
from carta_bar.costes import ConsumoTotal
from carta_bar.datos import (
    CampoImagenMarca,
    _validar_slug,
    actualizar_disponibilidad,
    actualizar_foto_plato,
    actualizar_imagen_marca,
    actualizar_nombre_restaurante,
    actualizar_plato_editable,
    cargar_carta,
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
    guardar_texto_qr,
    listar_restaurantes,
    obtener_clave_hash,
    obtener_texto_qr,
    ordenar_categorias,
    renombrar_categoria,
    slug_categoria,
)
from carta_bar.embeddings import cargar_modelo
from carta_bar.importador import PlatoLeido, leer_platos_de_foto
from carta_bar.limites import LIMITE_LOGIN, LIMITE_PREGUNTAR, limite_superado, limiter
from carta_bar.llm import MODELO, MODELO_TRADUCCION
from carta_bar.logging_config import configurar_logging
from carta_bar.mesas import (
    Comensal,
    ComensalExpulsadoError,
    FormaMesa,
    Mesa,
    MiSesion,
    SesionCambiadaError,
    SesionMesa,
    Zona,
    ZonaNoExisteError,
    abrir_mesa,
    cobrar_mesa,
    confirmar_mesa,
    crear_repositorio_mesas,
    entrar_por_qr,
    expulsar_comensal,
    liberar_mesa,
    mesas_del_local,
    mi_sesion,
    pedir_cuenta,
    sesion_de_mesa,
)
from carta_bar.metricas import (
    MetricasRestaurante,
    anotar_pregunta,
    anotar_visita,
    crear_repositorio_metricas,
    es_robot,
)
from carta_bar.modelos import Alergeno, Categoria, Etiqueta, MensajeChat, Plato, ResumenRestaurante
from carta_bar.presupuesto import AVISO_SIN_PRESUPUESTO, ControlGasto
from carta_bar.productos import (
    ConfigProductos,
    DatosGrupo,
    DatosPedidoPlato,
    Destino,
    GrupoNoExisteError,
    GrupoOpciones,
    PedidoPlato,
    asignar_grupo_a_platos,
    con_formatos,
    config_productos,
    crear_repositorio_productos,
    destino_de,
    grupos_de_plato,
)
from carta_bar.propuestas import (
    ComandaMesa,
    OpcionElegida,
    Propuesta,
    ajustar_precio,
    confirmar_pendientes,
    crear_repositorio_propuestas,
    proponer,
    resumen_mesa,
    retirar,
)
from carta_bar.seguridad import CabecerasSeguridad
from carta_bar.traductor import traducir_restaurante
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
_repositorio_uso = crear_repositorio()
control = ControlGasto(_repositorio_uso)
metricas = crear_repositorio_metricas(_repositorio_uso)
mesas = crear_repositorio_mesas()
productos = crear_repositorio_productos()
propuestas = crear_repositorio_propuestas()
comandas = crear_repositorio_comandas()

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
    return con_formatos(productos, restaurante_id, cargar_carta_traducida(restaurante_id, idioma))


@app.get("/categorias")
def obtener_categorias(restaurante_id: RestauranteActual) -> list[Categoria]:
    return cargar_categorias(restaurante_id)


# Aparte de /carta a proposito: los extras solo se piden al proponer un plato
# concreto (boton "Pedir"), no se cargan con toda la carta.
@app.get("/platos/{plato_id}/grupos")
def obtener_grupos_de_plato(
    plato_id: str, restaurante_id: RestauranteActual
) -> list[GrupoOpciones]:
    return grupos_de_plato(productos, restaurante_id, plato_id)


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
    request: Request,
    pregunta: Pregunta,
    restaurante_id: RestauranteActual,
    tareas: BackgroundTasks,
) -> dict[str, str]:
    # Una conversacion empieza cuando la pregunta llega sin historial: es la
    # unica forma de contarlas sin cambiar como funciona el chat.
    empieza_conversacion = not pregunta.historial

    # El corte va ANTES de llamar al LLM: comprobarlo despues no ahorraria nada.
    if not control.hay_presupuesto(restaurante_id):
        tareas.add_task(
            anotar_pregunta,
            metricas,
            restaurante_id,
            pregunta.idioma,
            conversacion_nueva=empieza_conversacion,
            rechazada=True,
        )
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
    tareas.add_task(
        anotar_pregunta,
        metricas,
        restaurante_id,
        pregunta.idioma,
        conversacion_nueva=empieza_conversacion,
    )

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
def inicio(request: Request, tareas: BackgroundTasks) -> HTMLResponse:
    # Cada carga de la carta es una visita, salvo robots (vistas previas al
    # compartir el enlace) y el propio gerente con la sesion abierta. Sin
    # depender de RestauranteActual: esta pagina se sirve tambien desde una
    # direccion que no es un bar, y ahi no debe empezar a dar 404.
    try:
        restaurante_id: str | None = _resolver_restaurante(request)
    except HTTPException:
        restaurante_id = None
    if (
        restaurante_id
        and not es_robot(request.headers.get("user-agent"))
        and not _sesion_activa(request, restaurante_id)
    ):
        tareas.add_task(anotar_visita, metricas, restaurante_id)

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


@app.get("/admin/impresion")
def admin_impresion(request: Request, restaurante_id: RestauranteActual) -> Response:
    """Pantalla aparte para el aparato dedicado a imprimir en cocina/barra
    (docs/PEDIDO-EN-MESA.md, "Impresion en cocina/barra"): nunca en el TPV
    principal del bar. Misma sesion de gerente que el resto del panel."""
    if not _sesion_activa(request, restaurante_id):
        return RedirectResponse("/admin/login", status_code=303)
    return HTMLResponse((DIR_FRONTEND / "impresion.html").read_text(encoding="utf-8"))


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
    # None = no tocar lo que ya hay: un cliente que no lo mande no puede
    # desconfirmar por descuido los alergenos de un plato ya revisado.
    alergenos_confirmados: bool | None = None

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
    tareas: BackgroundTasks,
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
        alergenos_confirmados=peticion.alergenos_confirmados,
    )
    if not encontrado:
        return Response(status_code=404, content="Plato no encontrado")
    _indices.pop(restaurante_id, None)
    tareas.add_task(traducir_restaurante, restaurante_id, control)
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
    # Un plato nuevo entra sin confirmar salvo que el gerente diga que ha
    # revisado los alergenos: no se da por bueno lo que nadie ha mirado.
    alergenos_confirmados: bool = False

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
    peticion: CrearPlatoEspecialPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
    tareas: BackgroundTasks,
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
        alergenos_confirmados=peticion.alergenos_confirmados,
    )
    _indices.pop(restaurante_id, None)
    tareas.add_task(traducir_restaurante, restaurante_id, control)
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
    peticion: CrearPlatoPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
    tareas: BackgroundTasks,
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
        alergenos_confirmados=peticion.alergenos_confirmados,
    )
    if creado is None:
        return Response(status_code=404, content="Categoría no encontrada")
    _indices.pop(restaurante_id, None)
    tareas.add_task(traducir_restaurante, restaurante_id, control)
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


# ------------------------------------------------ productos: lo que hace falta para pedir
#
# carta_bar/productos.py. Destino (cocina/barra) por categoria, y por plato:
# formatos con precio, grupos de extras/opciones y si lleva alcohol.


@app.get("/admin/api/productos", response_model=None)
def admin_config_productos(
    request: Request, restaurante_id: RestauranteActual
) -> ConfigProductos | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return config_productos(productos, restaurante_id)


class DestinoPeticion(BaseModel):
    destino: Destino


@app.put("/admin/api/categorias/{categoria_id}/destino")
def admin_destino_categoria(
    categoria_id: str,
    peticion: DestinoPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if categoria_id not in {c.id for c in cargar_categorias(restaurante_id)}:
        return Response(status_code=404, content="Categoría no encontrada")
    productos.fijar_destino_categoria(restaurante_id, categoria_id, peticion.destino)
    return Response(status_code=204)


@app.put("/admin/api/platos/{plato_id}/pedido", response_model=None)
def admin_pedido_plato(
    plato_id: str,
    peticion: DatosPedidoPlato,
    request: Request,
    restaurante_id: RestauranteActual,
) -> PedidoPlato | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if plato_id not in {p.id for p in cargar_carta(restaurante_id)}:
        return Response(status_code=404, content="Plato no encontrado")
    try:
        return productos.guardar_pedido_plato(restaurante_id, plato_id, peticion)
    except GrupoNoExisteError:
        return Response(status_code=400, content="Uno de los grupos de extras ya no existe")


@app.post("/admin/api/grupos-opciones", status_code=201, response_model=None)
def admin_crear_grupo(
    peticion: DatosGrupo, request: Request, restaurante_id: RestauranteActual
) -> GrupoOpciones | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return productos.crear_grupo(restaurante_id, peticion)


@app.put("/admin/api/grupos-opciones/{grupo_id}", response_model=None)
def admin_actualizar_grupo(
    grupo_id: str, peticion: DatosGrupo, request: Request, restaurante_id: RestauranteActual
) -> GrupoOpciones | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    grupo = productos.actualizar_grupo(restaurante_id, grupo_id, peticion)
    if grupo is None:
        return Response(status_code=404, content="Grupo no encontrado")
    return grupo


@app.delete("/admin/api/grupos-opciones/{grupo_id}")
def admin_eliminar_grupo(
    grupo_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not productos.eliminar_grupo(restaurante_id, grupo_id):
        return Response(status_code=404, content="Grupo no encontrado")
    return Response(status_code=204)


class AsignarGrupoPeticion(BaseModel):
    plato_ids: list[str] = Field(default_factory=list, max_length=1000)


@app.put("/admin/api/grupos-opciones/{grupo_id}/platos", response_model=None)
def admin_asignar_grupo(
    grupo_id: str,
    peticion: AsignarGrupoPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> ConfigProductos | Response:
    """Para no entrar plato a plato cuando el mismo grupo (ej. "Punto de la
    carne") va en muchos: se marca de una vez, desde el propio grupo."""
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    validos = {p.id for p in cargar_carta(restaurante_id)}
    if not set(peticion.plato_ids) <= validos:
        return Response(status_code=400, content="Alguno de esos platos no existe")
    try:
        asignar_grupo_a_platos(productos, restaurante_id, grupo_id, peticion.plato_ids)
    except GrupoNoExisteError:
        return Response(status_code=404, content="Grupo no encontrado")
    return config_productos(productos, restaurante_id)


# ------------------------------------------------ pedido en mesa (primer bloque)
#
# docs/PEDIDO-EN-MESA.md. Cookie propia (no la de gerente/superadmin): un
# comensal no es un usuario del panel, es quien esta sentado a una mesa.

COOKIE_COMENSAL = "sesion_comensal"


@app.get("/admin/api/mesas", response_model=None)
def admin_listar_mesas(
    request: Request, restaurante_id: RestauranteActual
) -> list[Mesa] | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return mesas_del_local(mesas, restaurante_id)


class NombrePlanoPeticion(BaseModel):
    """Nombre de una zona o de una mesa: libre ("Terraza", "Barril 1", "4")."""

    nombre: str = Field(min_length=1, max_length=60)

    @field_validator("nombre")
    @classmethod
    def _limpiar(cls, v: str) -> str:
        limpio = " ".join(v.split())
        if not limpio:
            raise ValueError("el nombre no puede estar vacio")
        return limpio


class OrdenZonasPeticion(BaseModel):
    ids: list[str] = Field(max_length=200)


class DisenoMesa(BaseModel):
    """Forma, tamano y posicion de una mesa en el plano (casillas de cuadricula)."""

    forma: FormaMesa
    x: float = Field(ge=0, le=200)
    y: float = Field(ge=0, le=200)
    ancho: float = Field(gt=0, le=20)
    alto: float = Field(gt=0, le=20)
    rotacion: int = Field(ge=0, lt=360)
    capacidad: int = Field(ge=1, le=30)


class CrearMesaPeticion(NombrePlanoPeticion):
    # Todo lo demas es opcional: sin diseno nace cuadrada, en el origen, en la
    # primera zona (asi sigue valiendo `{"nombre": "..."}` a secas).
    zona_id: str | None = Field(default=None, max_length=100)
    forma: FormaMesa | None = None
    x: float | None = Field(default=None, ge=0, le=200)
    y: float | None = Field(default=None, ge=0, le=200)
    ancho: float | None = Field(default=None, gt=0, le=20)
    alto: float | None = Field(default=None, gt=0, le=20)
    rotacion: int | None = Field(default=None, ge=0, lt=360)
    capacidad: int | None = Field(default=None, ge=1, le=30)


class ActualizarMesaPeticion(BaseModel):
    """Cambio parcial: solo se toca lo que venga en la peticion."""

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    zona_id: str | None = Field(default=None, max_length=100)
    forma: FormaMesa | None = None
    x: float | None = Field(default=None, ge=0, le=200)
    y: float | None = Field(default=None, ge=0, le=200)
    ancho: float | None = Field(default=None, gt=0, le=20)
    alto: float | None = Field(default=None, gt=0, le=20)
    rotacion: int | None = Field(default=None, ge=0, lt=360)
    capacidad: int | None = Field(default=None, ge=1, le=30)

    @field_validator("nombre")
    @classmethod
    def _limpiar(cls, v: str | None) -> str | None:
        if v is None:
            return None
        limpio = " ".join(v.split())
        if not limpio:
            raise ValueError("el nombre no puede estar vacio")
        return limpio


@app.get("/admin/api/zonas", response_model=None)
def admin_listar_zonas(
    request: Request, restaurante_id: RestauranteActual
) -> list[Zona] | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return mesas.listar_zonas(restaurante_id)


@app.post("/admin/api/zonas", status_code=201, response_model=None)
def admin_crear_zona(
    peticion: NombrePlanoPeticion, request: Request, restaurante_id: RestauranteActual
) -> Zona | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return mesas.crear_zona(restaurante_id, peticion.nombre)


# Ruta propia (no /zonas/orden) para no chocar con /zonas/{zona_id}.
@app.put("/admin/api/orden-zonas", response_model=None)
def admin_ordenar_zonas(
    peticion: OrdenZonasPeticion, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not mesas.ordenar_zonas(restaurante_id, peticion.ids):
        return Response(status_code=400, content="El orden debe incluir todas las zonas, una vez")
    return Response(status_code=204)


@app.put("/admin/api/zonas/{zona_id}", response_model=None)
def admin_renombrar_zona(
    zona_id: str,
    peticion: NombrePlanoPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Zona | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    zona = mesas.renombrar_zona(restaurante_id, zona_id, peticion.nombre)
    if zona is None:
        return Response(status_code=404, content="Zona no encontrada")
    return zona


@app.delete("/admin/api/zonas/{zona_id}", response_model=None)
def admin_eliminar_zona(
    zona_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = mesas.eliminar_zona(restaurante_id, zona_id)
    if resultado == "no_existe":
        return Response(status_code=404, content="Zona no encontrada")
    if resultado == "sesion_abierta":
        return Response(
            status_code=409,
            content="Hay una mesa de esta zona con clientes sentados: espera a que se cierre",
        )
    return Response(status_code=204)


@app.post("/admin/api/mesas", status_code=201, response_model=None)
def admin_crear_mesa(
    peticion: CrearMesaPeticion, request: Request, restaurante_id: RestauranteActual
) -> Mesa | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    diseno = peticion.model_dump(exclude={"nombre", "zona_id"}, exclude_none=True)
    try:
        return mesas.crear_mesa(restaurante_id, peticion.nombre, peticion.zona_id, **diseno)
    except ZonaNoExisteError:
        return Response(status_code=404, content="Zona no encontrada")


@app.put("/admin/api/mesas/{mesa_id}", response_model=None)
def admin_actualizar_mesa(
    mesa_id: str,
    peticion: ActualizarMesaPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Mesa | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    try:
        mesa = mesas.actualizar_mesa(
            restaurante_id, mesa_id, peticion.model_dump(exclude_none=True)
        )
    except ZonaNoExisteError:
        return Response(status_code=404, content="Zona no encontrada")
    if mesa is None:
        return Response(status_code=404, content="Mesa no encontrada")
    return mesa


@app.delete("/admin/api/mesas/{mesa_id}", response_model=None)
def admin_eliminar_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = mesas.eliminar_mesa(restaurante_id, mesa_id)
    if resultado == "no_existe":
        return Response(status_code=404, content="Mesa no encontrada")
    if resultado == "sesion_abierta":
        return Response(
            status_code=409,
            content="Hay clientes sentados en esta mesa: espera a que se cierre",
        )
    return Response(status_code=204)


@app.post("/admin/api/mesas/{mesa_id}/regenerar-qr", response_model=None)
def admin_regenerar_qr_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> Mesa | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    mesa = mesas.regenerar_token(restaurante_id, mesa_id)
    if mesa is None:
        return Response(status_code=404, content="Mesa no encontrada")
    return mesa


class EntrarMesaPeticion(BaseModel):
    token_qr: str = Field(min_length=1, max_length=200)
    nombre: str | None = Field(default=None, max_length=60)
    idioma: str = Field(default="es", pattern=r"^[a-z]{2}$")


class EntrarMesaRespuesta(BaseModel):
    sesion_id: str
    comensal_id: str
    rol: str
    estado: str


def _comensal_de_cookie(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_COMENSAL)
    return None if token is None else verificar_token_sesion(token)


@app.post("/api/mesa/entrar", response_model=None)
def api_mesa_entrar(
    peticion: EntrarMesaPeticion, request: Request
) -> EntrarMesaRespuesta | Response:
    try:
        resultado = entrar_por_qr(
            mesas,
            peticion.token_qr,
            peticion.nombre,
            peticion.idioma,
            comensal_actual=_comensal_de_cookie(request),
        )
    except ComensalExpulsadoError:
        return Response(status_code=403, content="El personal te ha quitado de esta mesa")
    if resultado is None:
        return Response(status_code=404, content="Mesa no encontrada")
    sesion, comensal = resultado

    respuesta = JSONResponse(
        EntrarMesaRespuesta(
            sesion_id=sesion.id, comensal_id=comensal.id, rol=comensal.rol, estado=sesion.estado
        ).model_dump()
    )
    respuesta.set_cookie(
        COOKIE_COMENSAL,
        crear_token_sesion(comensal.id),
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
    )
    return respuesta


@app.get("/api/mesa/yo", response_model=None)
def api_mesa_yo(request: Request, restaurante_id: RestauranteActual) -> MiSesion | Response:
    """Estado de la mesa de quien pregunta. 401 si ya no tiene mesa (se cerro,
    lo expulsaron o no entro nunca): la carta lo olvida y sigue como carta."""
    comensal_id = _comensal_de_cookie(request)
    datos = None if comensal_id is None else mi_sesion(mesas, restaurante_id, comensal_id)
    if datos is None:
        respuesta = Response(status_code=401, content="Sin mesa")
        respuesta.delete_cookie(COOKIE_COMENSAL)
        return respuesta
    return datos


@app.post("/api/mesa/pedir-cuenta", response_model=None)
def api_pedir_cuenta(request: Request, restaurante_id: RestauranteActual) -> Response:
    """Solo el anfitrion, y solo con la mesa ya abierta (docs/PEDIDO-EN-MESA.md,
    "Pedir la cuenta y cobrar")."""
    comensal_id = _comensal_de_cookie(request)
    if comensal_id is None:
        return _sin_mesa()
    sesion = pedir_cuenta(mesas, restaurante_id, comensal_id)
    if sesion is None:
        return Response(
            status_code=403,
            content="Solo el anfitrión puede pedir la cuenta, y solo si ya os aceptaron",
        )
    return Response(status_code=204)


# -- propuestas (bloque 2): lo que un comensal quiere, antes de que exista
# comanda. Requieren la cookie de comensal, igual que entrar/yo.


def _comensal_en_sesion(
    request: Request, restaurante_id: str
) -> tuple[Comensal, SesionMesa] | None:
    """El comensal de la cookie y su sesion, solo si sigue abierta y es de este
    restaurante. None en cualquier otro caso: la carta debe olvidar la mesa."""
    comensal_id = _comensal_de_cookie(request)
    if comensal_id is None:
        return None
    encontrado = mesas.comensal_con_sesion(comensal_id)
    if encontrado is None:
        return None
    comensal, sesion = encontrado
    if sesion.restaurante_id != restaurante_id or sesion.estado == "cerrada":
        return None
    if comensal.expulsado_en is not None:
        return None
    return comensal, sesion


def _sin_mesa() -> Response:
    respuesta = Response(status_code=401, content="Sin mesa")
    respuesta.delete_cookie(COOKIE_COMENSAL)
    return respuesta


class NuevaPropuestaPeticion(BaseModel):
    plato_id: str = Field(min_length=1, max_length=200)
    formato: str | None = Field(default=None, max_length=40)
    # Nombres de opciones elegidas, de cualquiera de los grupos del plato.
    opciones: list[str] = Field(default_factory=list, max_length=30)
    cantidad: int = Field(default=1, ge=1, le=20)
    nota: str | None = Field(default=None, max_length=200)


def _opciones_elegidas(
    grupos_del_plato: list[GrupoOpciones], nombres: list[str]
) -> list[OpcionElegida] | str:
    """Copia nombre y precio de cada opcion elegida. Devuelve un mensaje de
    error (str) si se pide una opcion que no existe o no se respeta el minimo
    o el maximo de algun grupo."""
    disponibles = {o.nombre: o for g in grupos_del_plato for o in g.opciones}
    for nombre in nombres:
        if nombre not in disponibles:
            return f'"{nombre}" no es una opcion de este plato'
    for grupo in grupos_del_plato:
        elegidas_del_grupo = [n for n in nombres if n in {o.nombre for o in grupo.opciones}]
        if len(elegidas_del_grupo) < grupo.minimo:
            return f'"{grupo.nombre}" necesita elegir al menos {grupo.minimo}'
        if len(elegidas_del_grupo) > grupo.maximo:
            return f'"{grupo.nombre}" admite como mucho {grupo.maximo}'
    return [OpcionElegida(nombre=n, precio=disponibles[n].precio) for n in nombres]


# Comun a quien proponga (el cliente desde la carta o el personal en nombre
# de la mesa, ver mas abajo): valida el plato, el formato y las opciones, y
# devuelve ya el precio que toca. Un Response es el error a devolver tal cual.
def _validar_pedido(
    restaurante_id: str, plato_id: str, formato: str | None, nombres_opciones: list[str]
) -> tuple[Plato, float, list[OpcionElegida]] | Response:
    plato = next(
        (p for p in cargar_carta(restaurante_id) if p.id == plato_id and p.disponible), None
    )
    if plato is None:
        return Response(status_code=404, content="Este plato ya no esta disponible")

    pedido = productos.listar_pedido_platos(restaurante_id).get(plato.id)
    precio_unitario: float | None = plato.precio
    if formato is not None:
        formato_elegido = next(
            (f for f in (pedido.formatos if pedido else []) if f.nombre == formato), None
        )
        if formato_elegido is None:
            return Response(status_code=400, content="Ese formato no existe para este plato")
        precio_unitario = formato_elegido.precio
    if precio_unitario is None:
        return Response(
            status_code=400, content="Este plato no tiene precio: hay que elegir un formato"
        )

    grupos_del_plato = grupos_de_plato(productos, restaurante_id, plato.id)
    opciones = _opciones_elegidas(grupos_del_plato, nombres_opciones)
    if isinstance(opciones, str):
        return Response(status_code=400, content=opciones)

    return plato, precio_unitario, opciones


@app.post("/api/mesa/propuestas", status_code=201, response_model=None)
def api_crear_propuesta(
    peticion: NuevaPropuestaPeticion, request: Request, restaurante_id: RestauranteActual
) -> Propuesta | Response:
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    comensal, sesion = encontrado

    validado = _validar_pedido(
        restaurante_id, peticion.plato_id, peticion.formato, peticion.opciones
    )
    if isinstance(validado, Response):
        return validado
    plato, precio_unitario, opciones = validado

    propuesta = proponer(
        propuestas,
        sesion.id,
        comensal.id,
        comensal.nombre,
        plato.id,
        plato.nombre,
        precio_unitario,
        peticion.formato,
        peticion.cantidad,
        opciones,
        peticion.nota,
    )
    mesas.actualizar_sesion(sesion.id, {"ultima_actividad": datetime.now(UTC)})
    return propuesta


@app.get("/api/mesa/propuestas", response_model=None)
def api_listar_propuestas(
    request: Request, restaurante_id: RestauranteActual
) -> list[Propuesta] | Response:
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    _, sesion = encontrado
    return propuestas.listar_de_sesion(sesion.id)


@app.delete("/api/mesa/propuestas/{propuesta_id}", response_model=None)
def api_quitar_propuesta(
    propuesta_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    comensal, _ = encontrado
    resultado = retirar(propuestas, propuesta_id, comensal.id, comensal.rol == "anfitrion")
    if resultado == "no_existe":
        return Response(status_code=404, content="Esa propuesta ya no esta pendiente")
    if resultado == "sin_permiso":
        return Response(status_code=403, content="Solo puedes quitar tus propias propuestas")
    return Response(status_code=204)


def _lineas_por_destino(
    restaurante_id: str, confirmadas: list[Propuesta]
) -> dict[Destino, list[LineaTicket]]:
    """De cada propuesta confirmada, la linea de ticket que le corresponde,
    agrupadas por a donde va (cocina o barra). El destino y el alcohol salen
    de "Para pedir" (productos.py), no de la propuesta: pueden haber cambiado
    desde que se propuso, y es la carta de hoy la que manda."""
    categoria_de = {p.id: p.categoria for p in cargar_carta(restaurante_id)}
    pedido_platos = productos.listar_pedido_platos(restaurante_id)
    destinos_categoria = productos.destinos_categoria(restaurante_id)

    resultado: dict[Destino, list[LineaTicket]] = {}
    for p in confirmadas:
        pedido = pedido_platos.get(p.plato_id)
        destino = destino_de(categoria_de.get(p.plato_id, ""), pedido, destinos_categoria)
        linea = LineaTicket(
            propuesta_id=p.id,
            nombre_plato=p.nombre_plato,
            formato=p.formato,
            precio_unitario=p.precio_unitario,
            cantidad=p.cantidad,
            opciones=[OpcionElegidaTicket(nombre=o.nombre, precio=o.precio) for o in p.opciones],
            nota=p.nota,
            alcohol=pedido.alcohol if pedido else False,
            pedido_por_nombre=p.comensal_nombre,
        )
        resultado.setdefault(destino, []).append(linea)
    return resultado


@app.post("/api/mesa/propuestas/confirmar", response_model=None)
def api_confirmar_propuestas(request: Request, restaurante_id: RestauranteActual) -> Response:
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    comensal, sesion = encontrado
    if comensal.rol != "anfitrion":
        return Response(status_code=403, content="Solo el anfitrion puede confirmar el pedido")
    n = _confirmar_y_generar_comanda(restaurante_id, sesion)
    return JSONResponse({"confirmadas": n})


# Comun al cliente (arriba) y al personal (mas abajo, "gestion de la comanda
# desde la mesa"): confirma lo pendiente y, si hay algo, arma la comanda y
# reparte los tickets por destino.
def _confirmar_y_generar_comanda(restaurante_id: str, sesion: SesionMesa) -> int:
    confirmadas = confirmar_pendientes(propuestas, sesion.id)
    if confirmadas:
        mesa = mesas.obtener_mesa(restaurante_id, sesion.mesa_id)
        mesa_nombre = mesa.nombre if mesa else sesion.mesa_id
        lineas = _lineas_por_destino(restaurante_id, confirmadas)
        crear_comanda(comandas, restaurante_id, sesion.id, mesa_nombre, lineas)
    return len(confirmadas)


# Aparte de la ruta para poder probarla llamandola directamente, sin abrir un
# stream HTTP de verdad (fragil de probar con TestClient: un generador que
# duerme entre yields puede dejar un hilo colgado del lado del test).
def _eventos_propuestas(comensal_id: str) -> Iterator[str]:
    """SSE (docs/PEDIDO-EN-MESA.md, seccion 10): sondea el estado cada 1,5 s y
    solo envia cuando cambia. Se corta a los 15 min; el navegador reconecta
    solo, asi no se queda un hilo ocupado toda la tarde en una mesa quieta."""
    anterior: str | None = None
    limite = time.monotonic() + 900
    while time.monotonic() < limite:
        encontrado = mesas.comensal_con_sesion(comensal_id)
        if encontrado is None or encontrado[1].estado == "cerrada":
            yield f"data: {json.dumps({'cerrada': True})}\n\n"
            return
        _, sesion = encontrado
        lista = [p.model_dump(mode="json") for p in propuestas.listar_de_sesion(sesion.id)]
        actual = json.dumps(lista, sort_keys=True, ensure_ascii=False)
        if actual != anterior:
            yield f"data: {actual}\n\n"
            anterior = actual
        else:
            yield ": \n\n"
        time.sleep(1.5)


@app.get("/api/mesa/propuestas/eventos", response_model=None)
def api_propuestas_eventos(
    request: Request, restaurante_id: RestauranteActual
) -> StreamingResponse | Response:
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    return StreamingResponse(_eventos_propuestas(encontrado[0].id), media_type="text/event-stream")


@app.get("/api/mesa/comandas", response_model=None)
def api_mesa_comandas(
    request: Request, restaurante_id: RestauranteActual
) -> list[ResumenComanda] | Response:
    """Lo que el cliente ve de su propio pedido, una vez confirmado (bloque 3):
    solo si va o no va, sin tickets ni destinos (eso es de cocina)."""
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    _, sesion = encontrado
    return resumen_comandas(comandas, sesion.id)


def _eventos_comandas(comensal_id: str) -> Iterator[str]:
    anterior: str | None = None
    limite = time.monotonic() + 900
    while time.monotonic() < limite:
        encontrado = mesas.comensal_con_sesion(comensal_id)
        if encontrado is None or encontrado[1].estado == "cerrada":
            yield f"data: {json.dumps([])}\n\n"
            return
        _, sesion = encontrado
        lista = [r.model_dump(mode="json") for r in resumen_comandas(comandas, sesion.id)]
        actual = json.dumps(lista, sort_keys=True, ensure_ascii=False)
        if actual != anterior:
            yield f"data: {actual}\n\n"
            anterior = actual
        else:
            yield ": \n\n"
        time.sleep(1.5)


@app.get("/api/mesa/comandas/eventos", response_model=None)
def api_comandas_eventos(
    request: Request, restaurante_id: RestauranteActual
) -> StreamingResponse | Response:
    encontrado = _comensal_en_sesion(request, restaurante_id)
    if encontrado is None:
        return _sin_mesa()
    return StreamingResponse(_eventos_comandas(encontrado[0].id), media_type="text/event-stream")


# -- el personal, desde el panel (hoy la cookie del gerente; con el bloque 3,
# tambien la del camarero)


class AbrirMesaPeticion(BaseModel):
    comensales: int | None = Field(default=None, ge=1, le=50)


class SesionConComensales(BaseModel):
    sesion: SesionMesa
    comensales: list[Comensal]


def _mesa_cambiada() -> Response:
    return Response(
        status_code=409, content="La mesa acaba de cambiar: vuelve a cargarla e inténtalo otra vez"
    )


@app.post("/admin/api/mesas/{mesa_id}/abrir", response_model=None)
def admin_abrir_mesa(
    mesa_id: str,
    request: Request,
    restaurante_id: RestauranteActual,
    peticion: AbrirMesaPeticion | None = None,
) -> SesionMesa | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    comensales = peticion.comensales if peticion is not None else None
    try:
        sesion = abrir_mesa(mesas, restaurante_id, mesa_id, comensales)
    except SesionCambiadaError:
        return _mesa_cambiada()
    if sesion is None:
        return Response(status_code=404, content="Mesa no encontrada")
    return sesion


@app.post("/admin/api/mesas/{mesa_id}/confirmar", response_model=None)
def admin_confirmar_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> SesionMesa | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    try:
        sesion = confirmar_mesa(mesas, restaurante_id, mesa_id)
    except SesionCambiadaError:
        return _mesa_cambiada()
    if sesion is None:
        return Response(status_code=404, content="Esta mesa no tiene clientes")
    return sesion


@app.post("/admin/api/mesas/{mesa_id}/liberar", response_model=None)
def admin_liberar_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not liberar_mesa(mesas, restaurante_id, mesa_id):
        return Response(status_code=404, content="Esta mesa ya estaba libre")
    return Response(status_code=204)


@app.post("/admin/api/mesas/{mesa_id}/cobrar", response_model=None)
def admin_cobrar_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    """Cierra la mesa con motivo "cobrada", para distinguirla de una liberada
    sin cobrar (docs/PEDIDO-EN-MESA.md, "Pedir la cuenta y cobrar")."""
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not cobrar_mesa(mesas, restaurante_id, mesa_id):
        return Response(status_code=404, content="Esta mesa ya estaba libre")
    return Response(status_code=204)


@app.get("/admin/api/mesas/{mesa_id}/sesion", response_model=None)
def admin_sesion_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> SesionConComensales | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = sesion_de_mesa(mesas, restaurante_id, mesa_id)
    if resultado is None:
        return Response(status_code=404, content="Esta mesa está libre")
    sesion, comensales = resultado
    return SesionConComensales(sesion=sesion, comensales=comensales)


@app.post("/admin/api/comensales/{comensal_id}/expulsar", response_model=None)
def admin_expulsar_comensal(
    comensal_id: str, request: Request, restaurante_id: RestauranteActual
) -> Comensal | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    comensal = expulsar_comensal(mesas, restaurante_id, comensal_id)
    if comensal is None:
        return Response(status_code=404, content="Comensal no encontrado")
    return comensal


# -------------------------------------------- gestion de la comanda desde la mesa
#
# Para cuando el camarero entra en una mesa ocupada (desde Servicio o Mesas):
# ve todo lo pedido, puede anadir algo el mismo (con un selector tipo TPV en
# el panel), ajustar el precio de una linea y confirmar. No hace falta que
# nadie haya escaneado el QR: "no todos lo usan desde el movil".


def _sesion_de_mesa_o_404(restaurante_id: str, mesa_id: str) -> tuple[SesionMesa, str] | Response:
    resultado = sesion_de_mesa(mesas, restaurante_id, mesa_id)
    if resultado is None:
        return Response(status_code=404, content="Esta mesa está libre")
    sesion, _ = resultado
    mesa = mesas.obtener_mesa(restaurante_id, mesa_id)
    return sesion, (mesa.nombre if mesa else mesa_id)


@app.get("/admin/api/mesas/{mesa_id}/comanda", response_model=None)
def admin_comanda_mesa(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> ComandaMesa | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = _sesion_de_mesa_o_404(restaurante_id, mesa_id)
    if isinstance(resultado, Response):
        return resultado
    sesion, _ = resultado
    return resumen_mesa(propuestas.listar_de_sesion(sesion.id))


class AnadirComoPersonalPeticion(BaseModel):
    plato_id: str = Field(min_length=1, max_length=200)
    formato: str | None = Field(default=None, max_length=40)
    opciones: list[str] = Field(default_factory=list, max_length=30)
    cantidad: int = Field(default=1, ge=1, le=20)
    nota: str | None = Field(default=None, max_length=200)


# Nombre fijo para lo que anade el personal: no hace falta que exista ya un
# comensal (el camarero puede montar la comanda entera sin que nadie haya
# escaneado el QR), y deja claro en el pedido quien lo puso.
NOMBRE_PERSONAL = "Camarero"


def _comensal_para_personal(sesion_id: str, ahora: datetime) -> Comensal:
    """El anfitrion si ya hay uno; si la mesa no tiene a nadie todavia (la
    abrio el personal y nadie ha escaneado), se crea un comensal para poder
    colgar las propuestas de ahi (hace falta uno por la clave foranea)."""
    presentes = [c for c in mesas.listar_comensales(sesion_id) if c.expulsado_en is None]
    anfitrion = next((c for c in presentes if c.rol == "anfitrion"), None)
    if anfitrion is not None:
        return anfitrion
    if presentes:
        return presentes[0]
    return mesas.anadir_comensal(sesion_id, NOMBRE_PERSONAL, "es", ahora)


@app.post("/admin/api/mesas/{mesa_id}/comanda", status_code=201, response_model=None)
def admin_anadir_a_comanda(
    mesa_id: str,
    peticion: AnadirComoPersonalPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Propuesta | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = _sesion_de_mesa_o_404(restaurante_id, mesa_id)
    if isinstance(resultado, Response):
        return resultado
    sesion, _ = resultado

    validado = _validar_pedido(
        restaurante_id, peticion.plato_id, peticion.formato, peticion.opciones
    )
    if isinstance(validado, Response):
        return validado
    plato, precio_unitario, opciones = validado

    ahora = datetime.now(UTC)
    comensal = _comensal_para_personal(sesion.id, ahora)
    propuesta = proponer(
        propuestas,
        sesion.id,
        comensal.id,
        NOMBRE_PERSONAL,
        plato.id,
        plato.nombre,
        precio_unitario,
        peticion.formato,
        peticion.cantidad,
        opciones,
        peticion.nota,
        ahora,
    )
    mesas.actualizar_sesion(sesion.id, {"ultima_actividad": ahora})
    return propuesta


@app.delete("/admin/api/mesas/{mesa_id}/comanda/{propuesta_id}", response_model=None)
def admin_quitar_de_comanda(
    mesa_id: str, propuesta_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = _sesion_de_mesa_o_404(restaurante_id, mesa_id)
    if isinstance(resultado, Response):
        return resultado
    sesion, _ = resultado
    propuesta = propuestas.obtener(propuesta_id)
    if propuesta is None or propuesta.sesion_id != sesion.id:
        return Response(status_code=404, content="Esa propuesta no es de esta mesa")
    # El personal puede quitar cualquier linea, la haya puesto quien la haya
    # puesto: por eso "quien_es_anfitrion=True" siempre aqui.
    resultado_retirar = retirar(propuestas, propuesta_id, "", True)
    if resultado_retirar == "no_existe":
        return Response(status_code=404, content="Esa propuesta ya no está pendiente")
    return Response(status_code=204)


class AjustarPrecioPeticion(BaseModel):
    precio_unitario: float = Field(ge=0, le=10_000)


@app.put("/admin/api/mesas/{mesa_id}/comanda/{propuesta_id}/precio", response_model=None)
def admin_ajustar_precio(
    mesa_id: str,
    propuesta_id: str,
    peticion: AjustarPrecioPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Propuesta | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = _sesion_de_mesa_o_404(restaurante_id, mesa_id)
    if isinstance(resultado, Response):
        return resultado
    sesion, _ = resultado
    propuesta = propuestas.obtener(propuesta_id)
    if propuesta is None or propuesta.sesion_id != sesion.id:
        return Response(status_code=404, content="Esa propuesta no es de esta mesa")
    actualizada = ajustar_precio(propuestas, propuesta_id, peticion.precio_unitario)
    if actualizada is None:  # pragma: no cover - ya se comprobo que existe
        return Response(status_code=404, content="Propuesta no encontrada")
    return actualizada


@app.post("/admin/api/mesas/{mesa_id}/comanda/confirmar", response_model=None)
def admin_confirmar_comanda(
    mesa_id: str, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    resultado = _sesion_de_mesa_o_404(restaurante_id, mesa_id)
    if isinstance(resultado, Response):
        return resultado
    sesion, _ = resultado
    n = _confirmar_y_generar_comanda(restaurante_id, sesion)
    return JSONResponse({"confirmadas": n})


# ------------------------------------------------------------ bloque 3: cocina y barra
#
# De momento en el propio /admin del gerente (decidido con el usuario el
# 2026-09-29): el rol de camarero, con su propio acceso, llega despues sin
# tener que rehacer esto.


class CambiarEstadoTicketPeticion(BaseModel):
    estado: Literal["en_preparacion", "servida"]


@app.get("/admin/api/tickets", response_model=None)
def admin_listar_tickets(
    request: Request, restaurante_id: RestauranteActual, destino: Destino | None = None
) -> list[Ticket] | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return comandas.listar_pendientes(restaurante_id, destino)


@app.post("/admin/api/tickets/{ticket_id}/estado", response_model=None)
def admin_cambiar_estado_ticket(
    ticket_id: str,
    peticion: CambiarEstadoTicketPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Ticket | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    ticket = comandas.actualizar_estado(
        restaurante_id, ticket_id, peticion.estado, datetime.now(UTC)
    )
    if ticket is None:
        return Response(status_code=404, content="Ticket no encontrado")
    return ticket


class AnularLineaPeticion(BaseModel):
    motivo: str = Field(min_length=1, max_length=200)


@app.post("/admin/api/tickets/{ticket_id}/lineas/{linea_id}/anular", response_model=None)
def admin_anular_linea(
    ticket_id: str,
    linea_id: str,
    peticion: AnularLineaPeticion,
    request: Request,
    restaurante_id: RestauranteActual,
) -> Ticket | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    ticket = anular_linea(comandas, restaurante_id, ticket_id, linea_id, peticion.motivo)
    if ticket is None:
        return Response(status_code=404, content="Esa línea no es de ese ticket")
    return ticket


# Aparte de la ruta, igual que _eventos_propuestas: para poder llamarla
# directamente en los tests sin abrir un stream HTTP de verdad. `destino` es
# para la pantalla de impresion (SeccionImpresion): cada una escucha solo lo
# suyo, cocina o barra, no las dos.
def _eventos_tickets(restaurante_id: str, destino: Destino | None = None) -> Iterator[str]:
    anterior: str | None = None
    limite = time.monotonic() + 900
    while time.monotonic() < limite:
        lista = [
            t.model_dump(mode="json") for t in comandas.listar_pendientes(restaurante_id, destino)
        ]
        actual = json.dumps(lista, sort_keys=True, ensure_ascii=False)
        if actual != anterior:
            yield f"data: {actual}\n\n"
            anterior = actual
        else:
            yield ": \n\n"
        time.sleep(1.5)


@app.get("/admin/api/tickets/eventos", response_model=None)
def admin_eventos_tickets(
    request: Request, restaurante_id: RestauranteActual, destino: Destino | None = None
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return StreamingResponse(
        _eventos_tickets(restaurante_id, destino), media_type="text/event-stream"
    )


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


# ------------------------------------------------------------ marca
#
# Nombre, logo y portada del restaurante. Las imagenes usan el mismo volumen y
# la misma ruta publica que las fotos de platos (/fotos/...), con un nombre de
# archivo fijo por tipo: subir otra reemplaza a la anterior.

_IMAGENES_MARCA: dict[str, tuple[CampoImagenMarca, str]] = {
    "logo": ("logo", "marca-logo"),
    "portada": ("foto_portada", "marca-portada"),
}
TipoImagenMarca = Literal["logo", "portada"]


class NombreRestaurantePeticion(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, nombre: str) -> str:
        limpio = " ".join(nombre.split())
        if not limpio:
            raise ValueError("El nombre no puede estar vacío")
        return limpio


@app.put("/admin/api/marca")
def admin_cambiar_nombre(
    peticion: NombreRestaurantePeticion, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not actualizar_nombre_restaurante(restaurante_id, peticion.nombre):
        return Response(status_code=404, content="Restaurante no encontrado")
    return Response(status_code=204)


@app.post("/admin/api/marca/{tipo}")
async def admin_subir_imagen_marca(
    tipo: TipoImagenMarca, request: Request, foto: UploadFile, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")

    contenido = await foto.read(TAMANO_MAX_FOTO + 1)
    if len(contenido) > TAMANO_MAX_FOTO:
        return Response(status_code=413, content="La imagen pesa demasiado")
    if not contenido.startswith(_CABECERA_JPEG):
        return Response(status_code=400, content="Solo se aceptan imagenes JPEG")

    campo, nombre_archivo = _IMAGENES_MARCA[tipo]
    ruta = _ruta_foto(restaurante_id, nombre_archivo)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)

    # ?v= evita que el navegador enseñe la imagen anterior al reemplazarla.
    url = f"/fotos/{restaurante_id}/{nombre_archivo}.jpg?v={int(time.time())}"
    if not actualizar_imagen_marca(restaurante_id, campo, url):
        ruta.unlink(missing_ok=True)
        return Response(status_code=404, content="Restaurante no encontrado")
    return Response(content=json.dumps({"url": url}), media_type="application/json")


@app.delete("/admin/api/marca/{tipo}")
def admin_quitar_imagen_marca(
    tipo: TipoImagenMarca, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    campo, nombre_archivo = _IMAGENES_MARCA[tipo]
    if not actualizar_imagen_marca(restaurante_id, campo, ""):
        return Response(status_code=404, content="Restaurante no encontrado")
    _ruta_foto(restaurante_id, nombre_archivo).unlink(missing_ok=True)
    return Response(status_code=204)


# ------------------------------------------------------------ codigo QR
#
# El QR se dibuja en el navegador (libreria de npm, sin tocar las dependencias
# de Python); aqui solo se decide a que direccion apunta y que texto lleva la
# hoja imprimible.

DOMINIO_BASE = os.getenv("DOMINIO_BASE", "jurux.app")
TEXTO_QR_POR_DEFECTO = "Escanea para ver la carta"


def _url_publica(restaurante_id: str) -> str:
    """La direccion de la carta: el id del restaurante es su subdominio, para
    todos por igual. El alias historico (cartia) solo sigue resolviendo, para
    que los QR ya impresos con esa direccion no dejen de funcionar."""
    return f"https://{restaurante_id}.{DOMINIO_BASE}"


def _datos_qr(restaurante_id: str) -> dict[str, str]:
    nombre = str(cargar_config(restaurante_id).get("nombre", restaurante_id))
    texto = obtener_texto_qr(restaurante_id).strip() or TEXTO_QR_POR_DEFECTO
    return {"url": _url_publica(restaurante_id), "nombre": nombre, "texto": texto}


class TextoQrPeticion(BaseModel):
    # Vacio = volver al texto por defecto.
    texto: str = Field(max_length=120)

    @field_validator("texto")
    @classmethod
    def limpiar_texto(cls, texto: str) -> str:
        return " ".join(texto.split())


@app.get("/admin/api/qr", response_model=None)
def admin_obtener_qr(
    request: Request, restaurante_id: RestauranteActual
) -> dict[str, str] | Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    return _datos_qr(restaurante_id)


@app.put("/admin/api/qr-texto")
def admin_guardar_texto_qr(
    peticion: TextoQrPeticion, request: Request, restaurante_id: RestauranteActual
) -> Response:
    if not _sesion_activa(request, restaurante_id):
        return Response(status_code=401, content="Sesión no válida")
    if not guardar_texto_qr(restaurante_id, peticion.texto):
        return Response(status_code=404, content="Restaurante no encontrado")
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


class MetricasConNombre(MetricasRestaurante):
    nombre: str


@app.get("/superadmin/api/metricas", response_model=None)
def superadmin_metricas(
    request: Request, dias: Annotated[int, Query(ge=1, le=90)] = 7
) -> list[MetricasConNombre] | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    try:
        por_restaurante = {m.restaurante_id: m for m in metricas.resumen(dias)}
        restaurantes = listar_restaurantes()
    except Exception as e:
        log.error("metricas_no_disponibles", motivo=str(e))
        return Response(status_code=503, content="Métricas no disponibles")
    # Todos los restaurantes, tengan o no actividad: un bar a cero tambien es
    # un dato.
    return [
        MetricasConNombre(
            **por_restaurante.get(r.id, MetricasRestaurante(restaurante_id=r.id)).model_dump(
                exclude={"coste_por_pregunta_usd"}
            ),
            nombre=r.nombre,
        )
        for r in restaurantes
    ]


@app.get("/superadmin/api/restaurantes/{restaurante_id}/qr", response_model=None)
def superadmin_obtener_qr(restaurante_id: str, request: Request) -> dict[str, str] | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    try:
        _validar_slug(restaurante_id, "restaurante_id")
    except ValueError:
        return Response(status_code=404, content="Restaurante no encontrado")
    if not _restaurante_existe(restaurante_id):
        return Response(status_code=404, content="Restaurante no encontrado")
    return _datos_qr(restaurante_id)


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


# Importador de carta desde una foto: herramienta de uso propio (dar de alta un
# restaurante o ampliarle una seccion sin teclear plato a plato), no algo que
# el gerente vea ni dispare. Solo lee y propone; nada se crea hasta que se
# confirma cada plato con los endpoints de abajo, igual que si los hubiera
# metido el gerente a mano.
@app.post("/superadmin/api/restaurantes/{restaurante_id}/leer-carta", response_model=None)
async def superadmin_leer_carta(
    restaurante_id: str, request: Request, foto: UploadFile
) -> list[PlatoLeido] | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    if not _restaurante_existe(restaurante_id):
        return Response(status_code=404, content="Restaurante no encontrado")
    if not control.hay_presupuesto(restaurante_id):
        return Response(status_code=429, content="Tope de gasto diario alcanzado")

    contenido = await foto.read(TAMANO_MAX_FOTO + 1)
    if len(contenido) > TAMANO_MAX_FOTO or not contenido.startswith(_CABECERA_JPEG):
        return Response(status_code=400, content="Sube una foto JPEG de menos de 3 MB")

    try:
        platos, consumo = leer_platos_de_foto(contenido)
    except Exception as e:
        log.error("importar_carta_fallido", restaurante_id=restaurante_id, motivo=str(e))
        return Response(status_code=502, content="No se pudo leer la carta de la foto")
    control.registrar(restaurante_id, MODELO_TRADUCCION, ConsumoTotal(consumos=[consumo]))
    return platos


@app.get("/superadmin/api/restaurantes/{restaurante_id}/categorias", response_model=None)
def superadmin_listar_categorias(
    restaurante_id: str, request: Request
) -> list[Categoria] | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    if not _restaurante_existe(restaurante_id):
        return Response(status_code=404, content="Restaurante no encontrado")
    return cargar_categorias(restaurante_id)


@app.post(
    "/superadmin/api/restaurantes/{restaurante_id}/categorias", status_code=201, response_model=None
)
def superadmin_crear_categoria(
    restaurante_id: str, peticion: NombreCategoriaPeticion, request: Request
) -> Categoria | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    if not _restaurante_existe(restaurante_id):
        return Response(status_code=404, content="Restaurante no encontrado")
    return crear_categoria(restaurante_id, peticion.nombre)


@app.post(
    "/superadmin/api/restaurantes/{restaurante_id}/platos", status_code=201, response_model=None
)
def superadmin_crear_plato(
    restaurante_id: str, peticion: CrearPlatoPeticion, request: Request, tareas: BackgroundTasks
) -> Plato | Response:
    if not _sesion_superadmin_activa(request):
        return Response(status_code=401, content="Sesión no válida")
    if not _restaurante_existe(restaurante_id):
        return Response(status_code=404, content="Restaurante no encontrado")
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
        alergenos_confirmados=peticion.alergenos_confirmados,
    )
    if creado is None:
        return Response(status_code=404, content="Categoría no encontrada")
    _indices.pop(restaurante_id, None)
    tareas.add_task(traducir_restaurante, restaurante_id, control)
    return creado
