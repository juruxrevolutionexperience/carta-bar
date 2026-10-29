# Base de datos — puesta en marcha

Estado: **el código está listo y probado; solo hay que conectarlo a un Postgres real.**

Lo que ya funciona sin base de datos: la app arranca, avisa por log de que no
hay persistencia y contabiliza el gasto en memoria. Se pierde al reiniciar.

Lo que aporta conectarla: que ese gasto se guarde de verdad, que el corte por
presupuesto sobreviva a un reinicio, y poder consultar cuánto gasta cada
restaurante.

---

## Por qué Postgres y no MySQL

| | Postgres | MySQL + phpMyAdmin |
|---|---|---|
| pgvector (embeddings) | Nativo | No hay equivalente maduro |
| RLS (aislar restaurantes) | En el motor, por fila | No existe |
| Migración desde lo que hay | Cero | Reescribir todo |

Las dos primeras son decisivas: el corazón de la app son embeddings, y RLS es
lo que impide que el restaurante A vea datos del B **aunque haya un fallo en el
código Python**.

Cualquier Postgres gestionado sirve. En local vale el contenedor de
`docker-compose.yml` y en producción un proveedor gestionado, con el mismo SQL.
Estas instrucciones usan Supabase como ejemplo porque tiene plan gratuito y no
pide tarjeta.

phpMyAdmin, de paso, no es una base de datos: es un panel de administración de
MySQL. Y un panel así expuesto a internet es un blanco clásico de bots.

---

## Paso 1 — Crear el proyecto

1. Entra en <https://supabase.com> y pulsa **Start your project**.
2. Crea una organización y luego un proyecto.
3. Elige una región cercana a tus usuarios. Para clientes europeos, una región
   europea: menos latencia y los datos no salen de la UE.
4. Te pedirá una **contraseña de base de datos**. Guárdala en un gestor de
   contraseñas: **no se puede recuperar después**, solo restablecer.
5. Espera 1-2 minutos a que el proyecto termine de aprovisionarse.

## Paso 2 — Copiar las credenciales

En el panel: **Project Settings → Database → Connection string → URI**.

Tendrá esta forma:

```
postgresql://USUARIO:CONTRASEÑA@HOST:PUERTO/BASE_DE_DATOS
```

De ahí salen los cinco valores. Ponlos en tu `.env` (el fichero que **no** se
sube a git):

```
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=
POSTGRES_PORT=5432
```

> La contraseña va en tu `.env` y ahí se queda: no se manda por chat, ni por
> correo, ni se pega en un issue. Para que alguien te ayude a verificar la
> conexión basta con el host y el mensaje de error.

## Paso 3 — Arrancar

```bash
uv run uvicorn carta_bar.api:app --reload
```

No hay que ejecutar ningún SQL a mano: al arrancar, `crear_repositorio()`
detecta las credenciales y aplica `sql/esquema.sql` solo (es idempotente).

**Cómo saber si ha funcionado.** En los logs del arranque:

- `uso_persistente destino=<host>:<puerto>/<base>` → conectado
- `uso_sin_persistencia motivo=...` → algo falla; el motivo lo dice la línea

## Paso 4 — Comprobar que se está guardando

Haz una pregunta en el chat y luego, en el editor SQL del proveedor:

```sql
-- Las últimas llamadas registradas
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
| `password authentication failed` | Contraseña mal copiada; restablécela en el panel |
| `could not translate host name` | Host mal escrito o incompleto |
| `connection timed out` | Cortafuegos o VPN bloqueando el puerto de Postgres |
| Arranca bien pero `uso_llm` vacía | ¿Se ha hecho alguna pregunta en el chat? |

---

## Lo que viene después

Conectar la base de datos es solo el principio. Por orden:

1. **Mover los JSON a tablas.** Los ficheros de cada restaurante (`platos`,
   `categorias`, `traducciones`, `config`) pasan a tablas.
2. ✅ **RLS.** Activada en las 10 tablas, sin políticas: la clave pública del
   proveedor no puede leer ni escribir nada. La app sigue funcionando porque
   entra con un rol que se salta RLS (`rolbypassrls = true`, comprobado; la web
   se probó tras activarla). Las sentencias están al final de
   `sql/esquema.sql`: toda tabla nueva añade ahí su
   `ENABLE ROW LEVEL SECURITY`.
3. **Resolución del restaurante por subdominio.** Regla que no se salta nunca:
   **jamás fiarse de un `restaurante_id` que venga en el cuerpo de la
   petición**.
4. **Embeddings a pgvector**, calculados al guardar un plato. Hoy se calculan
   al arrancar la app (`indexar()` en `api.py`), lo cual con cientos de
   restaurantes es inviable.
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
  Para que corte en su lugar, basta cambiar un `return True` en
  `presupuesto.py`.
