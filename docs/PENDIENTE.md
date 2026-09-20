# PENDIENTE · Carta Bar

Leyenda: ✅ hecho y probado · 🔍 hecho, falta verificar · ⬜ pendiente

Producción: https://cartia.jurux.app · cómo está montado, en
[docs/ARQUITECTURA.md](ARQUITECTURA.md)

## Reglas
1. Solo se trabaja en la fase actual.
2. Una fase se cierra cuando se cumple su "Terminada cuando".
3. Idea nueva → a "Aparcado". Sin discutirla, sin empezarla.
4. Cada tarea se responde con sí o no. Nada de "mejorar X".

---

## FASE 1 · Cerrar v0.1 y desplegar  ← ESTAMOS AQUÍ

**Terminada cuando:** La CatedRal tiene la carta en una URL pública con HTTPS,
con fotos reales, y el QR está listo para las mesas.

### Funciona y es seguro
- ✅ Conexión a Supabase por el pooler
- ✅ El agente responde en el idioma del cliente
- ✅ Carta oficial de 28 platos, en los 4 idiomas
- ⬜ Confirmar con el restaurante los alérgenos de 4 platos (Tataki de Atún y las
  3 tartas): la carta original no los detalla y hoy son estimados
- ✅ Un plato sin alérgenos confirmados nunca aparece como apto (filtro determinista)
- ✅ Límite de peticiones por cliente detrás de nginx: `CONFIAR_PROXY=true` y la IP que
  añade nginx, no la que manda el cliente. Probado en producción con 130 peticiones
  con IP inventada: antes pasaban las 130, ahora se cortan al agotar el cupo. Que cada
  comensal tenga su propio cupo lo cubre un test
- ✅ Tope de gasto diario de 5 USD (el chat pasa a "consulta al personal", la carta sigue)
- 🔍 Registro por llamada: pregunta, idioma, tokens, fecha. Se comprueba con la primera
  pregunta real en producción
- ✅ Aviso de alérgenos visible en la carta
- ✅ Ni la página ni la carta se guardan en caché: un cambio llega al desplegar
- ⬜ Probar el chat en producción con una pregunta real (no se ha hecho: gasta)

### Se ve bien (arreglos, no funciones nuevas)
Probado en el iPhone, confirmado bueno.
- ✅ El botón del chat no tapa el último plato
- ✅ El selector de idioma no muestra "ES ES"
- ✅ Tarjetas de categoría alineadas
- ✅ Barra de categorías fija al hacer scroll
- ✅ Escala fija en móvil: sin zoom de pellizco ni de doble toque
- ✅ Safari no amplía la página al tocar el campo del chat
- ✅ El botón del micrófono se retira si el navegador deniega el permiso
- 🔍 Fotos reales de los platos, comprimidas. 9 de 28 platos ya tienen
  foto real, subidas desde el panel de gestión. Faltan las 19 restantes
  (dependen de que el restaurante las vaya pasando)
- ✅ Tocar la foto abre un visor. Abrir, cerrar con la X, tocar fuera y "atrás",
  todo comprobado
- ✅ Quitar la foto de prueba de la Burger La Catedral

### Despliegue
- ✅ Servidor y app funcionando con HTTPS
- ✅ Claves y conexión a BD en variables de entorno, fuera del código
- ✅ Modelo de embeddings dentro de la imagen, y el arranque ya no consulta Hugging Face
  (`HF_HUB_OFFLINE=1`: 0 avisos en los logs; arranca en ~10 s)
- ✅ Desplegar desde GitHub (`git pull` con deploy key de solo lectura
  propia del servidor), no copiando desde el portátil. De paso salió
  y se arregló un `Dockerfile` roto (copiaba una carpeta `web/` que
  `rsync` arrastraba sin querer pero un clon limpio no tiene) —
  detalle en [docs/ARQUITECTURA.md](ARQUITECTURA.md)
- ✅ Dockerfile con dependencias y modelo antes que el código: build de 470 s a 4 s
- ⬜ Copia de seguridad diaria de datos/
- ⬜ Probado en móvil, con datos móviles, en los 4 idiomas
- ✅ QR generado (PNG y SVG) y verificado leyéndolo: apunta a https://cartia.jurux.app
- ✅ Parar gym-app: borrado del todo (contenedor, red, volumen de datos,
  imagen y carpeta) — no solo parado, ya no queda rastro en el servidor

---

## FASE 2 · Prueba real en La CatedRal (1 semana)

**Terminada cuando:** hay una semana de datos y una conversación con la gerente.

- ⬜ Acordar con la gerente qué indica éxito (menos preguntas a camareros, escaneos, conversaciones/día)
- ⬜ Anotar número de mesas y rotaciones
- ⬜ Calcular coste real por conversación y conversaciones por mesa/día
- ⬜ Fijar el precio con esos números

---

## FASE 3 · Panel de gestión (Bloque 2)

**Se empieza solo si:** la Fase 2 da señal positiva — condición saltada
a propósito: se decidió empezar los cimientos ya, sin esperar la prueba
real, porque lo único que falta de Fase 1 son las fotos y depende del
restaurante.

### Cimientos, antes de la primera pantalla
- ✅ La carta pasa de ficheros a la base de datos: 4 tablas nuevas en
  Supabase (`restaurantes`, `categorias`, `platos`, `traducciones_platos`),
  migradas y verificadas — un `UPDATE` en Supabase cambia un precio sin
  redesplegar. Interruptor `CARTA_BD_ACTIVA` en `.env`: si Postgres falla,
  se cae a los ficheros JSON solos
- ✅ Quitar `la-catedral` escrito en el código: ahora `RESTAURANTE_ID` en
  `.env`
- ✅ Almacenamiento para las fotos: se suben desde el panel a
  `datos/fotos/<restaurante>/`, montado como volumen en
  `docker-compose.prod.yml` para que sobrevivan a cada despliegue
- ⬜ Desplegar sin caída (hoy ~10 s mientras arranca el contenedor)

### Pantallas
- ✅ Login por restaurante, contraseña cifrada (pbkdf2, sin dependencias
  nuevas) y sesión por cookie firmada. Contraseña inicial con
  `scripts/establecer_clave_admin.py`; cambiarla luego desde el propio
  panel. Desplegado y confirmado en producción, incluida la escala fija
  en móvil (mismo arreglo que ya tenía la carta pública)
- ✅ CRUD de platos (solo editar, por ahora — crear/borrar esperan a
  poder confirmar categoría en el alta): nombre, descripción, precio,
  ingredientes. Desplegado y confirmado en producción
- ✅ Checkboxes de alérgenos y de etiquetas (recomendación del chef, más
  vendido, etc.) y de dieta (vegano/vegetariano/sin gluten/sin
  lactosa) en el mismo formulario de editar plato — nunca texto libre,
  mismo principio que ya tiene el modelo. Desplegado y confirmado en
  producción, incluida la regla de coherencia sin_gluten+alérgeno gluten
- ✅ Marcar un plato "agotado hoy" — interruptor rápido en la propia
  lista, sin abrir el CRUD completo. Desplegado y confirmado en producción
- ✅ Subida de fotos: comprimidas en el propio navegador (canvas, sin
  Pillow en el servidor), guardadas en disco con volumen persistente
  (`docker-compose.prod.yml`), servidas en `/fotos/<restaurante>/<id>.jpg`.
  Desplegado y confirmado en producción — las 9 fotos reales de La
  CatedRal ya están subidas (Tabla mixta, boquerones, bravas, las dos
  croquetas, tataki, bao de langostino, tartar de salchichón, Japo
  Burger, solomillo)
- ⬜ Gestión de categorías: crear, renombrar, reordenar (arrastrar y soltar)
- 🔍 "Fuera de carta": crear/eliminar especiales del día desde una sección
  propia del panel (categoría centinela `especial-de-hoy`, sin tocar los 28
  platos existentes), visibles en una tarjeta "⭐ Especial de hoy" al
  principio de la carta pública solo si hay alguno activo. Probado en local
  contra Supabase (crear, ver en `/carta`, eliminar). Falta desplegar
- ⬜ Vista previa de cómo queda la carta para el cliente, antes de publicar
  un cambio
- ⬜ Guardar y traducir (dispara `traducir_carta()` en segundo plano, el
  hash ya hace que solo traduzca lo que cambió)
- ⬜ Configuración de marca: nombre del negocio, logo, foto de portada/banner
- ⬜ Importador de carta (PDF o foto → borrador con alérgenos sin confirmar
  → el gerente los confirma con checkboxes, nunca se dan por buenos solos)
  → detalle completo en
  [docs/APARCADO-CARTAS-MULTINEGOCIO.md](APARCADO-CARTAS-MULTINEGOCIO.md)
- ⬜ Métricas básicas
- ✅ Migrar el frontend a React + TypeScript, pantalla a pantalla, sin
  romper nada entre medias (infraestructura con Vite, compilada en una
  etapa nueva del `Dockerfile`, servida por FastAPI en `/assets`):
  login, panel de admin completo y carta pública, las tres
  desplegadas y confirmadas en producción. `esprima` salió de las
  dependencias al dejar de hacer falta

---

## FASE 4 · SaaS multi-cliente (Bloque 3)

**Se empieza cuando:** hay un cliente de pago y llega el 2º o 3º —
salvo el aislamiento por subdominio, adelantado a propósito (ver
abajo) para saber que el sistema escala antes de necesitarlo, no
porque haya ya un segundo cliente.

- ✅ Panel superadmin desplegado y probado en producción (login,
  listado con nº de platos por restaurante, formulario de alta). El
  diseño se afina más adelante
- ⬜ Alta automática de verdad · facturación. El formulario del panel
  crea el acceso (subdominio + contraseña) pero el DNS y el
  certificado HTTPS siguen siendo manuales por restaurante — ver el
  plan del comodín de subdominio más abajo
- ✅ Aislamiento por subdominio: el restaurante se resuelve por el
  `Host` de cada petición (`_resolver_restaurante` en `api.py`), no
  por una variable fija — un mismo servidor sirve ya
  `cartia.jurux.app` (La CatedRal) y `demo.jurux.app` (restaurante de
  prueba, sembrado a mano) sin mezclar datos ni sesiones entre los
  dos. Probado con tests dedicados (`tests/test_multitenant.py`) y
  contra Supabase de verdad. Dar de alta un restaurante ya no es SQL
  a mano (el panel superadmin lo hace), pero el DNS y el certificado
  siguen siendo manuales — ver el plan del comodín justo abajo

### ✅ Comodín de subdominio (adelantado, hecho el 2026-09-19)

Un registro DNS y un certificado por restaurante no escala a 50-300
bares. La corrección no es dejar de usar subdominios (dan sensación
de que cada bar tiene su web propia, mejor que una carpeta dentro del
dominio) — es dejar de crearlos uno a uno:

1. ✅ Registro DNS comodín `*.jurux.app` → 178.104.233.131 en Cloudflare
2. ✅ Certificado HTTPS comodín (desafío DNS-01 con el plugin
   `certbot-dns-cloudflare`, token con permiso mínimo — solo editar DNS
   de `jurux.app`, restringido a las IPs del servidor). Token guardado
   en `/etc/letsencrypt/cloudflare.ini` (permisos `600`, root); renueva
   solo, certbot ya tiene la tarea programada
3. ✅ Un único bloque de nginx (`sites-available/carta`) que sirve
   `jurux.app` y `*.jurux.app` con ese certificado. Se quitó de paso
   `sites-available/gym`, que llevaba días sin app detrás

Verificado con `cartia`, `demo` y un subdominio inventado — los tres
sirven bien con el certificado comodín. `cuentas.jurux.app` (finanzas)
intacto, con su propio certificado, sin mezclarse.

Con esto, el panel superadmin (formulario "Añadir restaurante") deja
de necesitar ningún paso manual aparte para publicar el bar: darlo de
alta ya es suficiente.

**✅ Efecto secundario encontrado al probarlo, ya corregido:**
`_resolver_restaurante()` caía al `RESTAURANTE_ID` fijo (La CatedRal)
para cualquier host sin restaurante real, mezclando el caso legítimo
(desarrollo local: `localhost`, `127.0.0.1`, `testserver`) con el que
no lo es (un subdominio inventado con el comodín activo, que enseñaba
la carta de otro negocio). Ahora solo los hosts de desarrollo caen al
fijo; cualquier otro subdominio sin restaurante da 404. Verificado en
producción: `cosaquesea.jurux.app` → 404, `cartia`/`demo` siguen en 200.

**Por qué ahora y no en la Fase 4 completa:** es infraestructura que
se monta una sola vez, no una pantalla nueva — cuanto más se
retrase, más restaurantes habrá que migrar del esquema manual al
comodín. El resto de la Fase 4 (alta con pago, facturación) sí espera
a tener clientes de pago de verdad.

---

## APARCADO (ideas, no tareas)

- Pedido en mesa (comandas: anfitrión/invitados, cocina/barra en tiempo
  real, cuenta) → especificación completa lista, pero no se empieza
  hasta cumplir su propio requisito de entrada — un restaurante
  usando la carta y el panel de verdad durante un mes (la Fase 2 que
  aún no ha empezado). Detalle completo en
  [docs/APARCADO-PEDIDO-EN-MESA.md](APARCADO-PEDIDO-EN-MESA.md)
- Vídeo en los platos → después del panel
- Botones de filtro sin LLM (sin gluten, vegetariano...) → decidir con el coste medido en Fase 2
- Reducir coste del chat con niveles (filtros → plantillas → caché → LLM),
  estado estructurado en vez de historial, y respuesta del LLM en JSON acotado
  → decidir con el coste medido en Fase 2, detalle en
  [docs/APARCADO-NIVELES-COSTE.md](APARCADO-NIVELES-COSTE.md)
- Cartas de distintos negocios (variantes, extras, combos, plantillas) → detalle en
  [docs/APARCADO-CARTAS-MULTINEGOCIO.md](APARCADO-CARTAS-MULTINEGOCIO.md)
- Transformador de cartas PDF/foto → modelo de datos → mismo documento anterior
- Transcripción de voz en el servidor, para iPhone → solo si en Fase 2 se ve que la
  gente usa el micrófono
- VeriFactu → al montar la facturación

## EN PARALELO (días separados)

- Currículum: Módulo 2 y evaluación formal del Módulo 3
