# Copias de seguridad

Una copia que nunca se ha restaurado es una esperanza, no una copia. Este
documento dice qué se guarda, cómo se instala y **cómo se comprueba que sirve**.

## Qué se guarda (y qué no)

| Qué | Dónde vive | ¿Lo cubre el script? |
|---|---|---|
| Base de datos: cartas, platos, traducciones, claves de gerentes (hash), gasto, métricas | Supabase (plan gratuito: **sin copias propias**) | Sí, `bd-AAAA-MM-DD.sql.gz` |
| Fotos, logos y portadas subidos desde el panel | `datos/fotos/` en el servidor, fuera de git | Sí, `fotos-AAAA-MM-DD.tar.gz` |
| Código | GitHub | No hace falta |
| `.env` (claves de Anthropic y Supabase, `SESION_SECRETO`, hash del superadmin) | Solo en el servidor | **No, a propósito**: contiene secretos y no debe viajar sin cifrar. Guárdalo aparte, en tu gestor de contraseñas |
| Token de Cloudflare del certificado comodín | `/etc/letsencrypt/cloudflare.ini` | No. Se puede volver a crear en Cloudflare |

## El límite de esta solución

El script deja las copias **en el propio servidor**. Protege de un borrado
accidental, de un despliegue que rompa datos o de una base de datos dañada.
**No protege de perder el servidor** (o su disco): las copias caerían con él.
Para eso hay que sacarlas de ahí; ver "Sacar las copias del servidor".

## Instalarlo (una vez, en el servidor)

```bash
cd /home/xele/cartaBar
git pull

# Prueba a mano, antes de programar nada:
bash scripts/copia_seguridad.sh
ls -lh /home/xele/copias-carta
```

Debe imprimir `copia hecha: … de BD, … de fotos` y dejar dos ficheros. La
primera vez tarda un poco más: Docker descarga la imagen de Postgres (~100 MB).

Después, que se ejecute solo cada día a las 04:30 (el bar está cerrado):

```bash
crontab -e
```

y añade esta línea:

```
30 4 * * * bash /home/xele/cartaBar/scripts/copia_seguridad.sh >> /home/xele/copias-carta/copia.log 2>&1
```

Cada día se guardan 14 copias y se borran las anteriores.

## Comprobar que funciona

Al día siguiente:

```bash
tail -3 /home/xele/copias-carta/copia.log
ls -lh /home/xele/copias-carta
```

Si el script falla, **no lo hace en silencio**: escribe `ERROR: …` en el log y no
deja una copia a medias. Pero el cron no avisa por sí solo de que ha fallado:
alguien tiene que mirar. Para que te llegue un correo cuando un día no se
ejecute, crea un monitor gratuito en <https://healthchecks.io> y pasa su
dirección al script con `PING_URL` en la línea del cron:

```
30 4 * * * PING_URL=https://hc-ping.com/tu-codigo bash /home/xele/cartaBar/scripts/copia_seguridad.sh >> /home/xele/copias-carta/copia.log 2>&1
```

## Comprobar que se puede restaurar

Hazlo una vez ahora y cada pocos meses. Se restaura en una base de datos
desechable, sin tocar Supabase:

```bash
docker run -d --name prueba-restauracion -e POSTGRES_PASSWORD=prueba postgres:17-alpine
sleep 5
gunzip -c /home/xele/copias-carta/bd-AAAA-MM-DD.sql.gz \
  | docker exec -i prueba-restauracion psql -U postgres -v ON_ERROR_STOP=1
docker exec prueba-restauracion psql -U postgres \
  -c "SELECT (SELECT count(*) FROM public.restaurantes) AS restaurantes, (SELECT count(*) FROM public.platos) AS platos;"
docker rm -f prueba-restauracion
```

Deben salir tus restaurantes y tus 28 platos (y los que hayas añadido). Si
`psql` da un error, la copia no sirve y hay que arreglarlo antes de fiarse de ella.

## Restaurar de verdad

**Fotos** (por ejemplo, tras perder el servidor y volver a montarlo):

```bash
tar -xzf /home/xele/copias-carta/fotos-AAAA-MM-DD.tar.gz -C /home/xele/cartaBar/datos
```

**Base de datos:** el volcado crea las tablas desde cero, así que se restaura
en una base **vacía** (un proyecto nuevo de Supabase, por ejemplo). Restaurarlo
encima de tablas que ya existen da errores de "ya existe". Con las credenciales
de la base nueva:

```bash
export PGPASSWORD='la-contraseña'
gunzip -c bd-AAAA-MM-DD.sql.gz | docker run --rm -i -e PGPASSWORD postgres:17-alpine \
  psql -h HOST -p 5432 -U USUARIO -d postgres -v ON_ERROR_STOP=1
```

Luego se actualizan las variables `POSTGRES_*` del `.env` y se reinicia el contenedor.

## Sacar las copias del servidor

Sin esto, perder el servidor es perder también las copias. Esto vale para todo
el servidor, no solo para carta-bar: la app `cuentas` ya tiene su propia copia
diaria (`/opt/backups/backup.sh`, 7 días), pero también en el mismo disco.
Opciones, de más simple a menos:

1. **Copias del propio Hetzner** (Cloud Console → el servidor → *Backups*):
   una imagen diaria del disco entero, que incluye fotos, `.env`, las copias de
   `/opt/backups` y `/home/xele/copias-carta`, y el resto de apps. Se activa con
   un clic y cuesta el 20 % de lo que cuesta el servidor. Encaja con lo que ya
   hay: los scripts dejan ficheros consistentes en disco y Hetzner los saca de
   ahí (una imagen de un disco con una base de datos en marcha, por sí sola, no
   garantiza una copia limpia).
2. **Bajarlas a tu PC** de vez en cuando, con `scp` (gratis, pero manual):
   `scp -r xele@178.104.233.131:/home/xele/copias-carta .`
3. **Subirlas cada noche a un almacenamiento externo** (Backblaze B2,
   Cloudflare R2, un Storage Box de Hetzner) con `rclone`. Es lo más sólido, pero
   pide crear una cuenta y configurarla.

Ninguna está montada todavía: falta decidir cuál.
