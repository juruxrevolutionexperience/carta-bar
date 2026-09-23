# Arquitectura · Carta Bar

Cómo está montado hoy, qué es sólido y qué está cogido con pinzas.

## Mapa

```
  CLIENTE (móvil)
       │  escanea QR → https://la-catedral.jurux.app
       ▼
 ┌──────────────── SERVIDOR HETZNER ────────────────────┐
 │  nginx  (HTTPS, un subdominio por restaurante)       │
 │     │                                                │
 │     ▼  127.0.0.1:8001                                │
 │  Contenedor Docker "carta-bar" (uno para todos)      │
 │    ├─ web/dist/*          React (Vite): carta, panel │
 │    ├─ API FastAPI         /carta, /preguntar...      │
 │    ├─ resuelve restaurante por el Host de la peticion│
 │    └─ modelo embeddings   entiende "algo sin gluten" │
 │                                                      │
 │  Al lado: cuentas (:3000) y gym-app (:8080)          │
 └──────────┬───────────────────────────┬───────────────┘
            ▼                           ▼
   Supabase (Postgres)           Anthropic (Claude)
   carta, gasto y métricas       contesta el chat y traduce
```

## Producción

| | |
|---|---|
| URL | https://la-catedral.jurux.app (`cartia.jurux.app` sigue resolviendo a La CatedRal por los QR ya impresos) |
| Superadmin | `/superadmin` en cualquier subdominio que exista (p. ej. https://la-catedral.jurux.app/superadmin): alta de restaurantes, QR de cada uno, métricas e importador de carta desde una foto (`importador.py`, visión con Sonnet 5; herramienta de uso propio, el gerente no la ve). Clave en `SUPERADMIN_CLAVE_HASH` del `.env` |
| Servidor | Hetzner CPX22 `Jurux-Revolution`, 178.104.233.131 |
| Acceso | `ssh xele@178.104.233.131`. Root no entra por SSH con contraseña (`PermitRootLogin prohibit-password`, valor por defecto) |
| Código | `/home/xele/cartaBar` |
| Contenedor | `carta-bar`, solo en loopback `127.0.0.1:8001` |
| nginx | `/etc/nginx/sites-available/carta`; certbot renueva el certificado solo |
| DNS | Cloudflare, un registro A por restaurante (`cartia`, `demo`...) → 178.104.233.131, **solo DNS** (nube gris). Con la nube naranja, la IP que ve nginx sería la de Cloudflare y el límite de peticiones dejaría de distinguir comensales |
| Base de datos | Supabase por el *Session pooler*: la conexión directa es solo IPv6 |
| Variables | `/home/xele/cartaBar/.env` en el servidor, fuera de git. Ver `.env.example`; las últimas añadidas: `DOMINIO_BASE` (para el QR) y `MODELO_TRADUCCION` |
| Copias de seguridad | Cron diario 04:50 → `/home/xele/copias-carta` (base de datos de Supabase + fotos, 14 días). Detalle y restauración en [COPIAS-DE-SEGURIDAD.md](COPIAS-DE-SEGURIDAD.md). Aún dentro del mismo disco |
| Seguridad del host | ufw (22, 80, 443) y fail2ban. La IP de casa está en `ignoreip` de `/etc/fail2ban/jail.local` |

## Cómo se despliega (desde el 2026-09-19)

`/home/xele/cartaBar` es un clon de git de verdad, no una copia por `rsync`.
Autenticado con una **deploy key de solo lectura** propia del servidor
(`~/.ssh/github_carta_bar` en el propio servidor, añadida en GitHub →
Settings → Deploy keys del repo, sin permiso de escritura). Nadie con acceso
al servidor puede empujar cambios a GitHub con esa clave, solo traerlos.

Desplegar es, en el servidor, con sesión SSH propia del usuario `xele`
(no hay acceso SSH externo al servidor fuera de eso):

```bash
cd /home/xele/cartaBar
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

- **`.env` y `datos/fotos/` nunca se tocan**: están en `.gitignore`, así que
  `git pull` no los borra ni los pisa.
- **~10 s de caída** al final, mientras el contenedor carga el modelo. No desplegar
  en hora punta.
- Si solo cambia el código, el build tarda segundos (capas en caché). Si cambian
  `pyproject.toml`, `uv.lock` o el modelo de `embeddings.py`, vuelve a tardar ~8 min.
- El `Dockerfile` tiene una etapa Node aparte (`frontend/`, compilado con Vite)
  antes de la imagen de Python: si solo cambia el código de `carta_bar`, esa
  etapa se reutiliza en caché y no se recompila.

**Historial:** hasta esta fecha se desplegaba con `rsync` desde el portátil de
quien tocara el código. Al montar el `git clone`, salió que `docker compose`
fija el nombre del contenedor (`container_name: carta-bar`) — si hay uno
corriendo con ese nombre desde otra carpeta, el nuevo choca al arrancar; hay
que pararlo primero desde donde esté corriendo. Salió también un `Dockerfile`
roto: copiaba una carpeta `web/` que ya no existe desde la migración a React
(`rsync` la arrastraba sin querer porque nunca borra lo que sobra; un `git
clone` limpio no tiene ni la carpeta, y el build fallaba a la primera).

## Qué está sólido

- Modelo de datos con Pydantic, validado al cargar la carta.
- Filtro de alérgenos y dietas determinista: la IA nunca decide si un plato es apto.
- Seguridad: CSP con nonce por petición, escapado en el frontend, límite de peticiones
  por cliente, tope de gasto diario, cabeceras de seguridad. Los logs ya muestran bots
  probando rutas (`../../etc/passwd`, credenciales de AWS) y reciben 404.
- Más de 300 tests y `ruff` (los 5 de búsqueda/embeddings necesitan el modelo real).
- Docker + nginx + HTTPS con el mismo patrón que el resto de apps del servidor.

## Qué está cogido con pinzas

| # | Problema | Consecuencia | Se arregla en |
|---|---|---|---|
| 1 | La carta vive en JSON dentro de la imagen | Cambiar un precio exige reconstruir y redesplegar. Sin esto no hay panel posible | ✅ |
| 2 | Se despliega copiando desde el portátil | El servidor no sabe qué versión corre; otro despliegue puede pisarlo | Fase 1 |
| 3 | `la-catedral` escrito en el código | Un segundo restaurante no cabe sin tocar código | ✅ |
| 4 | Las fotos no tienen almacenamiento | Hoy solo admite enlaces externos o `data:` | ✅ |
| 5 | `.env` editado a mano en el servidor | Nada lo versiona ni lo comprueba | Con el punto 2 |
| 6 | El arranque consultaba Hugging Face | Resuelto con `HF_HUB_OFFLINE=1`: 0 avisos en los logs | ✅ |
| 7 | Caída en cada despliegue mientras arranca | ~10 s medidos: el QR da error ese rato | Fase 3 |
| 8 | El Dockerfile copiaba el código antes que las dependencias | Resuelto: el build pasa de 470 s a 4 s | ✅ |

El 1 y el 3 se resolvieron juntos: la carta pasa de ficheros a Postgres
(tablas `restaurantes`, `categorias`, `platos`, `traducciones_platos`),
migrada y verificada — un `UPDATE` en Supabase cambia un precio sin
redesplegar. `RESTAURANTE_ID` en `.env` sustituye el literal en código.
Interruptor `CARTA_BD_ACTIVA`: si Postgres falla, se cae a los ficheros
JSON solos, igual que ya hacía `uso_llm`. Activado y confirmado en
producción.

El 4 (almacenamiento de fotos) se resolvió con el panel de gestión:
las fotos se comprimen en el propio navegador (sin Pillow en el
servidor) y se guardan en `datos/fotos/<restaurante_id>/<plato_id>.jpg`,
con un volumen persistente en `docker-compose.prod.yml` para que
sobrevivan a `docker compose up -d --build`.

**Multi-tenant real, adelantado a la Fase 4:** el mismo contenedor
sirve ya varios restaurantes a la vez. `_resolver_restaurante()` en
`api.py` decide qué restaurante atiende cada petición según el
subdominio del `Host` (`cartia.jurux.app` → `la-catedral`,
`demo.jurux.app` → `demo`), en vez de la antigua variable
`RESTAURANTE_ID` fija por servidor (que se mantiene solo como
respaldo para desarrollo local). Un nuevo restaurante no exige
desplegar nada aparte — solo un registro DNS, ampliar el certificado
de nginx, y sembrar sus filas en Supabase (todavía a mano; el alta
automática es la pieza que falta). El aislamiento (datos y sesiones
de un restaurante nunca se cruzan con otro) está cubierto por
`tests/test_multitenant.py` y probado contra producción con un
restaurante de prueba (`demo`).

## Cómo responde el chat y cómo se traduce la carta

Decisiones tomadas el 2026-09-21, con sus porqués (el detalle de cada una está
en `docs/PENDIENTE.md`):

1. **El intérprete (Haiku 4.5)** convierte la pregunta en restricciones
   estructuradas (alergia, dieta, categoría). **El filtrado lo hace Python, no el
   modelo**: solo pasan al modelo de respuesta los platos que cumplen.
2. **Un plato sin alérgenos confirmados nunca es "apto"** (`alergenos_confirmados`).
   Ante una alergia o dieta solo se usan platos confirmados; si no queda ninguno,
   respuesta fija "consulta al personal"; a un plato sin confirmar se le presenta
   como "SIN CONFIRMAR", nunca como "sin alérgenos". La carta pública muestra
   "consultar alérgenos" en vez de sus alérgenos. El aviso "hay platos pendientes"
   se añade **después** de la respuesta del modelo: metido en su prompt, el modelo
   se negaba a recomendar nada.
3. **Se pasan hasta 15 platos** al modelo (`MAX_PLATOS_EN_CONTEXTO`) y la
   respuesta tiene techo de 900 tokens; si se corta, se quita la última línea
   incompleta.
4. **Traducciones:** se hacen una vez por plato, al crearlo o editarlo, en segundo
   plano (`traducir_restaurante`), con **Sonnet 5** (`MODELO_TRADUCCION`) porque
   Haiku cometía errores serios (cava → champagne, ternera → vacuno, palabras
   inventadas). El hash solo mira el texto en español, así que cambiar de modelo o
   de instrucciones exige `python -m carta_bar.traductor --forzar`.
5. **El nombre del plato no se traduce nunca**: lo decide el restaurante (el
   cliente lo pide al camarero por su nombre). Solo se traducen descripción e
   ingredientes. Está forzado al leer (`datos._con_traducciones`,
   `agente._en_el_idioma`) y al traducir, no solo en el prompt.
6. **El chat usa las traducciones guardadas** (las mismas que ve el cliente en la
   carta) y no traduce por su cuenta; si una está desfasada (hash distinto) o no se
   puede leer, usa el español.
7. **Coste:** cada llamada se anota con la tarifa de su modelo
   (`PRECIOS_POR_MODELO`); un modelo desconocido se cobra a la más cara. El tope
   diario de 5 USD cubre chat y traducciones.

## Los tests nunca tocan la base real

`llm.py` carga el `.env` al importarse, y en un PC con las credenciales de
Supabase eso conectaba la suite a producción: los tests de mesas crearon mesas
y sesiones de verdad en la base real. Ahora `tests/conftest.py` vacía las
variables `POSTGRES_*` y pone `CARTA_BD_ACTIVA=false` **antes** de importar
nada de `carta_bar` (`load_dotenv` no pisa lo que ya está puesto), y
`tests/test_aislada.py` comprueba que los repositorios de la suite son en
memoria. Al arrancar el servidor local para probar a mano, hacer lo mismo:
`POSTGRES_USER= POSTGRES_PASSWORD= POSTGRES_DB= POSTGRES_HOST= CARTA_BD_ACTIVA=false uvicorn ...`

## Cómo probar la interfaz (sin desplegar)

Dos niveles, los dos contra un servidor local **aislado de producción** (con
las variables `POSTGRES_*` vacías y `CARTA_BD_ACTIVA=false`, ver arriba):

1. **Comportamiento**, con un DOM simulado (jsdom) sobre el paquete real de
   Vite: añadir mesas, arrastrarlas, el tirador de tamaño, los límites del
   plano, zonas, candado. No pinta nada, pero comprueba que la pantalla hace
   lo que dice y que no salta ningún error de React.
2. **Aspecto**, con Chromium de verdad (Playwright) haciendo capturas en móvil
   y en escritorio. En este PC faltaban tres librerías del sistema
   (`libnspr4`, `libnss3`, `libasound2`); se bajan con `apt-get download` y se
   extraen con `dpkg-deb -x` a una carpeta propia, sin tocar el sistema, y se
   apuntan con `LD_LIBRARY_PATH`.

Un cambio de interfaz no se da por bueno sin mirar una captura: el primer
diseño del plano compilaba, pasaba los tests y aun así dejaba los nombres de
las mesas en "T…".
