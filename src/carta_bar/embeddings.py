from sentence_transformers import SentenceTransformer

MODELO = "paraphrase-multilingual-MiniLM-L12-v2"


def cargar_modelo(nombre: str = MODELO) -> SentenceTransformer:
    return SentenceTransformer(nombre)


def similitud(texto_a: str, texto_b: str, modelo: SentenceTransformer) -> float:
    vectores = modelo.encode([texto_a, texto_b])
    return float(modelo.similarity(vectores[0], vectores[1])[0][0])
