FROM python:3.12-slim

# uv resuelve e instala desde uv.lock, asi la imagen usa las mismas versiones
# exactas que en desarrollo.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/modelos

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev

# El modelo de embeddings se descarga aqui, al construir la imagen, y no en
# cada arranque: sin esto el contenedor tarda y depende de Hugging Face para
# poder levantar.
RUN uv run python -c "from carta_bar.embeddings import cargar_modelo; cargar_modelo()"

COPY datos ./datos
COPY web ./web
COPY sql ./sql

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "carta_bar.api:app", "--host", "0.0.0.0", "--port", "8000"]
