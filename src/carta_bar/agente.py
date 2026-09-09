import numpy as np
from sentence_transformers import SentenceTransformer

from carta_bar.busqueda import buscar_platos, filtrar_por_restricciones_cliente
from carta_bar.datos import cargar_categorias
from carta_bar.interprete import extraer_restricciones
from carta_bar.llm import MODELO, cliente
from carta_bar.modelos import Plato
from carta_bar.rag import texto_de_respuesta


def responder_cliente(
    pregunta: str,
    modelo: SentenceTransformer,
    carta: list[Plato],
    vectores: np.ndarray,
    restaurante_id: str,
) -> str:
    categorias = cargar_categorias(restaurante_id)
    nombres_categorias = [c.id for c in categorias]
    restricciones = extraer_restricciones(pregunta, nombres_categorias)
    candidatos = filtrar_por_restricciones_cliente(carta, restricciones)

    if not candidatos:
        return "No tenemos ningún plato que cumpla esas condiciones ahora mismo."

    indices = [carta.index(p) for p in candidatos]
    vectores_filtrados = vectores[indices]

    texto_busqueda = restricciones.intencion_busqueda or pregunta
    k = min(len(candidatos), 10)
    resultados = buscar_platos(texto_busqueda, modelo, candidatos, vectores_filtrados, k=k)

    contexto = "\n\n".join(
        f"{p.nombre} ({p.precio}€): {p.descripcion}. "
        f"Ingredientes: {', '.join(p.ingredientes)}. "
        f"Alérgenos: {', '.join(a.value for a in p.alergenos) or 'ninguno'}."
        for _, p in resultados
    )

    c = cliente()
    respuesta = c.messages.create(
        model=MODELO,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    "Eres el asistente de un restaurante. Responde la pregunta del cliente "
                    "usando SOLO los platos de este contexto. Muestra TODAS las opciones "
                    "relevantes del contexto que encajen, no solo una — el cliente decide, "
                    "tú le das el abanico. Sé breve y cercano en la descripción de cada una.\n\n"
                    f"Platos disponibles:\n{contexto}\n\nPregunta: {pregunta}"
                ),
            }
        ],
    )
    return texto_de_respuesta(respuesta)
