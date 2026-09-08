import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODELO = "claude-haiku-4-5-20251001"


def cliente() -> anthropic.Anthropic:
    clave = os.environ["ANTHROPIC_API_KEY"]
    return anthropic.Anthropic(api_key=clave)
