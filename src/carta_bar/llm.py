import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODELO = "claude-haiku-4-5-20251001"

# Traducir se hace una sola vez por plato (al crearlo o editarlo), no cada vez que
# alguien pregunta: aqui un modelo mejor cuesta centimos y evita errores como
# llamar "lenguado" a la lubina. Cambiable por variable de entorno.
MODELO_TRADUCCION = os.getenv("MODELO_TRADUCCION", "claude-sonnet-5")


def cliente() -> anthropic.Anthropic:
    clave = os.environ["ANTHROPIC_API_KEY"]
    return anthropic.Anthropic(api_key=clave)
