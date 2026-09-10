"""Corte automatico por gasto: el limite por IP no para un ataque distribuido.

El limitador de peticiones protege de UNA fuente abusiva. Este modulo protege
del gasto agregado, venga de donde venga, y es lo que impide que una noche mala
se convierta en una factura mala.
"""

import os
import time

import structlog

from carta_bar.costes import ConsumoTotal
from carta_bar.uso import RepositorioUso

log = structlog.get_logger()

# A ~0,004 $ la pregunta, 5 $/dia son unas 1.300 preguntas: de sobra para un
# restaurante real, y un tope claro si algo se desmadra.
TOPE_DIARIO_USD = float(os.getenv("TOPE_DIARIO_USD", "5.0"))

# Bajo ataque, avisar en cada peticion bloqueada llenaria el disco de logs:
# un DoS pobre, pero real. Con el corte activo basta un aviso por minuto.
INTERVALO_AVISO = 60.0

AVISO_SIN_PRESUPUESTO = {
    "es": "Ahora mismo no puedo atenderte. Pregunta al personal, que te ayudará encantado.",
    "en": "I can't help you right now. Please ask our staff, they'll be glad to assist.",
    "de": "Ich kann dir gerade nicht helfen. Frag bitte unser Personal.",
    "fr": "Je ne peux pas t'aider pour le moment. Demande au personnel, il t'aidera.",
}


class ControlGasto:
    """Decide si se puede seguir gastando y anota lo que se gasta."""

    def __init__(self, repositorio: RepositorioUso, tope_diario: float = TOPE_DIARIO_USD) -> None:
        self.repositorio = repositorio
        self.tope_diario = tope_diario
        self._ultimo_aviso: dict[str, float] = {}

    def _toca_avisar(self, clave: str) -> bool:
        """Deja pasar un aviso por minuto y clave; silencia la avalancha."""
        ahora = time.monotonic()
        if ahora - self._ultimo_aviso.get(clave, 0.0) < INTERVALO_AVISO:
            return False
        self._ultimo_aviso[clave] = ahora
        return True

    def hay_presupuesto(self, restaurante_id: str) -> bool:
        """Se consulta ANTES de llamar al LLM; si no, no ahorraria nada."""
        try:
            gastado = self.repositorio.gasto_del_dia(restaurante_id)
        except Exception as e:
            # Decision deliberada: si la contabilidad falla, se sigue sirviendo.
            # Dejar la carta de un restaurante muerta por un fallo de la base de
            # datos es peor que un sobregasto acotado, y el limite por IP sigue
            # puesto. El log queda en ERROR para que no pase desapercibido.
            if self._toca_avisar(f"error:{restaurante_id}"):
                log.error(
                    "presupuesto_no_verificable", restaurante_id=restaurante_id, motivo=str(e)
                )
            return True

        if gastado >= self.tope_diario:
            if self._toca_avisar(f"agotado:{restaurante_id}"):
                log.warning(
                    "presupuesto_agotado",
                    restaurante_id=restaurante_id,
                    gastado_usd=round(gastado, 4),
                    tope_usd=self.tope_diario,
                )
            return False
        return True

    def registrar(self, restaurante_id: str, modelo: str, consumo: ConsumoTotal) -> None:
        try:
            self.repositorio.registrar(restaurante_id, modelo, consumo)
        except Exception as e:
            # Perder una anotacion no debe tumbar una respuesta ya pagada.
            log.error("uso_no_registrado", restaurante_id=restaurante_id, motivo=str(e))
