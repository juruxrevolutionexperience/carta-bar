# Pantallas ya migradas a React, compiladas antes de que empiece la imagen
# de Python: capa aparte, no la reconstruye cambiar codigo de carta_bar.
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

# uv instala desde uv.lock: las mismas versiones exactas que en desarrollo.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/modelos

# Capas de lo que menos cambia a lo que más: tocar código no reinstala PyTorch.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Solo embeddings.py: esta capa se rehace únicamente si cambia el modelo.
COPY src/carta_bar/embeddings.py /tmp/embeddings.py
RUN uv run --no-sync python -c "import runpy; runpy.run_path('/tmp/embeddings.py')['cargar_modelo']()"

COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# El modelo ya va en la imagen; sin esto el arranque consulta a Hugging Face.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY datos ./datos
COPY sql ./sql
# Scripts de mantenimiento que se lanzan con `docker exec` (p. ej. establecer_clave_admin.py).
COPY scripts ./scripts
COPY --from=frontend /frontend/dist ./web/dist

EXPOSE 8000

# El entorno se sincronizó al construir; sin --no-sync uv lo recompila al arrancar.
CMD ["uv", "run", "--no-sync", "uvicorn", "carta_bar.api:app", "--host", "0.0.0.0", "--port", "8000"]
