# Base de datos — lo que tienes que hacer tú

Estado: **el código está listo y probado; falta conectarlo a un Postgres real.**

Lo que ya funciona sin base de datos: la app arranca, avisa por log de que no
hay persistencia y contabiliza el gasto en memoria. Se pierde al reiniciar.

Lo que falta: que ese gasto se guarde de verdad, que el corte por presupuesto
sobreviva a un reinicio, y poder consultar cuánto gasta cada restaurante.

---

## Por qué Supabase y no otra cosa

| | Postgres / Supabase | MySQL + phpMyAdmin |
|---|---|---|
| pgvector (embeddings) | Nativo | No hay equivalente maduro |
| RLS (aislar restaurantes) | En el motor, por fila | No existe |
| Migración desde lo que hay | Cero | Reescribir todo |

Las dos primeras son decisivas: el corazón de la app son embeddings, y RLS es
lo que impide que el restaurante A vea datos del B **aunque haya un fallo en el
código Python**. Supabase es Postgres gestionado, así que en local vale el
contenedor de `docker-compose.yml` y en producción Supabase, con el mismo SQL.

phpMyAdmin no es una base de datos: es un panel de administración de MySQL. Y
un panel así expuesto a internet es un blanco clásico de bots.

---

## Paso 1 — Crear el proyecto (5 minutos, gratis, sin tarjeta)

1. Entra en <https://supabase.com> y pulsa **Start your project**.
2. Crea una organización y luego un proyecto.
3. Elige región **europea** (Frankfurt o Londres): los datos de tus clientes
   son europeos y la latencia desde España es mucho menor.
4. Te pedirá una **contraseña de base de datos**. Apúntala en tu gestor de
   contraseñas: **no se puede recuperar después**, solo restablecer.
5. Espera 1-2 minutos a que el proyecto termine de aprovisionarse.

## Paso 2 — Copiar las credenciales

En el panel: **Project Settings → Database → Connection string → URI**.

Verás algo así:

```
postgresql://postgres:[TU-PASSWORD]@db.abcdefghijkl.supabase.co:5432/postgres
```

De ahí salen los cinco valores. Ponlos en tu `.env` (el fichero que NO se sube
a git):

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=la-que-elegiste-en-el-paso-1
POSTGRES_DB=postgres
POSTGRES_HOST=db.abcdefghijkl.supabase.co
POSTGRES_PORT=5432
```

> **La contraseña no se la mandes a nadie, tampoco por chat.** Va en tu `.env`
> y ahí se queda. Para verificar la conexión basta con el host.

## Paso 3 — Arrancar

```
uv run uvicorn carta_bar.api:app --reload
```

No hay que ejecutar ningún SQL a mano: al arrancar, `crear_repositorio()`
detecta las credenciales y aplica `sql/esquema.sql` solo (es idempotente).

**Cómo saber si ha funcionado.** En los logs del arranque:

- `uso_persistente destino=db.xxxx.supabase.co:5432/postgres` → conectado
- `uso_sin_persistencia motivo=...` → algo falla; el motivo lo dice la línea

## Paso 4 — Comprobar que se está guardando

Haz una pregunta en el chat y luego, en Supabase, **SQL Editor**:

```sql
-- Las ultimas llamadas registradas
SELECT llamada, tokens_entrada, tokens_salida, coste_usd, creado_en
FROM uso_llm ORDER BY creado_en DESC LIMIT 10;

-- Gasto de hoy por restaurante
SELECT restaurante_id, ROUND(SUM(coste_usd), 4) AS usd, COUNT(*) AS llamadas
FROM uso_llm
WHERE creado_en >= date_trunc('day', now())
GROUP BY restaurante_id;

-- Coste medio por pregunta (cada pregunta son 2 llamadas)
SELECT ROUND(SUM(coste_usd) / (COUNT(*) / 2.0), 5) AS usd_por_pregunta
FROM uso_llm;
```

Cada pregunta del chat debe generar **dos filas**: `interprete` y `respuesta`.

---

## Errores probables

| Síntoma | Causa y arreglo |
|---|---|
| `uso_sin_persistencia`, faltan credenciales | Alguna variable `POSTGRES_*` vacía en `.env` |
| `password authentication failed` | Contraseña mal copiada; restablécela en Supabase |
| `could not translate host name` | Host mal escrito, o falta `db.` delante |
| `connection timed out` | Cortafuegos o VPN bloqueando el puerto 5432 |
| Arranca bien pero `uso_llm` vacía | ¿Has hecho alguna pregunta en el chat? |

---

## Después de esto: el paso 4 de verdad

Conectar la base de datos es solo el principio. Lo que viene, por orden:

1. **Mover los JSON a tablas.** Hoy `datos/<restaurante>/` son ficheros:
   `platos`, `categorias`, `traducciones` y `config` pasan a tablas.
2. **RLS.** Está escrita como nota en `sql/esquema.sql` pero **sin activar**:
   activarla ahora, sin políticas definidas, bloquearía todos los accesos.
   Va junto con los roles.
3. **Resolución del restaurante por subdominio** (`lacatedral.tuapp.com`).
   Regla que no se salta nunca: **jamás fiarse de un `restaurante_id` que
   venga en el cuerpo de la petición**.
4. **Embeddings a pgvector**, calculados al guardar un plato. Hoy se calculan
   al arrancar la app (`indexar()` en `api.py`), lo cual con 200 restaurantes
   es inviable.
5. **Sesiones de chat en el servidor.** Hoy el historial lo custodia el
   navegador: un cliente podría fabricar turnos falsos del asistente.

## Lo que el código ya trae hecho

- `sql/esquema.sql` — tabla `uso_llm`, con `NUMERIC` para el dinero (nunca
  `DOUBLE`: el redondeo binario descuadra al sumar miles de fracciones de
  céntimo) e índice por `(restaurante_id, creado_en)`.
- `uso.py` — repositorio tras un `Protocol`, con implementación Postgres
  (con pool de conexiones) y en memoria.
- `presupuesto.py` — corte por tope diario **antes** de llamar al LLM.
- Si la base de datos se cae, la app **sigue sirviendo** y lo registra como
  ERROR. Es una decisión deliberada: dejar la carta muerta por un fallo de
  métricas es peor que un sobregasto acotado, y el límite por IP sigue puesto.
  Si prefieres que corte, es cambiar un `return True` en `presupuesto.py`.
