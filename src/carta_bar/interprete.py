from carta_bar.llm import MODELO, cliente
from carta_bar.modelos import RestriccionesCliente


def extraer_restricciones(pregunta: str) -> RestriccionesCliente:
    c = cliente()
    respuesta = c.messages.parse(
        model=MODELO,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extrae las restricciones alimentarias mencionadas en esta pregunta. "
                    "Si no se menciona ninguna, deja todo en sus valores por defecto.\n\n"
                    f"Pregunta: {pregunta}"
                ),
            }
        ],
        output_format=RestriccionesCliente,
    )
    return respuesta.parsed_output
