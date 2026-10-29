# Reglas de este repositorio

Instrucciones fijas para trabajar en Carta Bar. Tienen prioridad sobre
cualquier comportamiento por defecto.

## 1. Nunca subir nada sin permiso explícito

Nunca hago `git commit`, `git push` al repositorio, ni despliego o entro por
SSH al servidor de producción por mi cuenta, aunque tenga las credenciales o
parezca el siguiente paso obvio.

Sí puedo, sin pedir permiso, hacer todo lo que sirva para verificar mi propio
trabajo en local: editar archivos, correr `pytest`, `ruff`, `tsc`,
`npm run build`, `git status`/`diff`/`log`, levantar el servidor de desarrollo,
etc.

Cuando el trabajo esté listo: doy el mensaje de commit y los comandos exactos
(`git add` / `commit` / `push`, y luego los de despliegue de
`docs/ARQUITECTURA.md`), y espero a que el usuario los ejecute él mismo y
confirme el resultado. Nunca lo hago yo ni lo ofrezco como opción.

## 2. Respetar la arquitectura

`docs/ARQUITECTURA.md` documenta cómo está montado el sistema y por qué:
multi-tenant por subdominio, Postgres con fallback a ficheros JSON, filtro de
alérgenos determinista (la IA nunca decide si un plato es apto), traducciones
guardadas una vez por plato, etc. No reestructurar estas decisiones (cambiar de
proveedor de BD, saltarse el filtro determinista, tocar cómo se resuelve el
restaurante...) sin plantearlo primero y que el usuario lo confirme. Un
desarrollo nuevo se apoya en lo que ya hay, no lo sustituye por iniciativa
propia.

## 3. Todo desarrollo nuevo se prueba con tests

Cuando se implementa una funcionalidad o se corrige un bug, va acompañado de
tests que lo cubran (en `tests/`, con `pytest`) antes de darlo por terminado —
y si el bug era real, un test que falle contra el código viejo y pase con el
arreglo, para probar que de verdad lo detecta. Además, antes de dar algo por
hecho: `ruff check` / `ruff format --check` en Python, `tsc -b` y
`npm run build` en `frontend/`. Los cambios de interfaz se comprueban además
arrancando el servidor de desarrollo y mirándolos (cuando el propio entorno no
tenga forma de abrir un navegador, decirlo explícitamente en vez de dar el
cambio por verificado visualmente).

## 4. La carta la define el negocio

No opinar ni reestructurar las categorías o platos de la carta de un
restaurante: es una decisión suya, no del software.

## 5. El nombre de un plato nunca se traduce

En ningún idioma, ni en la carta ni en el chat. Solo se traducen descripción e
ingredientes. El porqué y dónde está forzado en el código, en
`docs/PEDIDO-EN-MESA.md`.
