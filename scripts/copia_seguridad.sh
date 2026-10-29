#!/usr/bin/env bash
# Copia de seguridad diaria: base de datos y fotos subidas desde el panel.
#
# Se ejecuta EN EL SERVIDOR, con cron (ver docs/COPIAS-DE-SEGURIDAD.md):
#   DIR_PROYECTO=/ruta/al/proyecto DESTINO=/ruta/de/copias bash scripts/copia_seguridad.sh
#
# Deja en $DESTINO, un par de ficheros por dia:
#   bd-AAAA-MM-DD.sql.gz       el esquema "public" entero (carta, claves, gasto, metricas)
#   fotos-AAAA-MM-DD.tar.gz    datos/fotos/ (fotos de platos, logos y portadas)
# y borra las de mas de $CONSERVAR_DIAS dias.
#
# Ojo: una copia en el mismo disco no sobrevive a perder el servidor. Este
# script es la mitad de la solucion; la otra es sacarlas de aqui.

set -euo pipefail

DIR_PROYECTO="${DIR_PROYECTO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DESTINO="${DESTINO:-$DIR_PROYECTO/copias}"
CONSERVAR_DIAS="${CONSERVAR_DIAS:-14}"
# pg_dump 17 sabe volcar servidores mas antiguos; al reves no.
IMAGEN_POSTGRES="${IMAGEN_POSTGRES:-postgres:17-alpine}"
# Opcional: una direccion tipo healthchecks.io. Si el script llega al final se
# le avisa; si un dia no llega, ese servicio te manda un correo.
PING_URL="${PING_URL:-}"

FECHA="$(date +%F)"

# Sin "source": el .env puede llevar simbolos '$' que el shell intentaria
# expandir. Solo se leen las variables que hacen falta.
valor() {
    # "|| true": si la variable no esta, que devuelva vacio y salte el mensaje
    # de mas abajo; con "set -e" el grep fallido pararia el script sin decir nada.
    { grep -E "^$1=" "$DIR_PROYECTO/.env" || true; } | head -n 1 | cut -d= -f2- | tr -d '\r'
}

fallo() {
    echo "[$(date '+%F %T')] ERROR: $*" >&2
    exit 1
}

mkdir -p "$DESTINO"
chmod 700 "$DESTINO"  # la copia de la base de datos tiene las claves (hash) de los gerentes

# ---------------------------------------------------------------- base de datos
PG_USER="$(valor POSTGRES_USER)"
PG_PASS="$(valor POSTGRES_PASSWORD)"
PG_DB="$(valor POSTGRES_DB)"
PG_HOST="$(valor POSTGRES_HOST)"
PG_PORT="$(valor POSTGRES_PORT)"
[ -n "$PG_USER" ] && [ -n "$PG_PASS" ] && [ -n "$PG_DB" ] && [ -n "$PG_HOST" ] \
    || fallo "faltan credenciales POSTGRES_* en $DIR_PROYECTO/.env"

BD_FINAL="$DESTINO/bd-$FECHA.sql.gz"
BD_TMP="$BD_FINAL.tmp"
trap 'rm -f "$BD_TMP" "${FOTOS_TMP:-}"' EXIT

# PGPASSWORD se pasa sin valor (-e VARIABLE): asi no aparece en la lista de procesos.
#
# El sed quita "CREATE SCHEMA public;": toda base de Postgres nueva ya trae ese
# esquema, y al restaurar con ON_ERROR_STOP esa linea paraba la restauracion
# antes de crear ninguna tabla.
export PGPASSWORD="$PG_PASS"
docker run --rm -e PGPASSWORD "$IMAGEN_POSTGRES" \
    pg_dump -h "$PG_HOST" -p "${PG_PORT:-5432}" -U "$PG_USER" -d "$PG_DB" \
    --schema=public --no-owner --no-privileges \
    | sed '/^CREATE SCHEMA public;$/d' \
    | gzip > "$BD_TMP" || fallo "pg_dump fallo"
unset PGPASSWORD

# Una copia vacia o rota es peor que ninguna: da falsa tranquilidad.
gzip -t "$BD_TMP" || fallo "el volcado de la base de datos esta corrupto"
zcat "$BD_TMP" | grep -q "CREATE TABLE public.restaurantes" \
    || fallo "el volcado no contiene la tabla restaurantes: no se guarda"
mv "$BD_TMP" "$BD_FINAL"

# ---------------------------------------------------------------- fotos
FOTOS_FINAL="$DESTINO/fotos-$FECHA.tar.gz"
FOTOS_TMP="$FOTOS_FINAL.tmp"
if [ -d "$DIR_PROYECTO/datos/fotos" ]; then
    tar -czf "$FOTOS_TMP" -C "$DIR_PROYECTO/datos" fotos || fallo "no se pudieron empaquetar las fotos"
    tar -tzf "$FOTOS_TMP" > /dev/null || fallo "el paquete de fotos esta corrupto"
    mv "$FOTOS_TMP" "$FOTOS_FINAL"
else
    echo "[$(date '+%F %T')] aviso: no existe $DIR_PROYECTO/datos/fotos, se omiten las fotos"
fi

# ---------------------------------------------------------------- limpieza
find "$DESTINO" -maxdepth 1 -type f \( -name 'bd-*.sql.gz' -o -name 'fotos-*.tar.gz' \) \
    -mtime "+$CONSERVAR_DIAS" -delete

echo "[$(date '+%F %T')] copia hecha: $(du -h "$BD_FINAL" | cut -f1) de BD," \
    "$( [ -f "$FOTOS_FINAL" ] && du -h "$FOTOS_FINAL" | cut -f1 || echo sin ) de fotos"

if [ -n "$PING_URL" ]; then
    curl -fsS -m 10 --retry 3 "$PING_URL" > /dev/null || echo "aviso: no se pudo avisar a $PING_URL"
fi
