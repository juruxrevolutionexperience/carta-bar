# PENDIENTE · Carta Bar

Leyenda: ✅ hecho y probado · 🔍 hecho, falta verificar · ⬜ pendiente

Producción: https://la-catedral.jurux.app (`cartia.jurux.app` sigue funcionando) · cómo está montado, en
[docs/ARQUITECTURA.md](ARQUITECTURA.md)

**Pedido en mesa (comandas):** en marcha desde el 2026-09-23, en paralelo a
todo lo de aquí — es su propio documento con sus propias fases (A-D), no
forma parte de la numeración de fases de abajo. Detalle, estado y por qué se
empezó saltando su requisito de entrada, en
[docs/PEDIDO-EN-MESA.md](PEDIDO-EN-MESA.md).

## Reglas
1. Solo se trabaja en la fase actual.
2. Una fase se cierra cuando se cumple su "Terminada cuando".
3. Idea nueva → a "Aparcado". Sin discutirla, sin empezarla.
4. Cada tarea se responde con sí o no. Nada de "mejorar X".

---

## DÓNDE LO DEJAMOS (2026-10-05, tercera parte) — LEER PRIMERO

El usuario se va a ver el bar en persona mañana (2026-10-06). Lo que trae de
vuelta de esa visita decide por dónde seguir. Puntos sueltos que dejó antes
de irse, sin empezar ninguno:

1. ⬜ **Conectar las impresoras de verdad** (cocina, barra, y la de cuenta si
   la hay) al aparato dedicado — de red o por USB, cuántas hay, si alguna
   cuelga del Turbopos (en cuyo caso hace falta el adaptador de red, no
   tocar el Turbopos). Esto es instalación/hardware en el bar, no código.
   El usuario comenta que es un problema típico de muchos bares y que nunca
   lo ha hecho él mismo — ir con tiempo. Guía ya dada en el chat (impresora
   de red vs. USB, predeterminada en Windows, `--kiosk-printing`); falta
   verlo físicamente mañana y contar cuántas impresoras y de qué tipo son.
2. ⬜ **VeriFactu**: pendiente de decidir si se plantea como su propio bloque
   (Fase D de `docs/PEDIDO-EN-MESA.md`, aparcada) o se sigue cobrando con el
   TPV de siempre por ahora. No se ha empezado nada de código.
3. Sobre comandas en general, el usuario cree que el flujo **ya está bien**
   tal cual — no pidió más funcionalidad ahí.
4. ⬜ **El diseño (visual) necesita una vuelta** — dicho así, sin concretar
   qué pantallas ni qué cambiar. Pendiente de que el usuario lo aterrice la
   próxima vez.
5. ⬜ **Bebidas sin carta** — confirmado que es un hueco real (el usuario no
   llegó a decir cuál de las dos lecturas era exactamente: faltan por dar de
   alta como platos normales, o hace falta una "venta libre" tipo TPV para
   que el camarero añada algo que no existe como plato). **Preguntar primero
   qué es exactamente antes de tocar nada** — no asumir, puede ser solo
   catálogo (decisión del negocio, no tocar sin que el usuario la dé de
   alta) o puede ser código nuevo.

---

## DÓNDE LO DEJAMOS (2026-10-05, segunda parte)

Preguntado el usuario si el sistema está listo para un bar real hoy: sí para
pedir y mandar a cocina/barra, **no** si Carta Bar tiene que sustituir el
cobro/caja del TPV (falta VeriFactu, Fase D, aparcado). El camarero puede
trabajar 100% sin que ningún cliente use el QR (botón "Abrir mesa" en
Servicio, ya existía).

De ahí salieron dos cosas más, ya hechas y verificadas (579 tests,
`tests/test_cuentas_postgres.py` con Postgres real vía `pgserver`, `ruff`,
`tsc -b`, `npm run build`):

1. ✅ **Bug real encontrado y corregido**: anular una línea en Cocina no
   tocaba la cuenta de la mesa — se seguía cobrando algo ya anulado. Detalle
   y test en `docs/PEDIDO-EN-MESA.md`, "Bug real: anular una línea...".
2. ✅ **Resumen de cuenta impreso al cobrar**: nuevo `src/carta_bar/cuentas.py`
   + tercer destino "Cuenta" en la pantalla de impresión dedicada
   (`/admin/impresion`), con precios y desglose por persona. No es factura
   (sin NIF ni numeración fiscal). Detalle en `docs/PEDIDO-EN-MESA.md`,
   "Resumen de cuenta impreso al cobrar".

Pendiente: dar los comandos de commit/push cuando el usuario quiera subir
esto (incluye una migración de base de datos nueva, tabla `recibos_cuenta`
— se aplica sola al arrancar, como todo `sql/esquema.sql`). Probar en real
en La CatedRal/el bar, sobre todo la impresión del resumen de cuenta en la
pantalla dedicada.

**Pendiente de decidir con el usuario, no empezado:** si se plantea VeriFactu
como su propio bloque (Fase D) o se sigue cobrando con el TPV de siempre por
ahora.

---

## DÓNDE LO DEJAMOS (2026-10-05) — LEER PRIMERO

Los tres ajustes pendientes del 2026-10-04 están hechos y verificados
(`tsc -b`, `npm run build`, `ruff check`, `pytest` 570 passed). Nada
comiteado ni desplegado todavía.

1. ✅ Diálogo de idioma antes que el de nombre: `EntrarMesaDialog` ahora no se
   pinta si `mostrarSelectorIdioma` está activo, así que un turista elige
   idioma antes de que le pregunten cómo se llama.
2. ✅ Avisos al personal: `useAvisosPersonal.ts` + `AvisosPersonal.tsx`, un
   banner fijo arriba a la derecha, montado una vez en `App.tsx` (visible en
   cualquier sección), con un pitido simple (WebAudio, sin archivo de audio)
   solo cuando aparece un aviso nuevo (mesa por confirmar o que pide la
   cuenta). No es historial: desaparece solo en cuanto se resuelve la mesa.
3. ✅ Panel simplificado en "día a día" vs "montaje": `secciones.tsx` marca
   cada sección con `montaje: boolean` (Servicio/Cocina/Mesas = día a día,
   el resto = montaje). `MenuLateral.tsx` muestra el día a día siempre
   visible y el montaje plegado bajo un desplegable "Montaje" (recuerda si
   estaba abierto en `localStorage`, empieza cerrado la primera vez). Nadie
   pierde acceso: el equipo de Carta Bar sigue entrando a QR/Marca/Platos
   para el montaje inicial, solo que no estorba en el día a día del bar.

Pendiente: dar los comandos de commit/push y despliegue cuando el usuario
quiera subir esto; probar en real en La CatedRal/el bar.

---

## DÓNDE LO DEJAMOS (2026-09-29)

- **Bloque 1 probado de punta a punta por el usuario**, en el móvil de
  verdad contra `demo.jurux.app`: escanear el QR, aceptar en Servicio,
  refresco automático a los 5 s en ambas pantallas. Confirmado con el
  usuario, sin fallos pendientes.
- **La carta ya se une a la mesa al escanear el QR** (antes solo abría la
  carta normal, sin llamar al backend): `useMesa.ts`, barra provisional de
  estado, refresco cada 5 s en el cliente igual que en Servicio.
- **Bloque 2 (propuestas), completo: backend + pantalla, sin desplegar.**
  Endpoints, modelo de datos, botón "Pedir" en cada plato con selector de
  formato/extras, panel del pedido de la mesa (quitar, confirmar), todo en
  tiempo real por SSE. 493 tests (`uv run pytest -q`), `ruff`, `tsc -b` y
  `npm run build` limpios. Detalle completo en `docs/PEDIDO-EN-MESA.md`,
  "Bloque 2 en detalle". **Solo comprobado con Edge headless y datos
  simulados: falta que el usuario lo pruebe en un móvil real.**
- `mypy` sigue bloqueado en este PC (política de Control de aplicaciones,
  os error 4551); `ruff check`/`format`, `pytest`, `tsc` y `npm run build`
  sí funcionan aquí.
- Nada de esto está commiteado todavía: falta dar los comandos de
  `git add/commit/push` y desplegar (incluye la migración SQL nueva, tabla
  `propuestas`, que se aplica sola al arrancar).
- **Siguiente paso tras probarlo:** bloque 3 (comandas de verdad: cocina/
  barra, tickets, rol camarero con acceso rápido).
- **Extra pedido por el usuario (mismo día):** en "Extras y opciones" del
  panel, cada grupo tiene ahora un botón "Asignar a platos" que marca el
  grupo en varios platos de golpe (agrupados por categoría), sin tener que
  abrir cada plato uno a uno para tildar la casilla. `asignar_grupo_a_platos()`
  en `productos.py`, endpoint `PUT /admin/api/grupos-opciones/{id}/platos`,
  8 tests nuevos. Formatos (media ración, etc.) siguen siendo por plato,
  porque el precio cambia en cada uno — eso no tiene atajo.
- **Tras probar en La CatedRal, 3 ajustes más (mismo día):**
  1. Al escanear el QR ahora se pide el nombre antes de entrar
     (`EntrarMesaDialog.tsx`), con opción de "seguir sin decirlo": antes
     siempre salía "Comensal 2", ahora se ve el nombre real en el pedido.
  2. Al añadir una propuesta, el panel del pedido se abre solo, para que
     quede claro que es una cesta compartida sin enviar, no un pedido ya
     mandado; además un aviso visible ("esto aún no se ha enviado") mientras
     haya líneas pendientes.
  3. El formulario valida los grupos obligatorios (ej. "Punto de la carne")
     antes de enviar nada al servidor, en vez de esperar al error 400.
  - Confirmado que ya funcionaba (sin cambios): se puede ir llenando la
    cesta aunque la mesa siga "por confirmar", sin perder nada mientras el
    camarero acepta. Test añadido para dejarlo protegido: 500 tests en total.
  - **Aviso importante, dicho también al usuario:** hoy "Confirmar pedido"
    solo cambia el estado interno a "confirmada"; no existe todavía ninguna
    pantalla de cocina/barra que lo reciba. Eso es el bloque 3, pendiente de
    plantear a fondo la próxima vez.

## DÓNDE LO DEJAMOS (2026-10-04) — LEER PRIMERO

El usuario probó el flujo completo en el bar. Funciona; tres ajustes:

1. ✅ **El pedido ya no se abre solo al añadir un plato.** Sale un aviso breve abajo
   ("✓ Tabla Mixta añadido · Ver pedido") que se quita a los 3 s, y el contador del pedido
   salta. El cliente lo abre cuando quiere. Esto deshace el ajuste del 2026-09-29 ("al añadir,
   el panel se abre solo"): en la práctica cortaba el ir eligiendo.
2. ✅ **Cocina sin paso "Empezar":** una lista y un botón "Listo" por comanda. Test nuevo
   `test_un_solo_toque_de_recien_llegada_a_servida`.
3. ⬜ **Avisos al personal** (mesa nueva, pide la cuenta…) en el aparato donde esté el
   panel, visibles y con sonido. Propuesto, pendiente de que el usuario elija alcance.
4. ⬜ **Simplificar el panel del bar:** el usuario no quiere que el cliente monte nada (QR,
   marca, plano, extras). Propuesto separar "montaje" (solo superadmin) de "día a día".
   Pendiente de decidir qué ve cada uno.

Visto de paso: al escanear por primera vez, el diálogo del nombre ("Dinos tu nombre") sale
encima del selector de idioma, en español, antes de que un turista pueda elegir el suyo.

## DÓNDE LO DEJAMOS (2026-10-01) — LEER PRIMERO

**Sin commitear todavía** (recuerda: nunca lo subo yo solo, comandos al final de este bloque).

Construido hoy, completando el ciclo de vida de una mesa de principio a fin:
1. **Pedir la cuenta y cobrar**, cerraba el hueco de "cuenta_pedida" (existía el estado, nada
   lo activaba). Cliente pide, camarero cobra y cierra con motivo "cobrada".
2. **Anular una línea ya confirmada**, con motivo, sin borrarla nunca. Botón en Cocina.
3. **Plato agotado:** ya existía (el interruptor "Disponible" de Platos). Confirmado con el
   usuario que no hace falta nada más.

Detalle técnico en [docs/PEDIDO-EN-MESA.md](PEDIDO-EN-MESA.md). **569 tests, todos en verde.**

**Incidente resuelto hoy, importante para la próxima sesión:** `uv run pytest` se bloqueó
toda la sesión con `os error 4551` ("Control de aplicaciones bloqueó este archivo"). Causa:
**Smart App Control de Windows** (modo Enforce) rechazando el `python.exe` de `.venv` por no
cumplir su "nivel de firma Enterprise" (confirmado mirando
`Microsoft-Windows-CodeIntegrity/Operational`, eventos 3077/3033/3089). El usuario lo
desactivó en Seguridad de Windows → Control de aplicaciones y del explorador → Smart App
Control → Desactivado, y pytest volvió a funcionar. **Si vuelve a pasar, es esto.**

**Pendiente, igual que antes:**
- Confirmar si las impresoras de cocina/barra son de red o USB al Turbopos (nunca tocar el
  Turbopos). Ver `docs/PEDIDO-EN-MESA.md`, "Impresión en cocina/barra".
- Config de nginx del servidor, para confirmar si el buffering afectaba al tiempo real (SSE).
  Sin confirmar todavía si sigue siendo un problema tras los últimos despliegues.
- ✅ Quitado el paso "Empezar" en Cocina: un solo botón "Listo" (2026-10-04).
- Pregunta sin responder: ¿el QR de la mesa debería verse también en modo servicio dentro de
  Mesas (hoy solo en modo lápiz)?

**Lo único que queda del plan "pedido en mesa" sin construir: rol camarero** (login propio,
permisos limitados). Se plantea aparte, con calma, cuando toque — no bloquea nada de lo demás.

**Siguiente paso acordado con el usuario:** probar el flujo completo de principio a fin
(escanear → pedir → aceptar → confirmar → cocina → cuenta → cobrar) antes de seguir
desarrollando nada más.

## DÓNDE LO DEJAMOS (2026-09-29, cierre del día) — LEER PRIMERO

Día largo, todo commiteado, subido y desplegado (`fb0eb07`, confirmado por el usuario en
producción). Resumen de lo que se construyó hoy, de arriba abajo, y lo que queda abierto.

**Construido y probado por el usuario en producción:**
1. Bloque 2 (propuestas): pedir desde la carta con formato/extras, cesta compartida, el
   anfitrión confirma. Pide el nombre al entrar.
2. Bloque 3 (comandas): confirmar reparte tickets en cocina/barra; pantalla "Cocina" en el
   panel; el cliente ve "Comanda N · en preparación/servido" en su móvil.
3. Pantalla de impresión dedicada (`/admin/impresion`), con historial y "Reimprimir" (por si
   se cancela el diálogo de imprimir antes de tener el modo silencioso configurado).
4. **Gestión de la comanda desde la mesa:** al entrar en una mesa ocupada (desde Servicio o
   desde Mesas, ahora es el mismo panel) se ve todo lo pedido por persona, el total, se puede
   añadir con un selector estilo TPV (categorías + platos grandes), ajustar el precio de una
   línea y confirmar.
5. **Mesas y Servicio unificados en modo ojo:** dejaron de ser dos paneles distintos. Mesas
   usa el mismo `PanelServicio` (abrir/aceptar/comanda/liberar); el modo lápiz sigue aparte,
   solo para montar el plano.

Detalle tecnico completo de todo esto en [docs/PEDIDO-EN-MESA.md](PEDIDO-EN-MESA.md).

**Abierto, para retomar la próxima sesión (en este orden de prioridad):**
1. **Sospecha sin confirmar: nginx puede estar bloqueando el tiempo real (SSE).** El usuario
   describió un fallo ("pedido que no se añade, lista en blanco") compatible con que nginx
   acumule (buffer) la respuesta en vez de dejarla fluir. Hace falta ver la config de nginx
   del servidor (`/etc/nginx/sites-available/` o `conf.d/` del dominio) para confirmarlo y
   añadir `proxy_buffering off;` en las rutas `/api/mesa/*/eventos` y
   `/admin/api/*/eventos` si hace falta. **Pedido al usuario, sin respuesta todavía.**
2. **Impresoras físicas de cocina/barra: ¿red (IP) o USB al Turbopos?** Determina si basta un
   mini PC/tablet en la wifi, o hace falta un adaptador de impresora en red (15-20€). Sin
   tocar el Turbopos en ningún caso (es la máquina crítica de los camareros, no se toca).
3. **Pregunta sin responder:** ¿el QR de la mesa debería verse también en modo servicio
   dentro de Mesas (antes se veía, ahora solo en modo lápiz), o se queda solo en edición?
4. **Decisión aplazada por el usuario ("hay que verlo bien"):** en la pantalla Cocina, quitar
   el paso intermedio "Empezar" y dejar un solo botón "Listo" (recibida → servida
   directamente), ya que el cliente ve lo mismo ("en preparación") en los dos estados de
   camino. Propuesto, sin decidir.
5. **Aparcado como proyecto propio, sin fecha:** sustituir Comandator por Carta Bar
   directamente en el Turbopos (rol camarero en el TPV físico). No tocar hasta plantearlo a
   fondo aparte.

## DÓNDE LO DEJAMOS (2026-09-29, madrugada) — LEER PRIMERO

- **Impresión en cocina/barra: construida, pendiente de probar en el bar.**
  Nueva pantalla `/admin/impresion` para un aparato APARTE y dedicado — el
  usuario dejó clarísimo que el TPV Turbopos de la barra NUNCA se toca para
  esto: es la máquina crítica donde cierran mesas y ya va lenta con
  Comandator instalado. Detalle completo en `docs/PEDIDO-EN-MESA.md`,
  "Impresión en cocina/barra". 538 tests, todo limpio.
- **Pendiente de comprobar en el bar (no es cosa de código):** si las
  impresoras de cocina/barra son de red o USB al Turbopos, y qué aparato se
  dedica a la impresión. Según eso, puede hacer falta un adaptador de
  impresora en red (15-20€) si son USB.
- **Aparcado como proyecto propio:** sustituir Comandator por Carta Bar
  directamente en el Turbopos (rol camarero en el TPV físico). Es un salto
  grande, con su propia sesión de planteamiento — no se ha tocado nada de
  esto todavía, ni se debe mezclar con lo de imprimir.
- Sigue sin desplegar nada de hoy (bloques 2 y 3 completos + esto).

## DÓNDE LO DEJAMOS (2026-09-29, noche) — LEER PRIMERO

- **Aclarado con el usuario (sin cambios de código):** el destino cocina/
  barra se configura por categoría en **Platos → "Organizar categorías"**
  (no en "Extras y opciones", como dije mal en un momento dado). Bebidas en
  "Barra", el resto ya va a "Cocina" por defecto.
- **Añadido: el cliente ve el estado de su comanda.** Antes, tras confirmar,
  el móvil solo decía "· pedido" sin más. Ahora hay un chip por comanda
  ("Comanda 5 · en preparación" / "servido"), en tiempo real por SSE.
  Detalle en `docs/PEDIDO-EN-MESA.md`. 535 tests, todo limpio.
- Sigue sin desplegar nada de la tarde de hoy (bloque 3 + esto). Ver el
  bloque de comandos más abajo.

## DÓNDE LO DEJAMOS (2026-09-29, tarde) — LEER PRIMERO

- **Bloque 3 (comandas de verdad) construido: backend + pantalla, sin desplegar.**
  Al confirmar el pedido, ahora se arma una comanda de verdad y se reparte en
  tickets de cocina/barra; nueva sección "Cocina" en el panel del gerente con
  tarjetas grandes por ticket. Detalle completo en `docs/PEDIDO-EN-MESA.md`,
  "Bloque 3 en detalle". 527 tests, `ruff`, `tsc -b`, `npm run build` limpios.
  **Solo comprobado con Edge headless y datos simulados: falta probarlo en
  un móvil/PC real.**
- **Decidido con el usuario (2026-09-29):** confirmar manda al instante, sin
  ventana de agrupación; la pantalla de cocina vive en el `/admin` del
  gerente por ahora (no hay rol camarero todavía); el alcohol solo se marca
  visualmente en la tarjeta, sin confirmación expresa al servirlo.
- **Pendiente para más adelante:** rol camarero con su propio acceso, aviso
  sonoro en la pantalla de cocina, SSE ahí en vez de refresco cada 5 s,
  confirmación expresa del alcohol al servir, anular una línea con motivo.
- Nada de esto está commiteado: falta `git add/commit/push` y desplegar
  (la migración SQL trae 3 tablas nuevas: `comandas`, `tickets`,
  `lineas_ticket`, se aplican solas al arrancar).

## DÓNDE LO DEJAMOS (2026-09-27) — LEER PRIMERO

- **Bloque 1 (estados de mesa + pantalla Servicio):** commiteado y subido
  (`32c7125`). Falta confirmar que está desplegado.
- **Productos: 🔍 hecho en local, falta subir y desplegar.** Detalle en
  `docs/PEDIDO-EN-MESA.md`, sección "Productos".
- **Decidido con el usuario (2026-09-27):** extras en grupos reutilizables;
  destino cocina/barra por categoría con excepción por plato; los formatos
  no se traducen (como el nombre del plato); los formatos se ven ya en la
  carta, los extras solo al pedir.
- **Siguiente: bloque 2** (pedidos, rondas, pedir la cuenta), que ya puede
  apoyarse en formatos, extras y destino.
- Aviso para el negocio, no tocado: algunas descripciones llevan precios
  escritos a mano (croquetas: "Media ración: 5,95 €"). Si el restaurante pone
  formatos, conviene que quite ese texto para no tener dos precios.

## DÓNDE LO DEJAMOS (2026-09-26)

- **Bloque 1 del flujo de mesa: 🔍 hecho en local, falta subir y desplegar.**
  Estados de mesa, abrir/aceptar/liberar, quitar comensales y cierre
  automático, más la pantalla **Servicio** (tarjetas por zona). Detalle en
  `docs/PEDIDO-EN-MESA.md`, "Bloque 1 en detalle".
- **Decidido con el usuario (2026-09-26):**
  1. **Sin código de 4 cifras.** Quien escanea entra; la protección es que el
     camarero sale a la mesa ("¿habéis pedido por la app?") y la acepta.
  2. Cierre automático: 30 min "por aceptar" y 4 h sin actividad.
  3. **Panel rápido en tarjetas** (mismas mesas que el plano, separadas por
     zona) adelantado del bloque 3 al 1: es donde el camarero acepta.
  4. **Siguiente: productos** (destino cocina/barra, formatos con precio,
     extras, alcohol), luego bloque 2 (pedidos). Falta preguntar al usuario:
     ¿extras por plato o grupos reutilizables?
- Verificación: 433 tests; SQL probado contra un Postgres 16 real (migración
  sobre datos viejos, carreras de 8 escaneos a la vez); pantalla probada en
  Chromium real (móvil y escritorio, claro y oscuro, botones pulsados).
- Entorno de este PC (WSL): Python sí funciona aquí. `uv` instalado en
  `~/.local/bin`; Postgres de prueba con `uv run --with pgserver`.

## DÓNDE LO DEJAMOS (2026-09-24)

- **Frontend de mesas: CERRADO** por decisión del usuario. Último cambio
  (plano en móvil: alto medido en JS, barra en dos filas, zoom sin flotar)
  desplegado en `dc2538c`. No se toca más salvo fallo real.
- **Siguiente: backend del pedido en mesa.** Todo el flujo acordado está en
  `docs/PEDIDO-EN-MESA.md`, secciones "Flujo de mesa y pedidos" y "Bloque 1
  en detalle". Orden: bloque 1 (estados, abrir, unirse, confirmar, liberar)
  → bloque 2 (pedidos, rondas, pedir la cuenta) → bloque 3 (rol camarero +
  acceso rápido tipo rejilla por zona, como Comandator).
- **Acordado con el usuario (2026-09-24):** confirmación del camarero cuando
  abre un cliente; "¿seguro?" antes de enviar comanda y, una vez enviada,
  solo el personal la deshace; el camarero/gerente puede liberar mesas;
  pedir la cuenta desde la carta; segunda contraseña "camarero" por
  restaurante. Principio: plantear cada bloque a fondo justo antes de
  hacerlo, no resolver todo de golpe.
- **Pendiente de respuesta del usuario para arrancar el bloque 1:**
  1. ¿Código de 4 cifras para que un invitado se una a una mesa con clientes?
  2. ¿Cierre automático: 30 min "por confirmar" sin confirmar y 4 h sin
     actividad?
- Sin cambios de código pendientes de subir; solo estos dos documentos.
- Nota: unos textos legales de Mansel que se pegaron el 2026-09-24 eran de
  otro proyecto. Ignorarlos, no tienen nada que ver con Carta Bar.

## DÓNDE LO DEJAMOS (2026-09-22)

Todo el trabajo de hoy está commiteado, subido a GitHub, desplegado en
producción y **comprobado por el usuario al 100 %**: importador de carta
(y confirmado que el gerente no ve ese botón), vista de escritorio,
visor de fotos navegable, copia de seguridad ejecutándose sola de
madrugada, y móvil con datos móviles en los 4 idiomas. Detalle de cada
pieza, en la Fase 3 más abajo (ya marcadas ✅).

### Confirmado en producción (2026-09-21, no volver a probar)
QR con hoja imprimible (impresión real probada) · chat con respuestas
completas, 15 platos y avisos en los 4 idiomas · alérgenos confirmados por
plato · guardar y traducir en segundo plano.

### Decisiones tomadas el 2026-09-22 que no se pueden olvidar
- **El importador es del superadmin, no del gerente**, y no está pensado
  solo para el alta inicial de un restaurante: también sirve para ampliar
  una carta ya existente con una sección nueva (se relaja la idea original
  de "solo bares con la carta vacía").
- Sigue en pie todo lo de ayer: nombre del plato nunca se traduce, un plato
  sin alérgenos confirmados nunca es "apto", traducciones con Sonnet 5, QR a
  `<restaurante>.jurux.app`, el gerente no ve costes ni métricas.

### Decisiones tomadas hoy que no se pueden olvidar
- **El importador es del superadmin, no del gerente**, y no está pensado
  solo para el alta inicial de un restaurante: también sirve para ampliar
  una carta ya existente con una sección nueva (se relaja la idea original
  de "solo bares con la carta vacía").
- Sigue en pie todo lo de ayer: nombre del plato nunca se traduce, un plato
  sin alérgenos confirmados nunca es "apto", traducciones con Sonnet 5, QR a
  `<restaurante>.jurux.app`, el gerente no ve costes ni métricas.

### Aviso de entorno: Python bloqueado en este PC
Este PC de trabajo tiene una Directiva de Control de aplicaciones de Windows
que bloquea **cualquier** ejecución de `python.exe` (directo o vía `uv run`),
incluso el intérprete del propio `.venv` — no es el problema antiguo de la
DLL de `torch`, es un bloqueo total. `ruff` sí funciona (es un binario aparte
que no depende de Python). Para verificar con `mypy`/`pytest` de verdad desde
este PC: lanzar un agente con `isolation: "remote"` (entorno en la nube, sin
la directiva) y pasarle el contenido exacto de los archivos nuevos o
modificados como texto en el prompt — un agente en un worktree local normal
**no sirve**, solo ve el último commit subido a GitHub, no los cambios sin
commitear. El PC de casa del usuario no tiene este bloqueo.

### Para retomar
- **Desplegar** (lo ejecutas tú en el servidor, yo solo doy los comandos):
  `cd /home/xele/cartaBar && git pull && docker compose -f docker-compose.prod.yml up -d --build`
- **Superadmin:** `/superadmin` en cualquier subdominio que exista, por ejemplo
  https://la-catedral.jurux.app/superadmin
- **SQL ya ejecutado en Supabase:** columnas `platos.alergenos_confirmados` y
  `restaurantes.texto_qr`; los platos p010 (Tataki de Atún) y p025, p026, p027
  (las 3 tartas) puestos en `alergenos_confirmados = false`. Las tablas de
  métricas se crean solas al arrancar.
- **Tests:** 304+ pasan (313 con los del importador). Los 5 de búsqueda y
  embeddings necesitan el modelo real y no corren en el PC de trabajo
  (Windows bloquea la DLL de torch); el resto se corre con un sustituto
  temporal de `sentence_transformers`.
- **Modelos:** chat e intérprete, Haiku 4.5; traducciones e importador,
  Sonnet 5 (`MODELO_TRADUCCION`). El gasto se anota con la tarifa de cada
  modelo (`PRECIOS_POR_MODELO` en `costes.py`); un modelo desconocido se
  cobra a la más cara para no pasarse del tope de 5 USD.

### Pendiente suelto (no de código)
- Confirmar con La CatedRal los alérgenos reales de 4 platos (Tataki de
  Atún y las 3 tartas).
- Preguntar si "Solomillo de Ternera" es *veal* o *beef* (ambiguo en
  español, hoy inconsistente entre idiomas).

---

## FASE 1 · Cerrar v0.1 y desplegar  ← ESTAMOS AQUÍ

**Terminada cuando:** La CatedRal tiene la carta en una URL pública con HTTPS,
con fotos reales, y el QR está listo para las mesas.

### Funciona y es seguro
- ✅ Conexión a Supabase por el pooler
- ✅ El agente responde en el idioma del cliente
- ✅ Carta oficial de 28 platos, en los 4 idiomas
- ⬜ Confirmar con el restaurante los alérgenos de 4 platos (Tataki de Atún y las
  3 tartas): la carta original no los detalla y hoy son estimados. Ya están
  marcados como sin confirmar en producción (la carta muestra "consultar
  alérgenos" y el chat no los recomienda ante una alergia); cuando el
  restaurante los confirme, el gerente marca la casilla en su panel
- ⬜ Preguntar al restaurante si la "Solomillo de Ternera" es ternera (*veal*) o
  vacuno (*beef*): en español es ambiguo y hoy sale como *Kalbsfilet* en alemán
  y *beef*/*bœuf* en inglés y francés
- 🔍 Un plato sin alérgenos confirmados nunca aparece como apto: campo
  `alergenos_confirmados` por plato (2026-09-21). Antes no existía ese concepto
  en el código y esta línea estaba marcada ✅ sin estarlo: el filtro solo quitaba
  los platos que *listan* el alérgeno, y uno con los alérgenos vacíos o
  adivinados pasaba como apto. Ahora, ante una alergia o dieta, el chat solo
  usa platos confirmados (y manda al personal si no queda ninguno); a un plato
  sin confirmar no se le presenta como "sin alérgenos"; y la carta pública
  muestra "consultar alérgenos" en vez de sus alérgenos. El gerente lo marca
  con la casilla "He revisado los alérgenos y la dieta" al crear o editar; un
  plato nuevo entra sin confirmar. Los platos que ya existían se dan por
  revisados, salvo los 4 estimados (Tataki y las 3 tartas), que hay que marcar
  como sin confirmar a mano. Con tests, y comprobado que fallan con la lógica
  anterior. Probado con el modelo real: una primera versión metía el aviso de
  "hay platos sin confirmar" en el prompt y el chat se negaba a recomendar
  ningún plato sin gluten; ahora el aviso se añade como frase fija tras la
  respuesta, en el idioma del cliente. Desplegado y comprobado en los 4 idiomas.
  Es la base del importador
- 🔍 Traducciones de calidad y coherentes con el chat: las traducciones
  guardadas tenían errores serios (la Lubina en alemán como "Loup de mer" y
  "Seeluppenfilet", una palabra inventada) y el chat traducía por su cuenta y se
  equivocaba otra vez ("Seezungenfilet" = lenguado). Ahora se traducen con
  Sonnet 5 (`MODELO_TRADUCCION`; el doble de precio que Haiku, pero solo se paga
  al crear o editar un plato: ~0,007 $ por plato en los 3 idiomas, 0,20 $ la
  carta entera), y el chat usa esas mismas traducciones en vez de traducir. Se
  pasan hasta 15 platos al chat (eran 10: un celíaco veía 10 de 13). Hay que
  rehacer las traducciones de producción con `--forzar` (el hash solo mira el
  español). Probado con el modelo real en local. **El nombre del plato no se
  traduce nunca** (decisión del restaurante: un cliente que lee "Jamón" se lo
  dice tal cual al camarero), forzado en código al leer y al traducir, así que
  vale ya con las traducciones que hay guardadas
- 🔍 Respuestas del chat cortadas a media palabra: una lista de 10 platos pide
  ~410 tokens y el límite era 400 (medido con el modelo real). Límite subido a
  900, con margen para 15 platos (solo cuesta lo que el modelo escribe) y, si aun así se corta, se quita
  la última línea incompleta. De paso, al modelo se le dice para qué dietas es
  apto cada plato confirmado: sin eso, en inglés no se atrevía a afirmar que un
  plato era "gluten free" y listaba 4 de 10. Falta verlo en producción
- ✅ Límite de peticiones por cliente detrás de nginx: `CONFIAR_PROXY=true` y la IP que
  añade nginx, no la que manda el cliente. Probado en producción con 130 peticiones
  con IP inventada: antes pasaban las 130, ahora se cortan al agotar el cupo. Que cada
  comensal tenga su propio cupo lo cubre un test
- ✅ Tope de gasto diario de 5 USD (el chat pasa a "consulta al personal", la carta sigue)
- 🔍 Registro por llamada: idioma, tokens, coste, fecha (el texto de la pregunta
  no se guarda a propósito: puede llevar datos de salud). Ya ha habido preguntas
  reales; se comprueba en el superadmin → Métricas
- ✅ Aviso de alérgenos visible en la carta
- ✅ Ni la página ni la carta se guardan en caché: un cambio llega al desplegar
- ✅ Probar el chat en producción con preguntas reales: hecho el 2026-09-21
  ("algo sin gluten" en los 4 idiomas y "postre sin lactosa"). De ahí salieron
  los arreglos de alérgenos, respuestas cortadas, 15 platos y traducciones

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
- 🔍 Copia de seguridad diaria: `scripts/copia_seguridad.sh` guarda cada día
  la base de datos (Supabase, plan gratuito sin copias propias) y `datos/fotos/`,
  14 días de rotación, y falla en voz alta si la copia sale vacía o rota. Probado
  con un `docker` simulado y en el servidor real. **Restauración comprobada**
  (2026-09-21) en una base desechable: 2 restaurantes, 29 platos, 84
  traducciones. La primera prueba falló por una línea `CREATE SCHEMA public;`
  del volcado, y se quitó del propio script. Cron diario a las 04:50
  instalado y confirmado (2026-09-22): se ejecutó solo esta noche, `copia.log`
  limpio. Detalle en [docs/COPIAS-DE-SEGURIDAD.md](COPIAS-DE-SEGURIDAD.md)
- ⬜ Sacar las copias del servidor: **aparcado hasta que haya clientes** (ver
  "Aparcado")
- ✅ Probado en móvil, con datos móviles, en los 4 idiomas (2026-09-22)
- ✅ QR generado (PNG y SVG) y verificado leyéndolo. El de La CatedRal impreso apunta a
  `cartia.jurux.app`, que sigue funcionando; el que genera ahora el panel apunta a
  `la-catedral.jurux.app`
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
- ✅ CRUD de platos completo: crear (con categoría y casilla obligatoria
  "he revisado los alérgenos"), editar y eliminar (borra también foto y
  traducciones): nombre, descripción, precio, ingredientes. Desplegado y
  confirmado en producción
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
- ✅ Gestión de categorías: crear, renombrar, reordenar arrastrando y borrar
  (solo vacías), dentro de Platos → "Organizar categorías". Backend
  verificado contra un Postgres real; falta confirmar el arrastre en el móvil
- 🔍 "Fuera de carta": crear/eliminar especiales del día desde una sección
  propia del panel (categoría centinela `especial-de-hoy`, sin tocar los 28
  platos existentes), visibles en una tarjeta "⭐ Especial de hoy" al
  principio de la carta pública solo si hay alguno activo. Probado en local
  contra Supabase (crear, ver en `/carta`, eliminar). Desplegado con el resto;
  falta comprobarlo en producción
- ✅ Vista previa en vivo de la tarjeta del plato al editar o crear (la
  misma tarjeta de la carta pública). Un borrador con "Publicar" queda
  descartado por ahora: los cambios se publican al guardar
- 🔍 Guardar y traducir: crear o editar un plato (o un especial) lanza
  `traducir_restaurante()` en segundo plano (`BackgroundTasks`); el hash hace
  que solo se pague lo que cambió, respeta el tope diario y anota el coste.
  Un candado por restaurante evita traducir dos veces lo mismo. Agotar un plato
  no traduce. Con tests (`tests/test_traduccion_panel.py`). Falta probarlo en
  producción: editar un plato y ver la carta en inglés al cabo de unos segundos.
  De paso: una traducción cuyo hash ya no coincide con el texto del plato
  no se enseña (sale en español), para que un plato editado nunca muestre
  ingredientes de la versión anterior. Vigencia de las 28 × 3 traducciones de
  Supabase: se rehacen todas con `--forzar` (ver "Dónde lo dejamos")
- 🔍 Configuración de marca: sección "Marca" del panel con nombre del negocio,
  logo y foto de portada (se comprimen en el navegador y se guardan en el mismo
  volumen que las fotos de platos, con nombre fijo por tipo). Backend con tests
  (`tests/test_admin_marca.py`) y frontend con `tsc` limpio. Desplegado y dado
  por bueno; falta probarlo en el móvil con un logo y una portada reales.
  Subtítulo y color de marca quedan fuera: hoy solo se cambian en la base de
  datos
- ✅ Importador de carta desde foto (`src/carta_bar/importador.py`): sube una
  foto de una carta en papel, Sonnet 5 (visión) propone los platos, se
  revisan en una tabla editable y no se crea nada hasta confirmar. Es una
  herramienta de uso propio en el **superadmin**, no un servicio para el
  gerente — lo dispara quien decide que vale la pena ese gasto (~1-2
  céntimos por foto). El gerente sigue añadiendo platos y categorías a mano
  con el panel que ya tenía, sin cambios ahí. Probado en producción
  (2026-09-22) con una foto real de La CatedRal: se revisó la tabla, se creó
  una categoría nueva y se confirmó; el gerente no ve el botón "Importar" en
  su panel. Detalle general en
  [docs/APARCADO-CARTAS-MULTINEGOCIO.md](APARCADO-CARTAS-MULTINEGOCIO.md)
- ✅ Código QR del restaurante en el panel del gerente (pestaña "QR"): verlo
  en pantalla, hoja imprimible con nombre + QR + texto editable por el gerente
  ("Escanea para ver la carta" por defecto), descargar PNG y SVG, copiar y
  abrir el enlace. El QR se dibuja en el navegador (paquete `qrcode` de npm,
  solo afecta a la etapa del frontend del `Dockerfile`). Apunta a
  `<restaurante>.jurux.app` para todos por igual, La CatedRal incluida
  (`la-catedral.jurux.app`); `cartia.jurux.app` sigue resolviendo, así que
  los QR ya impresos siguen funcionando. Con tests (`tests/test_qr.py`).
  Desplegado y comprobado (2026-09-21): se ve, se escanea con el móvil, se
  descarga y se imprime; la columna `texto_qr` ya está creada en Supabase. La
  impresión falló al principio en teoría (la hoja salía repetida en varias
  páginas, 5 con un panel normal) y se corrigió con una copia solo para papel
- 🔍 Código QR de cada restaurante en el panel superadmin: botón "Ver QR" en
  cada fila de la lista, con la misma hoja (usa el texto que haya guardado
  el gerente), para entregarlo al dar de alta un bar
- 🔍 Métricas básicas, solo en el superadmin (el gerente no ve nada nuevo, y
  el coste no se le enseña nunca): por bar y con selector de 7 o 30 días,
  visitas a la carta, preguntas al chat por idioma, conversaciones
  (aproximadas: pregunta que llega sin historial), preguntas cortadas por el
  tope de gasto, y coste del chat, de las traducciones y por pregunta.
  Contadores por día en hora de España (`visitas_diarias`, `preguntas_diarias`),
  sin IPs ni texto de las preguntas (pueden llevar datos de salud). Las visitas
  excluyen robots y al gerente con sesión abierta; registrar nunca puede romper
  la carta ni el chat. Backend con tests (`tests/test_metricas.py`) y el SQL
  validado con el parser de Postgres. Desplegado: la tarjeta carga y cuenta
  visitas (la del gerente con sesión abierta no cuenta, a propósito). Las
  tablas se crean solas al arrancar. El histórico de visitas y preguntas empieza
  el día del despliegue; el coste sí tiene historia. Falta mirar preguntas y
  costes con uso real
- ✅ Vista de escritorio (a partir de ~860px de ancho, el móvil no cambia)
  en carta pública, panel de gerente y superadmin: categorías como menú
  lateral en la carta y en el panel, tablas sin scroll lateral en el
  superadmin. Probado en producción (2026-09-22) con la ventana ancha
- ✅ Visor de foto navegable: al tocar la foto de un plato se abre a
  pantalla completa con nombre/precio/descripción superpuestos, flechas
  (o deslizar) para pasar al plato siguiente/anterior recorriendo toda la
  carta por categorías, y un aviso breve al cruzar de categoría. Probado
  en producción (2026-09-22): flechas, deslizar y el aviso al cambiar de
  categoría, todo comprobado
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

- Copias de seguridad fuera del servidor → cuando haya clientes. Hoy las copias
  de carta-bar y de `cuentas` están en el mismo disco: sirven contra un borrado
  o un despliegue que rompa datos, no contra perder el servidor. Recomendado:
  Backups de la consola de Hetzner (20 % del precio del servidor, cubre todo).
  Mientras tanto, `scp -r xele@178.104.233.131:/home/xele/copias-carta .` baja
  las de carta-bar a tu PC. Detalle en
  [docs/COPIAS-DE-SEGURIDAD.md](COPIAS-DE-SEGURIDAD.md)
- Editar a mano una traducción desde el panel, por si el modelo se equivoca en
  un plato → hoy solo se corrige cambiando el texto en español o rehaciendo la
  traducción
- Poner la palabra española entre paréntesis en las descripciones traducidas
  (p. ej. "iberischer Schinken (jamón ibérico)") → propuesto el 2026-09-21; el
  restaurante prefiere "en principio así" (solo el nombre queda en español)
- Que `--forzar` guarde plato a plato: hoy solo guarda al terminar cada idioma,
  y un Ctrl+C a mitad pierde esa pasada (y el gasto de esas llamadas no se anota)
- "Langostino" sale como *langoustine* en francés (no es exacto: son gambas);
  mismo alérgeno, así que es solo cosmético → corregirlo si vuelve a molestar
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
- Plantilla de etiqueta QR con diseño (ilustración, logo, "Scan Me", tipo
  posavasos) generada desde el propio panel → hoy se hace con Canva u otra
  herramienta externa, subiendo el PNG del QR que ya genera el panel. Solo
  compensa programarlo si hay varios restaurantes dándose de alta a la vez;
  con un cliente no. El NFC (mismo destino que el QR, se programa aparte con
  una app tipo "NFC Tools" sobre una pegatina NTAG213) no necesita ningún
  cambio de código, es un tema físico

## EN PARALELO (días separados)

- Currículum: Módulo 2 y evaluación formal del Módulo 3
