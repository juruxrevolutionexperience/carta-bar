"""Cabeceras de seguridad HTTP: la segunda barrera bajo el escapado.

El escapado del frontend es la primera defensa contra XSS. Esta es la segunda:
aunque se colara una etiqueta <script>, el navegador se niega a ejecutarla si
no lleva el nonce que solo genera el servidor, y que cambia en cada peticion.
"""

import secrets
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# La pagina carga tipografias de Google y nada mas; todo lo demas es propio.
_ORIGEN_FUENTES_CSS = "https://fonts.googleapis.com"
_ORIGEN_FUENTES = "https://fonts.gstatic.com"


def politica_csp(nonce: str) -> str:
    return "; ".join(
        [
            "default-src 'self'",
            # Sin 'unsafe-inline': un script inyectado no lleva nonce y no corre.
            f"script-src 'self' 'nonce-{nonce}'",
            # Los estilos si necesitan 'unsafe-inline': la carta pinta atributos
            # style= al construir las tarjetas de plato. Es un vector mucho mas
            # debil que el de scripts y todo va escapado igualmente.
            f"style-src 'self' 'unsafe-inline' {_ORIGEN_FUENTES_CSS}",
            f"font-src {_ORIGEN_FUENTES}",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            # Impide que otra web embeba la carta para robar clics.
            "frame-ancestors 'none'",
        ]
    )


class CabecerasSeguridad(BaseHTTPMiddleware):
    """Genera un nonce por peticion y sella la respuesta."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.nonce = secrets.token_urlsafe(16)
        respuesta = await call_next(request)

        respuesta.headers["Content-Security-Policy"] = politica_csp(request.state.nonce)
        # Evita que el navegador adivine el tipo de contenido y ejecute como
        # script algo que se sirvio como texto.
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["X-Frame-Options"] = "DENY"
        respuesta.headers["Referrer-Policy"] = "same-origin"
        # El microfono hace falta para el dictado; camara y ubicacion, no.
        respuesta.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
        # Solo surte efecto sobre HTTPS; sobre HTTP el navegador la ignora.
        respuesta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Nada de esta app debe quedarse guardado en el movil del comensal: el
        # HTML lleva un nonce distinto en cada peticion (uno guardado dejaria de
        # cuadrar con la politica) y la carta puede cambiar de precio o de plato
        # en cualquier momento. Sin esta cabecera el navegador decide por su
        # cuenta, y Safari en iPhone guarda durante bastante tiempo.
        respuesta.headers["Cache-Control"] = "no-store"
        return respuesta
