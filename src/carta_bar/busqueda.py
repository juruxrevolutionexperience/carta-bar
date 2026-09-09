import numpy as np
from sentence_transformers import SentenceTransformer

from carta_bar.datos import cargar_carta
from carta_bar.modelos import Plato, RestriccionesCliente


def texto_de_plato(plato: Plato) -> str:
    ingredientes = ", ".join(plato.ingredientes)
    return (
        f"{plato.nombre}. Categoría: {plato.categoria}. "
        f"{plato.descripcion}. Ingredientes: {ingredientes}."
    )


def indexar(modelo: SentenceTransformer) -> tuple[list[Plato], np.ndarray]:
    carta = cargar_carta()
    textos = [texto_de_plato(p) for p in carta]
    vectores = modelo.encode(textos, show_progress_bar=True)
    return carta, vectores


def filtrar_por_restricciones(carta: list[Plato], pregunta: str) -> list[Plato]:
    texto = pregunta.lower()
    resultado = carta

    if "vegano" in texto:
        resultado = [p for p in resultado if p.vegano]
    if "vegetarian" in texto:
        resultado = [p for p in resultado if p.vegetariano]
    if "sin gluten" in texto or "celiac" in texto or "celíac" in texto:
        resultado = [p for p in resultado if p.sin_gluten]
    if "sin lactosa" in texto or "intoleran" in texto:
        resultado = [p for p in resultado if p.sin_lactosa]

    return resultado


def buscar_platos(
    pregunta: str,
    modelo: SentenceTransformer,
    carta: list[Plato],
    vectores: np.ndarray,
    k: int = 3,
) -> list[tuple[float, Plato]]:
    candidatos = filtrar_por_restricciones(carta, pregunta)

    if not candidatos:
        return []

    indices = [carta.index(p) for p in candidatos]
    vectores_filtrados = vectores[indices]

    vector_pregunta = modelo.encode([pregunta])
    similitudes = modelo.similarity(vector_pregunta, vectores_filtrados)[0]

    mejores = similitudes.argsort(descending=True)[: min(k, len(candidatos))]
    return [(float(similitudes[i]), candidatos[i]) for i in mejores]


def filtrar_por_restricciones_cliente(carta: list[Plato], r: RestriccionesCliente) -> list[Plato]:
    resultado = carta
    if r.vegano:
        resultado = [p for p in resultado if p.vegano]
    if r.vegetariano:
        resultado = [p for p in resultado if p.vegetariano]
    if r.sin_gluten:
        resultado = [p for p in resultado if p.sin_gluten]
    if r.sin_lactosa:
        resultado = [p for p in resultado if p.sin_lactosa]
    for alergeno in r.alergenos_excluir:
        resultado = [p for p in resultado if alergeno not in p.alergenos]
    for palabra in r.ingredientes_excluir:
        resultado = [
            p
            for p in resultado
            if not any(palabra.lower() in ing.lower() for ing in p.ingredientes)
        ]
    return resultado
