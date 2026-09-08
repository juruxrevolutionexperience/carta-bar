import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from carta_bar.llm import MODELO, cliente

CORPUS = Path("corpus")


def responder(
    pregunta: str,
    modelo: SentenceTransformer,
    trozos: list[str],
    origenes: list[str],
    vectores: np.ndarray,
) -> str:
    resultados = buscar(pregunta, modelo, trozos, origenes, vectores, k=3)
    contexto = "\n\n---\n\n".join(f"[Fuente: {origen}]\n{trozo}" for _, origen, trozo in resultados)

    c = cliente()
    respuesta = c.messages.create(
        model=MODELO,
        max_tokens=400,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Responde la pregunta usando SOLO la información del contexto. "
                    f"Si no está en el contexto, di que no lo sabes.\n\n"
                    f"Contexto:\n{contexto}\n\nPregunta: {pregunta}"
                ),
            }
        ],
    )
    return texto_de_respuesta(respuesta)


def cargar_documentos() -> dict[str, str]:
    return {
        fichero.stem: fichero.read_text(encoding="utf-8") for fichero in sorted(CORPUS.glob("*.md"))
    }


def trocear(texto: str, tam: int = 800, solape: int = 100) -> list[str]:
    trozos = []
    inicio = 0
    while inicio < len(texto):
        trozos.append(texto[inicio : inicio + tam])
        inicio += tam - solape
    return trozos


def indexar(modelo: SentenceTransformer) -> tuple[list[str], list[str], np.ndarray]:
    documentos = cargar_documentos()
    trozos: list[str] = []
    origenes: list[str] = []

    for nombre, texto in documentos.items():
        for trozo in trocear_por_titulos(texto):
            trozos.append(trozo)
            origenes.append(nombre)

    vectores = modelo.encode(trozos, show_progress_bar=True)
    return trozos, origenes, vectores


def buscar(
    pregunta: str,
    modelo: SentenceTransformer,
    trozos: list[str],
    origenes: list[str],
    vectores: np.ndarray,
    k: int = 3,
) -> list[tuple[float, str, str]]:
    vector_pregunta = modelo.encode([pregunta])
    similitudes = modelo.similarity(vector_pregunta, vectores)[0]

    mejores = similitudes.argsort(descending=True)[:k]
    return [(float(similitudes[i]), origenes[i], trozos[i]) for i in mejores]


def trocear_por_titulos(texto: str, tam_max: int = 1500) -> list[str]:
    secciones = re.split(r"\n(?=#{1,3} )", texto)

    trozos: list[str] = []
    for seccion in secciones:
        seccion = seccion.strip()
        if not seccion:
            continue
        if len(seccion) <= tam_max:
            trozos.append(seccion)
        else:
            trozos.extend(trocear(seccion, tam=tam_max, solape=100))
    return trozos


def limpiar(texto: str) -> str:
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto


def indexar_limpio(modelo: SentenceTransformer) -> tuple[list[str], list[str], np.ndarray]:
    documentos = {
        fichero.stem: fichero.read_text(encoding="utf-8") for fichero in sorted(CORPUS.glob("*.md"))
    }
    trozos: list[str] = []
    origenes: list[str] = []

    for nombre, texto in documentos.items():
        for trozo in trocear_por_titulos(texto):
            trozos.append(limpiar(trozo))
            origenes.append(nombre)

    vectores = modelo.encode(trozos, show_progress_bar=True)
    return trozos, origenes, vectores


def texto_de_respuesta(respuesta: object) -> str:
    bloque = respuesta.content[0]  # type: ignore[attr-defined]
    if bloque.type != "text":
        return ""
    return str(bloque.text)
