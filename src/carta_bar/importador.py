"""Lee los platos de una foto de una carta en papel, para no tener que
teclearlos uno a uno. Herramienta de uso propio (superadmin) al dar de alta un
restaurante o al ampliarle una seccion: el gerente no la ve ni la paga, ese
gasto lo decide quien la usa. Solo lee y propone; no crea nada por su cuenta,
eso lo hace quien la usa revisando la tabla antes de confirmar.
"""

import base64

from pydantic import BaseModel

from carta_bar.costes import Consumo, medir
from carta_bar.llm import MODELO_TRADUCCION, cliente


class PlatoLeido(BaseModel):
    nombre: str
    descripcion: str
    ingredientes: list[str]
    precio: float | None


class CartaLeida(BaseModel):
    platos: list[PlatoLeido]


_PROMPT = (
    "Esta es una foto de una carta o cartel de un bar/restaurante español. "
    "Transcribe cada plato o bebida que veas, uno por uno.\n\n"
    "Reglas:\n"
    "- Un elemento por cada nombre distinto, tal cual está escrito: no lo "
    "traduzcas, no lo corrijas ni lo normalices.\n"
    "- descripcion: la composición o los ingredientes tal como aparecen en la "
    "carta, en una frase natural en español. Si no hay descripción visible, "
    "déjala vacía, no la inventes.\n"
    "- ingredientes: esos mismos ingredientes descompuestos en una lista de "
    "palabras sueltas en minúsculas, para poder buscarlos después.\n"
    "- precio: el número en euros si se distingue con seguridad en la foto, o "
    "null si no aparece o está borroso.\n"
    "- No inventes ningún plato que no esté en la foto. No dejes ninguno fuera."
)


def leer_platos_de_foto(imagen_jpeg: bytes) -> tuple[list[PlatoLeido], Consumo]:
    respuesta = cliente().messages.parse(
        model=MODELO_TRADUCCION,
        max_tokens=4096,
        # Transcribir no necesita razonar; sin esto Sonnet 5 piensa por
        # defecto y ese pensamiento se paga como salida.
        thinking={"type": "disabled"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.standard_b64encode(imagen_jpeg).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }
        ],
        output_format=CartaLeida,
    )
    if respuesta.parsed_output is None:
        raise ValueError("No se pudo leer la carta de la foto")
    consumo = medir("importar_carta", respuesta.usage, MODELO_TRADUCCION)
    return respuesta.parsed_output.platos, consumo
