# Copias de seguridad

Una copia que nunca se ha restaurado es una esperanza, no una copia. Este
documento dice qué se guarda, cómo se instala y **cómo se comprueba que sirve**.

## Qué se guarda (y qué no)

| Qué | Dónde vive | ¿Lo cubre el script? |
|---|---|---|
| Base de datos: cartas, platos, traducciones, credenciales de gerentes (solo hashes), gasto, métricas | Postgres gestionado (en plan gratuito, **sin copias del proveedor**) | Sí, `bd-AAAA-MM-DD.sql.gz` |
| Fotos, logos y portadas subidos desde el panel | Directorio de datos del servidor, fuera de git | Sí, `fotos-AAAA-MM-DD.tar.gz` |
| Código | Repositorio git | No hace falta |
| `.env` | Solo en el servidor | **No, a propósito**: contiene secretos y no debe viajar sin cifrar. Se guarda aparte, en un gestor de contraseñas |
| Credenciales del certificado comodín | Fuera del directorio de la app | No. Se pueden volver a emitir desde el proveedor de DNS |

## El límite de esta solución

El script deja las copias **en el propio servidor**. Protege de un borrado
accidental, de un despliegue que rompa datos o de una base de datos dañada.
**No protege de perder el servidor** (o su disco): las copias caerían con él.
Para eso hay que sacarlas de ahí; ver "Sacar las copias del servidor".

## Instalarlo (una vez, en el servidor)

Desde el directorio de la aplicación:

```bash
git pull

# Prueba a mano, antes de programar nada:
bash scripts/copia_seguridad.sh
ls -lh "$DIR_COPIAS"
```

Debe imprimir `copia hecha: … de BD, … de fotos` y dejar dos ficheros. La
primera vez tarda un poco más: Docker descarga la imagen de Postgres (~100 MB).

Después, que se ejecute solo cada día de madrugada, con el negocio cerrado:

```bash
crontab -e
```

y añadir una línea con esta forma:

```
30 4 * * * bash <DIR_APP>/scripts/copia_seguridad.sh >> <DIR_COPIAS>/copia.log 2>&1
```

Cada día se guardan 14 copias y se borran las anteriores.

## Comprobar que funciona

Al día siguiente:

```bash
tail -3 "$DIR_COPIAS/copia.log"
ls -lh "$DIR_COPIAS"
```

Si el script falla, **no lo hace en silencio**: escribe `ERROR: …` en el log y no
deja una copia a medias. Pero el cron no avisa por sí solo de que ha fallado:
alguien tiene que mirar. Para recibir un aviso cuando un día no se ejecute,
sirve un monitor gratuito tipo *dead man's switch* (por ejemplo
<https://healthchecks.io>), pasándole su dirección al script con `PING_URL` en
la línea del cron:

```
30 4 * * * PING_URL=<url-del-monitor> bash <DIR_APP>/scripts/copia_seguridad.sh >> <DIR_COPIAS>/copia.log 2>&1
```

## Comprobar que se puede restaurar

Hazlo una vez al montarlo y cada pocos meses. Se restaura en una base de datos
desechable, sin tocar la de producción:

```bash
docker run -d --name prueba-restauracion -e POSTGRES_PASSWORD=prueba postgres:17-alpine
sleep 5
gunzip -c "$DIR_COPIAS/bd-AAAA-MM-DD.sql.gz" \
  | docker exec -i prueba-restauracion psql -U postgres -v ON_ERROR_STOP=1
docker exec prueba-restauracion psql -U postgres \
  -c "SELECT (SELECT count(*) FROM public.restaurantes) AS restaurantes, (SELECT count(*) FROM public.platos) AS platos;"
docker rm -f prueba-restauracion
```

Deben salir los restaurantes y los platos esperados. Si `psql` da un error, la
copia no sirve y hay que arreglarlo antes de fiarse de ella.

## Restaurar de verdad

**Fotos** (por ejemplo, tras perder el servidor y volver a montarlo):

```bash
tar -xzf "$DIR_COPIAS/fotos-AAAA-MM-DD.tar.gz" -C <DIR_APP>/datos
```

**Base de datos:** el volcado crea las tablas desde cero, así que se restaura
en una base **vacía** (un proyecto nuevo del proveedor, por ejemplo).
Restaurarlo encima de tablas que ya existen da errores de "ya existe". Con las
credenciales de la base nueva:

```bash
export PGPASSWORD='...'
gunzip -c bd-AAAA-MM-DD.sql.gz | docker run --rm -i -e PGPASSWORD postgres:17-alpine \
  psql -h <HOST> -p 5432 -U <USUARIO> -d <BASE> -v ON_ERROR_STOP=1
```

Luego se actualizan las variables `POSTGRES_*` del `.env` y se reinicia el
contenedor.

## Sacar las copias del servidor

Sin esto, perder el servidor es perder también las copias. Opciones, de más
simple a menos:

1. **Copias del propio proveedor del VPS**: una imagen diaria del disco
   entero, que incluye las fotos, el `.env` y las copias del script. Suele
   activarse con un clic por un porcentaje del coste del servidor. Encaja bien
   con lo que ya hay: el script deja ficheros consistentes en disco y la imagen
   los saca de ahí (una imagen de un disco con una base de datos en marcha, por
   sí sola, no garantiza una copia limpia).
2. **Descargarlas periódicamente** con `scp` o `rsync`: gratis, pero manual y
   fácil de olvidar.
3. **Subirlas cada noche a un almacenamiento de objetos externo** (S3, B2, R2,
   un storage box) con `rclone`. Es lo más sólido, pero exige crear y
   configurar una cuenta aparte.

La opción elegida se documenta aquí cuando se monte.
