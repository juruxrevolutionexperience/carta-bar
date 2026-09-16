# Arquitectura · Carta Bar

Cómo está montado hoy, qué es sólido y qué está cogido con pinzas.

## Mapa

```
  CLIENTE (móvil)
       │  escanea QR → https://cartia.jurux.app
       ▼
 ┌──────────────── SERVIDOR HETZNER ────────────────────┐
 │  nginx  (HTTPS con certificado de Let's Encrypt)     │
 │     │                                                │
 │     ▼  127.0.0.1:8001                                │
 │  Contenedor Docker "carta-bar"                       │
 │    ├─ web/index.html     la página que ve el cliente │
 │    ├─ API FastAPI        /carta, /preguntar...       │
 │    ├─ datos/*.json       LA CARTA, dentro de la imagen│
 │    └─ modelo embeddings  entiende "algo sin gluten"  │
 │                                                      │
 │  Al lado: cuentas (:3000) y gym-app (:8080)          │
 └──────────┬───────────────────────────┬───────────────┘
            ▼                           ▼
   Supabase (Postgres)           Anthropic (Claude)
   hoy solo guarda el gasto      contesta el chat
```

## Producción

| | |
|---|---|
| URL | https://cartia.jurux.app |
| Servidor | Hetzner CPX22 `Jurux-Revolution`, 178.104.233.131 |
| Acceso | `ssh xele@178.104.233.131`. Root no entra por SSH con contraseña (`PermitRootLogin prohibit-password`, valor por defecto) |
| Código | `/home/xele/cartaBar` |
| Contenedor | `carta-bar`, solo en loopback `127.0.0.1:8001` |
| nginx | `/etc/nginx/sites-available/carta`; certbot renueva el certificado solo |
| DNS | Cloudflare, registro A `cartia` → 178.104.233.131, **solo DNS** (nube gris). Con la nube naranja, la IP que ve nginx sería la de Cloudflare y el límite de peticiones dejaría de distinguir comensales |
| Base de datos | Supabase por el *Session pooler*: la conexión directa es solo IPv6 |
| Variables | `/home/xele/cartaBar/.env` en el servidor, fuera de git |
| Seguridad del host | ufw (22, 80, 443) y fail2ban. La IP de casa está en `ignoreip` de `/etc/fail2ban/jail.local` |

## Cómo se despliega hoy (provisional)

```bash
rsync -az --exclude .venv --exclude .git --exclude .env \
  --exclude __pycache__ --exclude '.*_cache' \
  ./ xele@178.104.233.131:/home/xele/cartaBar/
ssh xele@178.104.233.131 \
  "cd /home/xele/cartaBar && docker compose -f docker-compose.prod.yml up -d --build"
```

- **Excluir `.env`**: el del servidor tiene variables que el local no (`CONFIAR_PROXY`,
  `TOPE_DIARIO_USD`, `LOGS_JSON`). Copiarlo encima las borra.
- **No lanzar dos despliegues a la vez**: se pisan y el contenedor puede quedar
  arrancado con la imagen anterior. Si pasa: `up -d --force-recreate`.
- **~10 s de caída** al final, mientras el contenedor carga el modelo. No desplegar
  en hora punta.
- Si solo cambia el código, el build tarda unos segundos. Si cambian `pyproject.toml`,
  `uv.lock` o el modelo de `embeddings.py`, vuelve a tardar ~8 min.
- El `Dockerfile` tiene una etapa Node aparte (`frontend/`, compilado con Vite)
  antes de la imagen de Python: si solo cambia el código de `carta_bar`, esa
  etapa se reutiliza en caché y no se recompila.

## Qué está sólido

- Modelo de datos con Pydantic, validado al cargar la carta.
- Filtro de alérgenos y dietas determinista: la IA nunca decide si un plato es apto.
- Seguridad: CSP con nonce por petición, escapado en el frontend, límite de peticiones
  por cliente, tope de gasto diario, cabeceras de seguridad. Los logs ya muestran bots
  probando rutas (`../../etc/passwd`, credenciales de AWS) y reciben 404.
- 80 tests, `ruff` y `mypy strict`.
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
