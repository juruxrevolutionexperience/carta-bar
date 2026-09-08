# NOTAS

Cheatsheet. Una línea por cosa. Si esto crece a más de una pantalla, lo recorto.

## 1. Arranque de un proyecto nuevo

```
uv init --package nombre-proyecto
cd nombre-proyecto
uv python pin 3.12
uv add pydantic structlog
uv add --dev ruff mypy pytest pytest-cov
cp .env.example .env      # y relleno las variables
uv sync
make up
make check
```

## 2. Chuleta de comandos

**uv**
- `uv add <paquete>` — dependencia de producción
- `uv add --dev <paquete>` — dependencia solo de desarrollo (linters, tests)
- `uv run <comando>` — ejecuta dentro del venv sin activarlo
- `uv sync` — instala/actualiza el entorno según el lock
- `uv python pin 3.12` — fija la versión de Python del proyecto

**docker compose**
- `docker compose up -d` — levanta en segundo plano
- `docker compose down` — para y elimina contenedores
- `docker compose down -v` — igual, y borra también el volumen (datos fuera)
- `docker compose logs -f db` — sigue los logs del servicio db
- `docker compose exec db psql -U agente -d agente_db` — consola psql dentro del contenedor

**Makefile**
- `make install` — `uv sync`
- `make check` — format + lint + test, el que corro antes de dar nada por hecho
- `make up` / `make down` — levanta/para Postgres
- `make db` — psql directo
- `make test-cov` — tests con líneas sin cubrir
- `make test-fast` — pytest -x -q, para iterar rápido
- `make reset` — down -v + up, base de datos limpia de un tirón

## 3. Errores que ya me han pasado

- La consola de Python no ve cambios en un módulo → salgo y vuelvo a entrar (recarga en caliente no existe)
- Docker no aparece en WSL → `wsl --shutdown` desde PowerShell (no desde dentro de WSL) y reabrir
- Makefile: el nombre del target no lleva indentación, pero los comandos debajo sí van con tabulador, nunca espacios
- Comparar floats con `==` falla por redondeo → usar `math.isclose`
- Un fichero de 0 bytes casi siempre es que no guardé (o el editor no ha volcado a disco todavía)

# editar pyproject.toml: [tool.ruff], [tool.ruff.lint], [tool.mypy]
- La nota: el error de los floats lo has redactado perfecto, y ese es el que más te va a servir en el módulo 3 comparando similitudes coseno.

## Exp 1 — k=3 → k=10
| Métrica | Base | k=10 |
|---|---|---|
| Recall chunk | 40% | 50% |

Conclusión: subir k apenas ayuda. El problema no es de ordenación,
es que la respuesta no está en ningún chunk. Descartado: coste x3 por +10%.

## Exp 2 — chunking fijo → por títulos (tam_max 1500)
| Métrica | Fijo | Títulos |
|---|---|---|
| Recall chunk | 40% | **60%** |
| Recall doc | 100% | 90% |
| MRR | 0.850 | 0.850 |

Conclusión: +20 puntos en la métrica que importa. Adoptado.
El descenso en Recall doc revela que esa métrica es demasiado rígida
(q004 acierta el chunk desde otro documento).

## Exp 3 (corregido) — limpieza aislada del re-chunking
Mismas fronteras (194 chunks en ambos), solo cambia el contenido limpio/sucio.

| | doc | chunk |
|---|---|---|
| Sin limpiar | 9/10 | 6/10 |
| Limpio | 9/10 | 5/10 |

Conclusión: la limpieza no mejora, posiblemente empeora ligeramente.
Con n=10 esta diferencia (1 pregunta) es ruido estadístico, no concluyente.
Decisión: NO adoptar limpieza. Mantener chunking por títulos (Exp 2) como base.