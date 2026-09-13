"""Límites de peticiones: la primera defensa del presupuesto de LLM.

Cada pregunta de un cliente son DOS llamadas al modelo (intérprete + respuesta),
así que una petición sin control no cuesta latencia: cuesta dinero.
"""

import os

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Un comensal real no pasa de unas pocas preguntas por minuto; un bot, sí.
LIMITE_PREGUNTAR = "10/minute;60/hour"

# El resto de rutas (carta, categorías, config) no llaman al LLM, pero leen
# disco en cada petición: sin tope siguen siendo un blanco fácil.
LIMITE_GENERAL = "120/minute"

# Detrás de nginx, request.client.host es la IP del proxy y TODOS los clientes
# compartirían el mismo cupo. Pero fiarse de X-Forwarded-For sin un proxy delante
# permite falsificar la cabecera y saltarse el límite entero. Por eso es una
# decisión explícita de despliegue, no un automatismo. Supone un único proxy: con
# otro delante (Cloudflare con la nube naranja) la IP útil ya no es la última.
CONFIAR_PROXY = os.getenv("CONFIAR_PROXY", "false").lower() == "true"


def ip_cliente(request: Request) -> str:
    """Identifica al cliente para contarle sus peticiones."""
    if CONFIAR_PROXY:
        reenviada = request.headers.get("x-forwarded-for")
        if reenviada:
            # El último valor lo añade nginx; los anteriores los manda el cliente.
            return reenviada.split(",")[-1].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=ip_cliente, default_limits=[LIMITE_GENERAL])


# El handler que trae slowapi devuelve texto plano y una firma que mypy strict
# rechaza. Este devuelve la misma forma que /preguntar ({"respuesta": ...}), así
# que el chat pinta el aviso como un mensaje más en lugar de romperse.
AVISO_LIMITE = (
    "Vas un poco rápido y no me da tiempo a pensar. Espera unos segundos y vuelve a preguntarme."
)


def limite_superado(request: Request, exc: Exception) -> Response:
    """Respuesta 429 amable, en el formato que espera el frontend."""
    respuesta = JSONResponse(status_code=429, content={"respuesta": AVISO_LIMITE})
    if isinstance(exc, RateLimitExceeded) and exc.limit is not None:
        respuesta.headers["Retry-After"] = str(exc.limit.limit.get_expiry())
    return respuesta
