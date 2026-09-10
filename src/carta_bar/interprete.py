from carta_bar.costes import Consumo, medir
from carta_bar.llm import MODELO, cliente
from carta_bar.modelos import MensajeChat, RestriccionesCliente


def _conversacion(historial: list[MensajeChat]) -> str:
    """Rinde la conversación previa para que el extractor no la pierda."""
    if not historial:
        return ""
    turnos = "\n".join(
        f"{'Cliente' if m.rol == 'cliente' else 'Asistente'}: {m.texto}" for m in historial
    )
    return f"Conversación hasta ahora:\n{turnos}\n\n"


def extraer_restricciones(
    pregunta: str,
    categorias_disponibles: list[str],
    historial: list[MensajeChat] | None = None,
) -> tuple[RestriccionesCliente, Consumo]:
    c = cliente()
    lista_categorias = ", ".join(categorias_disponibles)
    conversacion = _conversacion(historial or [])
    respuesta = c.messages.parse(
        model=MODELO,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extrae las restricciones alimentarias de la conversación. "
                    "IMPORTANTE: una restricción dicha en un mensaje anterior SIGUE "
                    "VIGENTE aunque no se repita en el último (si dijo que su hijo es "
                    "alérgico a los frutos secos, lo sigue siendo después). "
                    "Trata también los gustos como restricción: 'no le gustan las "
                    "verduras' es un ingrediente a excluir, no solo una alergia. "
                    "Si no se menciona ninguna, deja todo en sus valores por defecto. "
                    "Pon 'pedido_cerrado' a true SOLO si el cliente indica que ya ha "
                    "decidido o que no quiere nada más ('con esto voy servido', "
                    "'ya lo tengo claro', 'con eso me vale', 'nada más'). "
                    "Además, en 'intencion_busqueda' escribe SOLO la parte de la pregunta "
                    "que expresa qué tipo de plato busca (sabor, tipo de comida, ocasión), "
                    "sin mencionar las restricciones. Si no hay ninguna intención de "
                    "búsqueda concreta, deja ese campo vacío. "
                    "Si el cliente pide explícitamente una categoría de la carta, "
                    f"elige su identificador EXACTO de esta lista: {lista_categorias}. "
                    "Si no pide ninguna categoría concreta o no coincide con ninguna "
                    "de la lista, deja ese campo vacío.\n\n"
                    f"{conversacion}Ultimo mensaje del cliente: {pregunta}"
                ),
            }
        ],
        output_format=RestriccionesCliente,
    )
    if respuesta.parsed_output is None:
        raise ValueError("El modelo no devolvió una respuesta estructurada válida")
    return respuesta.parsed_output, medir("interprete", respuesta.usage)
