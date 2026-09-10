# Carta-Bar

Asistente de carta para restaurantes. El comensal escanea un QR, ve la carta en
su idioma y puede preguntarle a un chat qué puede comer según sus alergias,
dietas o lo que le apetezca. Pensado como **SaaS multi-restaurante**: un solo
software sirviendo a muchos locales a la vez.

Busca los platos por significado (embeddings), no por palabras clave, y filtra
las restricciones en Python **antes** de que el modelo redacte nada.

---

## Requisitos

| | Linux / macOS | Windows |
|---|---|---|
| Python 3.12 | sí | sí |
| [uv](https://docs.astral.sh/uv/) | sí | sí |
| `make` | ya viene | **no viene**; usa la columna de comandos `uv` |
| Docker | opcional (Postgres local) | opcional |

Docker es opcional: sin base de datos la app arranca igual y contabiliza el
gasto en memoria. Para persistirlo, lo más cómodo es Supabase, que no necesita
Docker — ver [docs/BASE-DE-DATOS.md](docs/BASE-DE-DATOS.md).

## Puesta en marcha

**Linux / macOS**

```bash
cp .env.example .env      # y rellena ANTHROPIC_API_KEY
make install
make check
uv run uvicorn carta_bar.api:app --reload
```

**Windows (PowerShell)**

```powershell
Copy-Item .env.example .env      # y rellena ANTHROPIC_API_KEY
uv sync
uv run ruff format . ; uv run ruff check . ; uv run mypy src tests ; uv run pytest
uv run uvicorn carta_bar.api:app --reload
```

Abre <http://localhost:8000>. No hace falta activar el entorno: `uv run` lo
hace por ti.

> El dictado por voz necesita **HTTPS o `localhost`**. En `127.0.0.1` algunos
> navegadores no dan acceso al micrófono; usa `localhost`.

## Comandos

| Qué hace | Linux / macOS | Windows / sin make |
|---|---|---|
| Instalar dependencias | `make install` | `uv sync` |
| Formatear | `make format` | `uv run ruff format .` |
| Linter + tipos | `make lint` | `uv run ruff check .` y `uv run mypy src tests` |
| Tests | `make test` | `uv run pytest` |
| Todo lo anterior | `make check` | los cuatro de arriba en orden |
| Tests rápidos | `make test-fast` | `uv run pytest -x -q` |
| Cobertura | `make test-cov` | `uv run pytest --cov=src --cov-report=term-missing` |
| Arrancar la app | — | `uv run uvicorn carta_bar.api:app --reload` |
| Traducir la carta | — | `uv run python -m carta_bar.traductor` |
| Postgres local | `make up` / `make down` | `docker compose up -d` / `down` |
| Consola psql | `make db` | `docker compose exec db psql -U agente -d agente_db` |
| Reiniciar la BD | `make reset` | `docker compose down -v` y `up -d` |

## Cómo se atiende una pregunta

```
POST /preguntar
  ├─ límite de peticiones por IP          (10/min, 60/h)
  ├─ ¿queda presupuesto hoy?              corta ANTES de gastar
  ├─ LLM 1 · intérprete                   restricciones + historial → JSON
  ├─ filtrado en Python                   determinista, no lo decide el modelo
  ├─ búsqueda por embeddings              los 10 platos más afines
  ├─ LLM 2 · redactor                     solo redacta sobre lo ya filtrado
  └─ se registra el gasto                 tokens y coste de las 2 llamadas
```

Que el **filtrado sea Python y no el modelo** es deliberado: una alergia no
puede depender de que el LLM interprete bien una frase.

## Módulos

| Fichero | Responsabilidad |
|---|---|
| `api.py` | Rutas HTTP, validación de entrada y arranque |
| `agente.py` | Orquesta la respuesta al comensal |
| `interprete.py` | Extrae restricciones estructuradas de la conversación |
| `busqueda.py` | Filtrado y búsqueda semántica |
| `embeddings.py` | Carga del modelo de vectores |
| `datos.py` | Carga de cartas y categorías (valida las rutas) |
| `modelos.py` | Modelos Pydantic del dominio |
| `llm.py` | Cliente de Anthropic y modelo en uso |
| `costes.py` | Tarifa y medición de cada llamada |
| `uso.py` | Persistencia del uso (Postgres o memoria) |
| `presupuesto.py` | Corte automático por gasto |
| `limites.py` | Límites de peticiones |
| `seguridad.py` | Cabeceras HTTP y CSP |
| `traductor.py` | Traducción de la carta (herramienta de línea de comandos) |
| `logging_config.py` | Logging estructurado |
| `rag.py` | Legado de la versión anterior, solo se usa un ayudante |

## Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Obligatoria.** Clave del modelo |
| `POSTGRES_*` | vacías | Sin ellas, el gasto se contabiliza en memoria |
| `TOPE_DIARIO_USD` | `5.0` | Corte de gasto diario por restaurante |
| `CONFIAR_PROXY` | `false` | A `true` **solo** detrás de nginx o Cloudflare |
| `LOGS_JSON` | `false` | A `true` en producción |

> `CONFIAR_PROXY` a `true` sin un proxy delante permite falsificar
> `X-Forwarded-For` y saltarse el límite de peticiones. A `false` detrás de un
> proxy, todos los clientes comparten un solo cupo. Es una decisión de
> despliegue, no un automatismo.

## Seguridad

- **Travesía de rutas**: `restaurante_id` e idioma se validan contra
  `^[a-z0-9-]+$` donde se construyen las rutas.
- **XSS**: todo dato del restaurante se escapa antes de tocar `innerHTML`;
  las URL de imagen pasan por lista blanca de esquemas.
- **CSP con nonce** por petición, sin `'unsafe-inline'` en `script-src`.
- **SQL**: consultas parametrizadas, nunca concatenación.
- **Inyección de prompt**: el modelo **no tiene herramientas ni acceso a la
  base de datos**; solo redacta sobre platos ya filtrados. Esto es lo que acota
  el daño y **no debe romperse**.
- **Coste**: límite por IP, tope de longitud de entrada y corte por gasto.

## Costes

Unos **0,004 $ por pregunta** (dos llamadas a Claude Haiku 4.5). Un restaurante
con 1.500 preguntas al mes ronda los **6 $**. El coste real de cada pregunta se
lee de `response.usage` y queda en el log y en la tabla `uso_llm`.

## Documentación

- [docs/PENDIENTE.md](docs/PENDIENTE.md) — qué falta, por orden de urgencia
- [docs/BASE-DE-DATOS.md](docs/BASE-DE-DATOS.md) — conectar Supabase paso a paso

## Decisiones

- **uv** como gestor de paquetes y entornos.
- **mypy strict** desde el primer día: en un proyecto vacío no cuesta nada, y
  con el proyecto crecido sería inviable.
- **Pydantic** valida en ejecución. Mypy comprueba el código antes de correr,
  pero no puede saber qué llega de fuera; Pydantic cubre esa frontera.
- **`.env` fuera de Git** porque lleva las credenciales. `.env.example`
  documenta qué variables hacen falta sin revelar sus valores.
- **Postgres y no MySQL**: pgvector para los embeddings y RLS para aislar unos
  restaurantes de otros en el motor, no solo en el código.
- **Si la base de datos se cae, la app sigue sirviendo.** Una carta muerta por
  un fallo de métricas es peor que un sobregasto acotado, y el límite por IP
  sigue puesto.
- **La voz se resuelve en el navegador**: no pasa por el backend, no consume
  tokens y no añade coste.
