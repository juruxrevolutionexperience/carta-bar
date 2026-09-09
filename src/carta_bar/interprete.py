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
                    "Si no se menciona ninguna, deja todo en sus valores por defecto. "
                    "Además, en 'intencion_busqueda' escribe SOLO la parte de la pregunta "
                    "que expresa qué tipo de plato busca (sabor, tipo de comida, ocasión), "
                    "sin mencionar las restricciones. Si no hay ninguna intención de "
                    "búsqueda concreta, deja ese campo vacío. "
                    "Si el cliente pide explícitamente una categoría de la carta "
                    "(por ejemplo entrantes, principales, postres, panes, tostas), "
                    "escribe su identificador exacto en minúsculas en 'categoria_pedida'. "
                    "Si no pide ninguna categoría concreta, deja ese campo vacío.\n\n"
                    f"Pregunta: {pregunta}"
                ),
            }
        ],
        output_format=RestriccionesCliente,
    )
    if respuesta.parsed_output is None:
        raise ValueError("El modelo no devolvió una respuesta estructurada válida")
    return respuesta.parsed_output

    if respuesta.parsed_output is None:
        raise ValueError("El modelo no devolvió una respuesta estructurada válida")
    return respuesta.parsed_output
