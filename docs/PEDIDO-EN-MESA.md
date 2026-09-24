# Pedido en Mesa · Especificación y plan de desarrollo

Documento base del sistema de pedido desde la mesa, construido encima de la carta digital
existente.

**Estado: en marcha desde el 2026-09-23, saltando el requisito 3 a propósito.**

Requisito de entrada original:
1. ✅ Carta digital desplegada en producción con HTTPS.
2. ✅ Panel de gestión funcionando (el restaurante edita su carta solo).
3. ⬜ Al menos un restaurante usándolo de verdad durante un mes — **no
   cumplido**. El QR físico en las mesas ni siquiera está puesto todavía
   (previsto para la semana del 2026-09-28); el mes de uso real no ha
   empezado a contar.

**Por qué se empieza igual:** decisión explícita del dueño del producto el
2026-09-23, tras que se lo planteara dos veces en la misma conversación. Sus
palabras: "son reglas que yo pongo, eso significa que si digo que avanzamos
es por algo". No es que el requisito 3 se cumpliera, es que decidió saltarlo
a sabiendas. Queda anotado aquí para que quien retome esto no piense que fue
un despiste.

**Plan revisado con el dueño del producto (2026-09-23):** se repasó en la
conversación, bloque a bloque — el modelo de anfitrión/invitados, el
recorrido completo del cliente (secciones 5.1-5.7) y la parte del
restaurante (alta de mesas, pantalla de cocina/barra, móvil del camarero,
configuración por restaurante, secciones 11-12). Confirmado que coincide con
la idea que tenía: "sí, es que me gusta". Vale como plantilla para empezar;
se irá afinando con el tiempo, no es definitivo.

**Primer bloque — ✅ hecho, probado y desplegado (2026-09-23, commit
`eb8d668`):**
1. ✅ Tablas `mesas`, `sesiones_mesa`, `comensales` (sección 6, con el índice
   único que evita dos sesiones para la misma mesa si dos personas escanean
   a la vez). Se crean solas al arrancar, como el resto del esquema.
2. ✅ Endpoint para entrar por QR (`POST /api/mesa/entrar`): crea sesión y
   hace anfitrión al primero, une como invitado a partir del segundo.
   Maneja la carrera si dos personas escanean a la vez.
3. ✅ Cookie firmada de comensal (`sesion_comensal`, como ya existe para
   gerente/superadmin).
4. ✅ `GET`/`POST /admin/api/mesas` para que el gerente dé de alta mesas.
5. 12 tests nuevos + los 330 de la suite, todos en verde (verificado con
   `mypy`/`pytest` reales, no solo revisado a ojo — Python está bloqueado en
   el PC de trabajo, se verificó en un entorno aparte).

**Todavía sin pantalla:** estos endpoints no tienen ningún botón en el panel
todavía. El gerente de `demo` no puede dar de alta una mesa a golpe de clic
hasta el siguiente bloque.

**Decisión pendiente de confirmar antes de seguir — roles gerente/camarero:**
al plantear cómo probar esto desde el panel, salió que hace falta poder
entrar como "solo camarero" (ve mesas/comandas, no ve Marca/QR/Cuenta) sin
montar cuentas individuales por persona. Propuesta hecha el 2026-09-23: dos
contraseñas por restaurante (una de gerente, una de personal), mismo sitio
de login, panel distinto según cuál se use — pendiente de que el dueño la
confirme antes de tocar el modelo de sesión de admin.

**Segundo bloque — plano del local (2026-09-23): 🔍 hecho en local, falta
desplegar y probar en el móvil.** Decidido con el dueño del producto:
- **Zonas sin límite** (Terraza, Barra, Salón 1...), como pestañas; se crean,
  renombran, reordenan arrastrando y borran. Un bar sin zonas recibe "Sala".
- **Mesas con forma y tamaño:** redonda, cuadrada, rectangular, barril y
  taburete. Se colocan con el dedo sobre una cuadrícula (24 × 18 casillas, con
  imán), se redimensionan con un tirador, se giran de 45° en 45° y se mueven
  de zona. El nombre es libre y el número no es obligatorio ("Barril 1",
  "Terraza 4" o solo "4"); al crear una se propone "Mesa N".
- **Se pueden borrar mesas y zonas.** Sin historial se borran del todo; con
  historial de sesiones se archivan (`activa = false`) y dejan de verse y de
  abrir con su QR. Con clientes sentados no se borra nada (409).
- **La barra es una mesa más.** Los taburetes no llevan QR propio.
- Cada mesa sigue con su QR y "Cambiar el QR de esta mesa"; la vista "Lista de
  QR" queda para imprimirlos todos.

Hecho con tests (`tests/test_plano.py`, 45), SQL verificado contra un Postgres
real y la interfaz probada con un DOM simulado (43 comprobaciones: añadir,
arrastrar, tirador, límites del plano, giro, zonas, borrar). **No** se ha
visto en un navegador real: el tacto en el móvil y el aspecto visual quedan
por confirmar. Los nombres de las tablas nuevas y su RLS se crean solos al
arrancar (`zonas` y las columnas nuevas de `mesas`, en `sql/esquema.sql`).

**Rediseño del panel (2026-09-23), tras ver un TPV de la competencia:** la
primera versión funcionaba pero parecía una maqueta. Decidido con el dueño:
- **Panel oscuro entero.** El fondo es la misma tinta cálida de la carta
  (`#121110`): la carta del cliente sigue clara, el panel es su reverso. Toda
  la paleta vive en `:root` de `frontend/src/admin/estilos.css`.
- **Menú lateral que se despliega** (`MenuLateral.tsx`) en vez de la barra
  inferior de iconos: con mesas, comandas, cocina y camarero no caben cinco
  huecos. En escritorio (≥860px) se queda fijo y desaparece la hamburguesa.
  Las secciones se declaran una sola vez en `secciones.tsx`.
- **Plano legible:** cuadrícula de 12×9 casillas de 56px (antes 24×18 de 32px,
  que en un móvil obligaba a un zoom del 43% y dejaba los nombres en "T…").
- **Texto a tamaño de pantalla:** el plano se escala con `transform: scale()`,
  pero nombre, aforo y tirador se dividen por `--z` (el zoom) para conservar su
  tamaño real. Sin eso, al alejar, el texto se volvía ilegible.
- **Detalle según el sitio** (`detalleVisible` en `planoUtil.ts`): con poco
  espacio en pantalla se oculta el aforo y queda solo el nombre.
- **Herramientas del plano:** zoom, "ver el plano entero" (ajusta a lo ancho y
  a lo alto) y **candado**, para que el gerente pueda mirar sin mover mesas de
  un roce.
- **Ocupación en cada pestaña de zona** (TERRAZA 12, SALÓN 6...).

Probado con un Chromium de verdad (capturas en móvil y escritorio) además de
las 55 comprobaciones de comportamiento. Para volver a sacar capturas, ver
"Cómo probar la interfaz" en [ARQUITECTURA.md](ARQUITECTURA.md).

**Segunda vuelta del plano (2026-09-23), con Turbopos como referencia.** El
dueño pasó una foto de un TPV real y de ahí salió lo que faltaba:
- **Sillas dibujadas alrededor de cada mesa** según su aforo (`SillasMesa.tsx`,
  reparto en `repartirSillas`). Es el cambio que más se nota: de un vistazo se
  ve si una mesa es de 2 o de 6 sin leer ningún número. Una mesa de 2 las pone
  enfrentadas, no en esquina; una alargada, casi todas arriba y abajo.
- **Tres aparatos, no uno encogido** (bloque "TRES APARATOS" en `estilos.css`):
  el reparto de pantalla se decide por el **ancho** y el tamaño de lo que se
  toca por el **tipo de puntero** (`pointer: coarse` = dedo).
  - *Móvil:* plano a lo ancho y los datos de la mesa subiendo desde abajo.
  - *Ordenador:* dos columnas, plano a la izquierda y datos fijos a la derecha.
  - *TPV táctil del bar (todos los bares tienen uno):* lo mismo, con botones,
    pestañas y tirador bastante más grandes.
- **El hueco del panel se reserva siempre** en pantalla ancha: si apareciera
  solo al elegir una mesa, el plano se encogería de golpe. El dueño pidió
  expresamente que se viera "más estable".
- **Las mesas no se montan unas sobre otras:** al arrastrar, si ahí no cabe, la
  mesa se queda en la última posición buena.
- **Barriles y taburetes se llaman solo con el número** ("1", "2"): ocupan una
  casilla y "Mesa 6" no cabía, salía "Mes…".

**Tercera vuelta del plano (2026-09-24): escala Turbopos.** El dueño comparó
lado a lado una captura de Turbopos y la nuestra: "no está desarrollado, quiero
lo mismo que Turbopos a nuestro estilo" (no habla de color ni de interfaz, solo
del panel de mesas). La causa era una decisión de la segunda vuelta: cuadrícula
gorda de 12×9 casillas de 56 px, "a propósito" para que en el móvil se leyera el
nombre. Con eso una mesa ocupaba 1/6 del plano, cinco mesas lo llenaban y había
que hacer scroll. **Regla del dueño: ante cualquier duda de diseño de esta
pantalla, hacerlo como Turbopos.** Cambios:
- **Plano fino de 48×30 unidades** (`COLUMNAS`/`FILAS`/`CELDA = 20` en
  `planoUtil.ts`). Mesa de 4 = 3×3, rectangular 6×3, barril 2×2, taburete 1×1
  (`DISENO_POR_FORMA` en `mesas.py`, mismos valores). Al abrir se ve el local
  entero (zoom que cabe); en móvil se acerca con el zoom (0,2–3, cada pulsación
  ×1,25).
- **Dos modos, ojo y lápiz** (arriba a la izquierda del plano, como Turbopos).
  *Ojo (servicio):* sin paleta, sin cuadrícula, las mesas solo se tocan para ver
  su estado y su QR. *Lápiz (edición):* paleta de formas, guía cada 4 unidades,
  mover, tirador de tamaño, girar, borrar. Un local sin mesas se abre en edición;
  uno montado, en servicio. Sustituye al candado, que ya no existe.
- **Ocupación real:** `Mesa.ocupada` (se calcula al listar: hay una sesión sin
  cerrar) pinta la mesa en rojo con el icono de personas, y la pestaña de zona
  muestra `ocupadas/total` (TERRAZA 5/20). Se refresca cada 8 s sin tocar lo que
  se esté moviendo. **Todavía no se provoca escaneando el QR**: la carta aún no
  lee `?mesa=` ni llama a `/api/mesa/entrar` (siguiente bloque). Para probarlo a
  mano: `curl -X POST https://<bar>.jurux.app/api/mesa/entrar -H "Content-Type:
  application/json" -d '{"token_qr":"<lo que va tras ?mesa= en el enlace del QR>"}'`.
  Ojo: una mesa con sesión abierta no se puede borrar (409) y aún no hay forma de
  cerrarla desde la pantalla; en pruebas, con SQL:
  `UPDATE sesiones_mesa SET estado='cerrada', cerrada_en=now() WHERE restaurante_id='demo' AND estado!='cerrada';`
- **Mesa limpia:** contorno fino y el nombre centrado (sin la etiqueta con
  fondo); el aforo solo en las mesas grandes; en las diminutas nada hasta
  acercar (`detalleVisible`). Sillas finas a escala de la mesa.
- **Migración:** las zonas guardadas en el plano viejo se convierten una sola
  vez al arrancar (`zonas.plano_version`: posiciones ×4 en x y ×3 en y, tamaños
  ×1,5 hacia arriba; ninguna mesa se sale ni se monta sobre otra). Las zonas
  nuevas nacen ya en la versión 2.
- Visto con un Chromium sin cabeza (PC, edición y móvil de 500 px de ancho) con
  datos de prueba. **Sin ver aún en un móvil real ni en el TPV.**
- **Sigue pendiente de Turbopos** (por orden): elementos del local (barra
  rayada, plantas, puertas, baños; necesitan tabla nueva), pellizco para hacer
  zoom en el móvil, líneas guía al alinear, duplicar mesa.

**Cuarta vuelta del plano (2026-09-24), tras probarlo en un móvil y un PC reales:**
- **Tema claro por defecto** con botón sol/luna en la barra superior (`tema.ts`),
  guardado en cada navegador. Toda la paleta, incluida la del plano, vive en
  variables de `:root` / `:root[data-tema="oscuro"]` en `estilos.css`.
- **PC:** sin botones de zoom (el plano se reajusta solo al cambiar la ventana,
  `ResizeObserver`), resumen de la zona en la columna derecha mientras no hay mesa
  elegida, sin texto seleccionable en el plano, **menú escondido** en la pantalla
  de Mesas (clase `plano-completo` en `body`; se abre con la hamburguesa) y plano
  a pantalla completa que cabe sin scroll (`max-height` = alto de pantalla − 310).
- **Móvil:** el zoom flota sobre el plano en vez de ocupar una fila; **tocar una
  mesa al editar solo la elige** (el panel de datos ya no salta y deja arrastrar),
  un segundo toque o el botón "Datos de «…»" sobre el plano abre la hoja. En modo
  ojo, un toque abre los datos como antes.
- Etiqueta en el plano: solo el número si el nombre es "Mesa N" (`etiquetaPlano`);
  el nombre completo sigue en el panel.
- **Pendiente (móvil):** pellizcar para hacer zoom y abrir ya con más zoom.
- **Decisión en curso, elementos del local:** seis tipos propuestos (barra rayada,
  pared, puerta, baños, planta, texto libre), manejados igual que una mesa desde el
  lápiz, solo decoración en modo ojo, tabla nueva `elementos_plano` aparte de las
  mesas. Pendiente de que el dueño confirme los tipos (y si la barra es elemento o
  mesa grande; recomendado: elemento).

**Aviso de migración (segunda vuelta, ya superado por la tercera):** el plano
pasó de 24×18 casillas a 12×9 (más grandes).
Una mesa guardada con el plano viejo puede caer fuera del nuevo; al cargar la
pantalla se trae dentro y se guarda corregida (`corregirSiSeSale`). De paso
salió un fallo real: `limitarTamano` devolvía anchos negativos para una mesa
fuera de la cuadrícula.

**Pendiente de esta línea** (por orden acordado): elementos del local (puerta,
barra, baños, columnas, plantas — necesitan tabla nueva), tema claro/oscuro
elegible, y el resto de mejoras del plano (líneas guía al alinear, duplicar
mesa, tamaño del local por zona).

**Decisión para el paso 3 (juntar mesas en servicio, sin hacer):** lo hace el
camarero durante el servicio y se deshace al cobrar; **no** toca el plano
fijo. Si las dos mesas tienen comandas, **las cuentas se fusionan en una**; si
están vacías, se juntan sin más. Ojo: si las dos tienen comandas de comida o
bebida, hay que decidir cómo se ven los tickets ya enviados (siguen siendo los
de cada mesa original, con la cuenta común).

**Siguiente bloque** (sin empezar): que la carta lea `?mesa=`, llame a
`/api/mesa/entrar` y muestre la barra inferior; después propuestas desde la
carta + panel del anfitrión con el resumen y el total.

**Para probarlo ahora mismo en `demo.jurux.app`:** el restaurante `demo` no
tiene contraseña de gerente establecida. En el servidor:
`docker exec -it carta-bar uv run --no-sync python scripts/establecer_clave_admin.py demo`

Leyenda de tareas: ✅ hecho y probado · 🔍 hecho, falta verificar · ⬜ pendiente

---

## Índice

1. [Qué problema resuelve](#1-qué-problema-resuelve)
2. [Principios de diseño](#2-principios-de-diseño)
3. [Glosario](#3-glosario)
4. [Actores y permisos](#4-actores-y-permisos)
5. [Recorridos completos](#5-recorridos-completos)
6. [Modelo de datos](#6-modelo-de-datos)
7. [Máquinas de estado](#7-máquinas-de-estado)
8. [Reglas de negocio](#8-reglas-de-negocio)
9. [API](#9-api)
10. [Tiempo real](#10-tiempo-real)
11. [Pantallas](#11-pantallas)
12. [Configuración por restaurante](#12-configuración-por-restaurante)
13. [Seguridad y abuso](#13-seguridad-y-abuso)
14. [Casos límite](#14-casos-límite)
15. [Fases de desarrollo](#15-fases-de-desarrollo)
16. [Pruebas](#16-pruebas)
17. [Métricas](#17-métricas)
18. [Decisiones pendientes](#18-decisiones-pendientes)
19. [Fuera de alcance](#19-fuera-de-alcance)

---

## 1. Qué problema resuelve

### El problema observado

En una terraza llena con dos camareros, el tiempo se va en tres cosas: explicar la carta,
tomar notas de pedidos que luego se corrigen, y volver a la mesa a por lo que se olvidó.
Cuando más gente hay es cuando peor se atiende, y es justo cuando más se juega el local.

La carta digital ya resuelve la primera parte: el cliente pregunta y obtiene respuesta sin
esperar a nadie. Este sistema resuelve la segunda y la tercera.

### Qué aporta a cada uno

**Al cliente.** Pide cuando quiere, sin levantar la mano ni esperar. Ve lo que lleva pedido,
lo que cuesta y cómo va su comanda. Si es extranjero, todo en su idioma.

**Al camarero.** Deja de ser un transcriptor. Las comandas llegan escritas, sin letra ni
malentendidos. Puede dedicarse a servir, recomendar y resolver.

**Al dueño.** Menos errores de comanda (que son platos tirados y dinero perdido), más
rotación, y un ticket medio más alto porque el cliente añade cosas sin tener que buscar a
nadie. Y datos que hoy no tiene: qué se pide, a qué hora, desde qué mesa.

### La diferencia con lo que ya existe

Los TPV que ofrecen "pedido desde la mesa" tratan cada móvil como un cliente independiente.
Resultado: seis personas pidiendo a la vez, seis comandas sueltas de la misma mesa, la
cocina descoordinada y una cuenta imposible de cuadrar.

Aquí el modelo es distinto y es el núcleo del producto: **una mesa, un responsable.**

---

## 2. Principios de diseño

Estos principios se leen antes de cada decisión. Si una función los contradice, se descarta
o se rediseña.

**1. Independencia total.**
No se integra con ningún TPV externo. Cocina y barra usan una pantalla web propia. Ningún
tercero puede bloquear el calendario ni exigir permisos. La integración, si algún día llega,
es una función más, nunca un cimiento.

**2. Un responsable por mesa.**
El anfitrión es quien confirma. Los invitados proponen. Esto da un interlocutor, una cuenta
y una responsabilidad clara.

**3. Nunca se bloquea una venta.**
Un bar vive de las rondas. El sistema agrupa, avisa de demora y ordena, pero jamás impide
pedir. Un cliente bloqueado llama al camarero, que es lo que queríamos evitar.

**4. Los límites los pone el restaurante.**
Todos los umbrales (ventana de agrupación, carga máxima, importe máximo) viven en
configuración, no en el código. Un chiringuito y un restaurante de menú no se comportan
igual.

**5. Las personas mandan sobre el sistema.**
El camarero puede anular, corregir, reasignar y cerrar cualquier cosa desde su móvil.
Siempre. Sin excepciones.

**6. El sistema nunca es la única vía.**
Se puede pedir al camarero de toda la vida en cualquier momento. Si se cae el wifi, el
restaurante sigue funcionando.

**7. No se promete lo que no se controla.**
Nada de tiempos estimados ni de puesto en la cola. Estados reales y poco más.

**8. Una fase no se empieza hasta cerrar la anterior.**
Cada fase tiene un criterio de "terminada" verificable. Sin eso, se acumulan cosas a medias.

---

## 3. Glosario

| Término | Definición |
|---|---|
| **Mesa** | Ubicación física del local. Tiene un identificador fijo y un QR o NFC permanente. |
| **Sesión de mesa** | Periodo desde que la mesa se ocupa hasta que se cobra. Todo cuelga de aquí. Una mesa tiene muchas sesiones al día. |
| **Comensal** | Cada persona que escanea y se une a la sesión. |
| **Anfitrión** | El comensal que controla la mesa. Único que puede confirmar pedidos. Es un rol traspasable, no una persona fija. |
| **Invitado** | Comensal sin permiso para confirmar. Puede proponer. |
| **Propuesta** | Plato que un invitado quiere. Vive en el panel del anfitrión. No ha salido a cocina. |
| **Comanda** | Conjunto de líneas confirmado por el anfitrión. Esto sí sale a cocina o barra. |
| **Línea** | Una unidad pedida: plato, cantidad, variante, modificadores, quién la pidió. |
| **Ticket** | La parte de una comanda que va a un destino concreto. |
| **Destino** | Dónde se prepara algo: `cocina` o `barra`. |
| **Ventana de agrupación** | Segundos tras confirmar en los que se puede añadir sin generar comanda nueva. |
| **Freno por carga** | Aviso de demora cuando hay demasiadas comandas pendientes. |

---

## 4. Actores y permisos

| Acción | Invitado | Anfitrión | Camarero | Gerente |
|---|:---:|:---:|:---:|:---:|
| Ver la carta y preguntar al agente | ✓ | ✓ | ✓ | ✓ |
| Proponer un plato | ✓ | ✓ | — | — |
| Confirmar un pedido | — | ✓ | ✓ | ✓ |
| Quitar una propuesta propia | ✓ | ✓ | ✓ | ✓ |
| Quitar cualquier propuesta | — | ✓ | ✓ | ✓ |
| Ver la cuenta de la mesa | ✓ | ✓ | ✓ | ✓ |
| Pedir la cuenta | — | ✓ | — | — |
| Ceder el rol de anfitrión | — | ✓ | ✓ | ✓ |
| Anular una línea ya enviada | — | — | ✓ | ✓ |
| Marcar plato no disponible | — | — | ✓ | ✓ |
| Unir o dividir mesas | — | — | ✓ | ✓ |
| Cerrar la sesión | — | — | ✓ | ✓ |
| Configurar umbrales y destinos | — | — | — | ✓ |

El camarero puede hacer todo lo que puede hacer el anfitrión, y más. Ante cualquier lío, el
personal desatasca.

---

## 5. Recorridos completos

### 5.1 Primera persona que llega a la mesa

1. Escanea el QR de la mesa 7.
2. El sistema comprueba si hay sesión abierta en esa mesa. No la hay, así que crea una.
3. Se le asigna el rol de anfitrión y se le da un identificador de comensal en una cookie.
4. Ve la carta de siempre, más una barra inferior nueva con su pedido.
5. Se le explica en una línea: es el responsable de la mesa y puede ceder el rol.

### 5.2 Los demás se sientan

1. Escanean el mismo QR.
2. Ya hay sesión abierta, así que entran como invitados.
3. Eligen un nombre corto o se les asigna uno ("Comensal 2"), para el reparto de la cuenta.
4. Añaden platos, que van a propuestas.
5. El anfitrión recibe aviso: "Ana quiere unas croquetas".

### 5.3 Confirmar el primer pedido

1. El anfitrión ve todas las propuestas agrupadas, con quién pidió cada cosa y el total.
2. Ajusta: quita, cambia cantidades, añade lo suyo.
3. Pulsa confirmar.
4. Se abre la ventana de agrupación (60-90 s) con cuenta atrás visible y un botón de enviar
   ya.
5. Al cerrarse la ventana se crea la comanda y se divide en tickets por destino.
6. Barra recibe las bebidas; cocina, los platos.
7. Todos ven el estado: recibido.

### 5.4 En barra

1. Suena un aviso y entra un ticket nuevo.
2. El camarero de barra lo marca en preparación.
3. Prepara y marca servido.
4. Si hay alcohol, la línea aparece señalada: hay que confirmarla al servirla, viendo a
   quién se le sirve.

### 5.5 Segunda ronda

1. Cualquiera propone más cosas. No hay bloqueo por tiempo.
2. Si la cocina está saturada, aparece un aviso de demora en los platos de cocina. Las
   bebidas siguen igual, porque van a barra.
3. El anfitrión confirma y se repite el ciclo.

### 5.6 La cuenta

1. Cualquiera abre la cuenta y ve el total y el desglose por persona.
2. El anfitrión pide la cuenta y elige efectivo o tarjeta.
3. Al camarero le llega el aviso con el importe y la forma de pago, y va con el datáfono.
4. Cobra y cierra la sesión desde su móvil.
5. La sesión queda cerrada: nadie puede seguir pidiendo desde esos móviles.

### 5.7 Algo va mal

- **Plato agotado:** el camarero lo marca no disponible y desaparece de la carta al
  instante. Si estaba en una comanda pendiente, avisa a la mesa y la anula.
- **Pedido equivocado:** el camarero anula la línea, que queda registrada como anulada,
  nunca borrada.
- **El anfitrión se va:** cede el rol, o el camarero se lo asigna a otro.

---

## 6. Modelo de datos

### 6.1 Modelos de dominio

```python
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class Destino(str, Enum):
    COCINA = "cocina"
    BARRA = "barra"


class EstadoSesion(str, Enum):
    ABIERTA = "abierta"
    CUENTA_PEDIDA = "cuenta_pedida"
    CERRADA = "cerrada"


class EstadoTicket(str, Enum):
    RECIBIDA = "recibida"
    EN_PREPARACION = "en_preparacion"
    SERVIDA = "servida"
    ANULADA = "anulada"


class EstadoPropuesta(str, Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"


class RolComensal(str, Enum):
    ANFITRION = "anfitrion"
    INVITADO = "invitado"


class Mesa(BaseModel):
    id: str                      # "mesa-07"
    restaurante_id: str
    nombre: str                  # "Terraza 7"
    token_qr: str                # secreto, va en la URL del QR
    activa: bool = True


class Comensal(BaseModel):
    id: str
    sesion_id: str
    nombre: str                  # "Ana" o "Comensal 2"
    rol: RolComensal
    idioma: str = "es"
    creado_en: datetime


class SesionMesa(BaseModel):
    id: str
    restaurante_id: str
    mesa_id: str
    estado: EstadoSesion = EstadoSesion.ABIERTA
    abierta_en: datetime
    cerrada_en: datetime | None = None
    sesion_padre_id: str | None = None   # si se unió a otra mesa
    forma_pago: str | None = None        # "efectivo" | "tarjeta"


class Linea(BaseModel):
    id: str
    plato_id: str
    nombre_plato: str            # copia: un cambio de carta no altera el histórico
    cantidad: int = Field(ge=1)
    precio_unitario: Decimal     # copia, por el mismo motivo
    variante: str | None = None
    modificadores: list[str] = []
    nota: str | None = None      # "sin cebolla"
    pedido_por_id: str           # comensal, para el reparto
    destino: Destino
    requiere_confirmacion: bool = False   # alcohol
    anulada: bool = False


class Propuesta(BaseModel):
    id: str
    sesion_id: str
    linea: Linea
    estado: EstadoPropuesta = EstadoPropuesta.PENDIENTE
    creada_en: datetime


class Comanda(BaseModel):
    id: str
    sesion_id: str
    numero: int                  # correlativo del día, para hablar en voz alta
    lineas: list[Linea]
    confirmada_por_id: str
    confirmada_en: datetime


class Ticket(BaseModel):
    """La parte de una comanda que va a un destino."""
    id: str
    comanda_id: str
    sesion_id: str
    mesa_nombre: str
    destino: Destino
    lineas: list[Linea]
    estado: EstadoTicket = EstadoTicket.RECIBIDA
    creado_en: datetime
    actualizado_en: datetime
```

### 6.2 Por qué se copian nombre y precio

Es la decisión más importante del modelo. `nombre_plato` y `precio_unitario` se guardan en
la línea; no se leen del plato al mostrar la cuenta.

Si el gerente sube el precio del pulpo a media tarde, las comandas de la mañana tienen que
seguir valiendo lo que valían. Referenciar el plato vivo haría que las cuentas cambiaran
solas, y eso es un problema contable y legal, no un detalle.

### 6.3 Tablas

```sql
CREATE TABLE mesas (
    id              TEXT PRIMARY KEY,
    restaurante_id  TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    token_qr        TEXT NOT NULL UNIQUE,
    activa          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE sesiones_mesa (
    id                TEXT PRIMARY KEY,
    restaurante_id    TEXT NOT NULL,
    mesa_id           TEXT NOT NULL REFERENCES mesas(id),
    estado            TEXT NOT NULL,
    abierta_en        TIMESTAMPTZ NOT NULL,
    cerrada_en        TIMESTAMPTZ,
    sesion_padre_id   TEXT REFERENCES sesiones_mesa(id),
    forma_pago        TEXT
);

-- Solo una sesión abierta por mesa. Lo garantiza la base de datos, no el código.
CREATE UNIQUE INDEX una_sesion_abierta_por_mesa
    ON sesiones_mesa (mesa_id)
    WHERE estado != 'cerrada';

CREATE TABLE comensales (
    id          TEXT PRIMARY KEY,
    sesion_id   TEXT NOT NULL REFERENCES sesiones_mesa(id),
    nombre      TEXT NOT NULL,
    rol         TEXT NOT NULL,
    idioma      TEXT NOT NULL DEFAULT 'es',
    creado_en   TIMESTAMPTZ NOT NULL
);

CREATE TABLE comandas (
    id                TEXT PRIMARY KEY,
    sesion_id         TEXT NOT NULL REFERENCES sesiones_mesa(id),
    numero            INTEGER NOT NULL,
    confirmada_por_id TEXT NOT NULL REFERENCES comensales(id),
    confirmada_en     TIMESTAMPTZ NOT NULL
);

CREATE TABLE tickets (
    id              TEXT PRIMARY KEY,
    comanda_id      TEXT NOT NULL REFERENCES comandas(id),
    sesion_id       TEXT NOT NULL REFERENCES sesiones_mesa(id),
    destino         TEXT NOT NULL,
    estado          TEXT NOT NULL,
    creado_en       TIMESTAMPTZ NOT NULL,
    actualizado_en  TIMESTAMPTZ NOT NULL
);

CREATE TABLE lineas (
    id                     TEXT PRIMARY KEY,
    ticket_id              TEXT REFERENCES tickets(id),
    sesion_id              TEXT NOT NULL REFERENCES sesiones_mesa(id),
    plato_id               TEXT NOT NULL,
    nombre_plato           TEXT NOT NULL,
    cantidad               INTEGER NOT NULL CHECK (cantidad >= 1),
    precio_unitario        NUMERIC(10,2) NOT NULL,
    variante               TEXT,
    modificadores          JSONB NOT NULL DEFAULT '[]',
    nota                   TEXT,
    pedido_por_id          TEXT NOT NULL REFERENCES comensales(id),
    destino                TEXT NOT NULL,
    requiere_confirmacion  BOOLEAN NOT NULL DEFAULT FALSE,
    anulada                BOOLEAN NOT NULL DEFAULT FALSE,
    anulada_por            TEXT,
    motivo_anulacion       TEXT
);

CREATE TABLE propuestas (
    id          TEXT PRIMARY KEY,
    sesion_id   TEXT NOT NULL REFERENCES sesiones_mesa(id),
    linea_id    TEXT NOT NULL REFERENCES lineas(id),
    estado      TEXT NOT NULL,
    creada_en   TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_tickets_pendientes
    ON tickets (sesion_id, estado) WHERE estado != 'servida';
CREATE INDEX idx_lineas_sesion ON lineas (sesion_id);
```

Dos detalles que ahorran problemas graves:

**El índice único de sesión abierta.** Si dos personas escanean a la vez, sin él se crean dos
sesiones para la misma mesa y la cuenta se parte en dos. Que lo garantice la base de datos y
no un `if` en Python.

**Nada se borra.** Las líneas anuladas se marcan con `anulada`, `anulada_por` y motivo. Un
plato que desaparece sin rastro es una discusión con el cliente que no se puede resolver.

---

## 7. Máquinas de estado

### Sesión de mesa

```
             escanea el primero
                    │
                    ▼
               [ ABIERTA ] ──── pide la cuenta ───► [ CUENTA_PEDIDA ]
                    │                                      │
                    │                                cobra el camarero
                    │                                      │
                    └──── cierra el camarero ────────► [ CERRADA ]
                                                            │
                                     nadie puede pedir con esa sesión
```

Desde `CUENTA_PEDIDA` se puede volver a `ABIERTA`: alguien pide un chupito de última hora y
el camarero reabre. Hay que preverlo, porque pasa constantemente.

### Ticket

```
   [ RECIBIDA ] ──► [ EN_PREPARACION ] ──► [ SERVIDA ]
        │                   │
        └───────────────────┴──► [ ANULADA ]   (solo camarero, con motivo)
```

No se salta de recibida a servida sin pasar por preparación, salvo que el camarero lo fuerce
(bebidas simples). Una vez servida no se anula: se corrige en la cuenta.

### Propuesta

```
   [ PENDIENTE ] ──► [ ACEPTADA ]   (pasa a formar parte de una comanda)
         │
         └────────► [ RECHAZADA ]   (la quita el anfitrión o quien la propuso)
```

---

## 8. Reglas de negocio

### 8.1 Ventana de agrupación

Al confirmar, no sale nada inmediatamente. Se abre una ventana de N segundos (por defecto
75, configurable entre 0 y 180) durante la cual:

- Se pueden añadir líneas y entran en la misma comanda.
- La mesa ve una cuenta atrás y un botón "enviar ya".
- Al terminar, se crea la comanda y se reparten los tickets.

Sirve para lo típico: se confirma, y dos segundos después alguien dice "ponme otra caña".
Sin la ventana, eso son dos comandas y dos viajes.

Con la ventana a 0, el sistema se comporta como uno normal.

### 8.2 Freno por carga

```python
def hay_demora(sesion, config) -> bool:
    pendientes = contar_tickets_pendientes(
        restaurante_id=sesion.restaurante_id,
        destino=Destino.COCINA,
    )
    return pendientes >= config.umbral_demora_cocina
```

Cuando se supera el umbral, los platos de cocina muestran un aviso ("La cocina va con
retraso, este plato puede tardar más de lo normal"). **No se bloquea nada.** Las bebidas no
se ven afectadas, porque van a barra.

El umbral lo fija el restaurante. El valor por defecto (por ejemplo 12) es un punto de
partida que hay que ajustar viendo un servicio real.

Mejora para cuando haya histórico: usar el tiempo medio de los últimos tickets servidos en
vez del número de pendientes.

### 8.3 Alcohol

Toda línea de un plato con `contiene_alcohol` lleva `requiere_confirmacion = True`.

- Se pide normalmente desde la app.
- El ticket de barra la muestra destacada.
- El camarero la confirma al servirla, viendo a quién.
- Si no procede, la anula con un toque.

Esto no es una traba: es lo que permite vender el sistema a un dueño sin que le entre el
pánico. Servir alcohol a un menor tiene consecuencias serias para el local, y un sistema que
lo ignora es un sistema que no puede instalar.

### 8.4 Importe máximo por comanda

Umbral configurable (por defecto 150 €). Por encima, la comanda entra igual pero marcada
para que el camarero la valide antes de que cocina empiece. Protege de un dedo torpe y de
una broma.

### 8.5 Reparto de la cuenta

Cada línea sabe quién la pidió, así que el reparto sale solo:

```python
def repartir(sesion) -> dict[str, Decimal]:
    totales: dict[str, Decimal] = {}
    for linea in lineas_no_anuladas(sesion):
        importe = linea.precio_unitario * linea.cantidad
        totales[linea.pedido_por_id] = totales.get(linea.pedido_por_id, Decimal("0")) + importe
    return totales
```

Lo compartido (una paella para cuatro) necesita marcarse como compartido y repartirse entre
los comensales indicados. Es la parte más fácil de subestimar: decidirlo en la Fase C, no
improvisarlo.

---

## 9. API

Todo bajo `/api/mesa`. Autenticación por cookie de sesión de comensal, firmada.

### Sesión

```
POST   /api/mesa/entrar
       body: { token_qr, nombre?, idioma? }
       → crea o se une a la sesión. Devuelve sesion_id, comensal_id, rol.
       → asigna cookie firmada.

GET    /api/mesa/estado
       → sesión completa: comensales, propuestas, comandas, estados, total.

POST   /api/mesa/ceder-anfitrion
       body: { comensal_id }
       → solo anfitrión o camarero.
```

### Pedido

```
POST   /api/mesa/propuestas
       body: { plato_id, cantidad, variante?, modificadores?, nota? }
       → crea propuesta pendiente.

DELETE /api/mesa/propuestas/{id}
       → quien la creó, o el anfitrión.

POST   /api/mesa/confirmar
       → solo anfitrión. Abre la ventana de agrupación.
       → devuelve { comanda_id, cierra_en }

POST   /api/mesa/confirmar/{comanda_id}/enviar-ya
       → cierra la ventana antes de tiempo.
```

### Cuenta

```
GET    /api/mesa/cuenta
       → total, desglose por comensal, líneas anuladas aparte.

POST   /api/mesa/cuenta/pedir
       body: { forma_pago }
       → pasa la sesión a CUENTA_PEDIDA y avisa al personal.
```

### Personal (requiere login de restaurante)

```
GET    /api/personal/tickets?destino=cocina&estado=pendientes
POST   /api/personal/tickets/{id}/estado     body: { estado }
POST   /api/personal/lineas/{id}/anular      body: { motivo }
POST   /api/personal/platos/{id}/disponible  body: { disponible }
POST   /api/personal/sesiones/{id}/cerrar
POST   /api/personal/sesiones/unir           body: { sesion_a, sesion_b }
GET    /api/personal/eventos                 (SSE)
```

### Idempotencia

`POST /api/mesa/confirmar` y los cambios de estado aceptan una cabecera `Idempotency-Key`.
Sin esto, un doble toque en un móvil lento genera dos comandas. Pasa constantemente y es de
las cosas que más enfadan al personal.

---

## 10. Tiempo real

| Opción | Ventaja | Inconveniente |
|---|---|---|
| Recarga periódica cada 3-5 s | Trivial, sobrevive a cualquier corte | Consumo, algo de retraso |
| **SSE (Server-Sent Events)** | Simple, reconexión automática del navegador, va sobre HTTP normal | Solo servidor → cliente |
| WebSocket | Bidireccional | Más infraestructura, reconexión a mano |

**Recomendación: SSE.** Todo lo que necesita empuje va en una dirección (el servidor avisa de
un ticket nuevo o de un cambio de estado). Las acciones del cliente son POST normales.
FastAPI lo sirve sin dependencias extra y el navegador reconecta solo.

La pantalla de cocina debe además:

- Guardar los tickets en memoria del navegador para sobrevivir a un corte breve.
- Mostrar bien visible cuándo perdió la conexión. Una pantalla congelada que parece viva es
  peor que una que avisa.
- Recuperar el estado completo al reconectar, no solo los eventos perdidos.

---

## 11. Pantallas

### 11.1 Cliente (sobre la carta actual)

**Barra inferior fija.** Número de líneas y total. Al tocar, se abre el pedido. Ojo con no
tapar el último plato ni el botón del chat.

**Panel de pedido.** Propuestas agrupadas por persona, con quién pidió qué. Si eres
anfitrión, botón de confirmar. Si eres invitado, un texto claro: "Ana confirma los pedidos
de la mesa".

**Cuenta atrás de la ventana.** Discreta pero visible, con "enviar ya".

**Estado de comandas.** Lista sencilla: "Comanda 3 · en preparación". Sin número de cola, sin
minutos.

**Cuenta.** Total, desglose por persona, y botón de pedir la cuenta solo para el anfitrión.

### 11.2 Pantalla de cocina y barra

Es la pantalla que más importa y la que más se descuida. Se usa de pie, con prisa, con las
manos sucias y a dos metros de distancia.

- Tarjetas grandes, una por ticket, en columnas por estado.
- Tipografía grande. Se lee desde lejos.
- Color por antigüedad: normal, ámbar a partir de X minutos, rojo pasado Y.
- Aviso sonoro al entrar un ticket, con opción de silenciar.
- Botones enormes. Nada de menús ni de gestos finos.
- Mesa y número de comanda en grande, arriba.
- Notas y modificadores destacados, nunca en letra pequeña: ahí están las alergias.
- Alcohol con un distintivo claro.

### 11.3 Móvil del camarero

- Lista de mesas con su estado y su total.
- Mesas que han pedido la cuenta, arriba del todo.
- Anular línea con motivo, en dos toques.
- Marcar plato agotado.
- Reasignar anfitrión, unir mesas, cerrar sesión.

---

## 12. Configuración por restaurante

```json
{
  "pedido_en_mesa": {
    "activo": true,
    "ventana_agrupacion_segundos": 75,
    "umbral_demora_cocina": 12,
    "umbral_demora_barra": 20,
    "importe_maximo_comanda": 150.00,
    "requiere_confirmacion_alcohol": true,
    "permitir_notas_libres": true,
    "longitud_maxima_nota": 120,
    "caducidad_sesion_horas": 4,
    "destinos_por_categoria": {
      "bebidas": "barra",
      "cafes": "barra",
      "entrantes": "cocina",
      "principales": "cocina",
      "postres": "cocina"
    },
    "horario_pedidos": { "desde": "12:00", "hasta": "23:30" }
  }
}
```

El horario evita que alguien pida a las tres de la mañana desde la calle con un QR
fotografiado.

---

## 13. Seguridad y abuso

| Riesgo | Mitigación |
|---|---|
| Alguien fotografía el QR y pide desde casa | Sesión ligada a la mesa, caducidad por inactividad, horario de pedidos y cierre al cobrar |
| Un gracioso pide 40 platos | Importe máximo por comanda y validación del camarero por encima del umbral |
| Un invitado se hace pasar por anfitrión | El rol vive en el servidor, nunca en el cliente |
| Un comensal ve otra mesa | Todo endpoint filtra por la sesión de la cookie, nunca por un id que venga del cliente |
| Un restaurante ve datos de otro | Todo filtrado por `restaurante_id`, con test explícito |
| Manipular precios desde el navegador | El precio se toma siempre del servidor. El cliente solo manda `plato_id` y cantidad |
| Spam de propuestas | Límite de peticiones por comensal |
| Token de QR filtrado | Se puede regenerar por mesa desde el panel |

**Datos personales.** El nombre del comensal es un apodo para la mesa. No se piden ni
teléfono ni correo. Al cerrar la sesión, los nombres se pueden anonimizar conservando solo
los datos agregados del pedido. Cuanto menos se guarde, menos obligaciones de RGPD y menos
que proteger.

---

## 14. Casos límite

| Caso | Solución | Fase |
|---|---|---|
| Dos personas escanean a la vez | El índice único de la base de datos decide; el segundo entra como invitado | A |
| El anfitrión se va | Cesión del rol, o reasignación por el camarero | A |
| Comensal sin batería | Otro puede seguir; siempre se puede pedir al camarero | A |
| Sesión olvidada abierta toda la noche | Caducidad por inactividad + cierre al final del horario | A |
| Dos mesas se juntan | El camarero une sesiones; una pasa a ser hija de la otra | B |
| Una mesa se divide | Se cierra y se abren dos, repartiendo líneas | C |
| Se cae el wifi en el local | La pantalla guarda en local, avisa de la desconexión y recupera al volver | B |
| Se cae el servidor | El restaurante trabaja como siempre; nada depende de la app | — |
| Plato agotado ya pedido | El camarero anula y avisa a la mesa | B |
| Cliente cambia de idioma | Cada comensal tiene el suyo; el ticket sale siempre en el idioma del local | A |
| Nota con una alergia | Se destaca en el ticket, y se recuerda confirmarlo verbalmente | B |
| Doble toque en confirmar | Clave de idempotencia | B |
| Mesa que no paga | La sesión queda abierta hasta que el camarero la cierra, y queda registrada | C |

**Sobre las alergias escritas en una nota:** es el punto más delicado de todo el sistema. Una
nota de texto libre no sustituye a la conversación con el camarero. La app debe mostrar un
aviso al cliente ("comunícaselo también al personal") y destacar la nota en el ticket, pero
la responsabilidad sigue siendo del restaurante y así debe quedar reflejado.

---

## 15. Fases de desarrollo

### FASE A · Precomanda

Sin cocina, sin pagos. Valida el modelo de anfitrión con el mínimo trabajo.

- ⬜ Tabla de mesas y generación de QR/NFC por mesa
- ⬜ Entrar por QR: crear sesión o unirse
- ⬜ Asignación de rol y cookie firmada de comensal
- ⬜ Índice único de sesión abierta por mesa
- ⬜ Nombre de comensal
- ⬜ Añadir propuestas desde la carta
- ⬜ Panel del anfitrión con las propuestas agrupadas
- ⬜ Aceptar y rechazar propuestas
- ⬜ Resumen de mesa con total estimado
- ⬜ Cada comensal lo ve en su idioma
- ⬜ Caducidad por inactividad y cierre manual
- ⬜ Cesión del rol de anfitrión

**Terminada cuando:** una mesa real de cuatro o más personas usa el resumen para pedir al
camarero, y el camarero confirma que le ha servido de algo.

Este es el punto de decisión de todo el proyecto. Si aquí la gente no usa el modelo de
anfitrión, las fases B, C y D no se construyen.

---

### FASE B · Comanda real

- ⬜ Comandas, tickets y división por destino
- ⬜ Ventana de agrupación
- ⬜ Pantalla de cocina y barra, con SSE
- ⬜ Aviso sonoro y color por antigüedad
- ⬜ Cambios de estado
- ⬜ Freno por carga
- ⬜ Marcado y confirmación de alcohol
- ⬜ Importe máximo por comanda
- ⬜ Móvil del camarero: anular, agotar, cerrar
- ⬜ Idempotencia en confirmar y en cambios de estado
- ⬜ Reconexión y recuperación de estado
- ⬜ Numeración correlativa diaria de comandas

**Terminada cuando:** un servicio completo sale sin que nadie mire el papel, y el camarero
prefiere el sistema al cuaderno.

---

### FASE C · Cuenta

- ⬜ Cuenta en tiempo real
- ⬜ Reparto por comensal
- ⬜ Platos compartidos
- ⬜ Pedir la cuenta con forma de pago
- ⬜ Cierre de sesión al cobrar
- ⬜ Reapertura de sesión
- ⬜ Unir y dividir mesas
- ⬜ Histórico de sesiones cerradas

**Terminada cuando:** el camarero llega a la mesa sabiendo el importe y la forma de pago sin
preguntar.

---

### FASE D · Pago desde el móvil

Solo si un cliente de pago lo exige. **Decidir antes quién emite el ticket.**

- ⬜ Proveedor de pagos, con el dinero yendo del cliente al restaurante
- ⬜ Pago parcial y propina
- ⬜ Devoluciones
- ⬜ Conciliación con la cuenta
- ⬜ Emisión de factura simplificada y cumplimiento de VeriFactu

Esta fase multiplica el trabajo y añade obligaciones legales. Todo lo anterior aporta valor
sin ella.

---

## 16. Pruebas

Las que de verdad evitan desastres, no relleno:

```
test_dos_escaneos_simultaneos_crean_una_sola_sesion
test_segundo_comensal_entra_como_invitado
test_invitado_no_puede_confirmar
test_precio_se_toma_del_servidor_no_del_cliente
test_precio_en_linea_no_cambia_si_cambia_la_carta
test_comanda_mixta_se_divide_en_dos_tickets
test_ventana_agrupacion_mete_lineas_en_la_misma_comanda
test_doble_confirmacion_con_misma_clave_crea_una_comanda
test_freno_por_carga_avisa_pero_no_bloquea
test_alcohol_marca_requiere_confirmacion
test_linea_anulada_no_cuenta_en_el_total
test_sesion_cerrada_rechaza_nuevos_pedidos
test_comensal_no_ve_otra_sesion
test_restaurante_no_ve_datos_de_otro_restaurante
test_sesion_caduca_por_inactividad
test_reparto_suma_exactamente_el_total
```

Las dos de aislamiento (comensal y restaurante) son obligatorias antes de tocar producción.

---

## 17. Métricas

**Para el restaurante:** comandas por servicio, ticket medio con y sin el sistema, platos más
pedidos por franja horaria, tiempo medio de ticket por destino, líneas anuladas y su motivo,
porcentaje de mesas que usan el sistema.

**Para ti:** sesiones por restaurante, tasa de escaneo por mesa, invitados por sesión,
porcentaje de propuestas aceptadas, errores y desconexiones de la pantalla.

El dato que mejor vende es el ticket medio. Si sube, la conversación con el dueño deja de ser
sobre el precio.

---

## 18. Decisiones pendientes

Cerrarlas antes de empezar la fase indicada.

- ⬜ **(B)** ¿SSE o recarga periódica? Recomendado SSE.
- ⬜ **(B)** ¿La cocina usa tablet, pantalla fija o también impresora de tickets?
- ⬜ **(B)** ¿Qué pasa con una comanda si la pantalla está apagada?
- ⬜ **(A)** ¿Los datos van en las mismas tablas que la carta o en un esquema aparte?
- ⬜ **(C)** ¿Cómo se reparten los platos compartidos?
- ⬜ **(D)** ¿Quién emite el ticket fiscal?
- ⬜ **(—)** ¿Esto se cobra aparte o va incluido en la cuota mensual?
- ⬜ **(—)** ¿Se ofrece a restaurantes que ya tienen TPV con pedido propio?

---

## 19. Fuera de alcance

No entran. Si alguien los pide, se apuntan aquí sin empezarlos:

- Integración con TPV externos
- 3D y vídeo 360 de platos
- Reservas de mesa
- Reseñas
- Fidelización, cupones y promociones
- Reparto a domicilio y recogida
- Gestión de personal y turnos
- Escandallos e inventario

**Sobre el pulido visual:** importa, y mucho, pero se hace con lo que ya hay (animaciones
suaves, transiciones, tipografía y fotos reales). No requiere un motor 3D y va **después** de
tener las comandas funcionando.

---

## Recordatorio final

Este documento es un plan, no una lista de tareas para mañana. Se empezó el 2026-09-23 saltando
a propósito el requisito 3 (ver arriba) — eso ya está decidido y no hay que replanteárselo cada
vez. Lo que sí sigue en pie: **una fase no se empieza hasta cerrar la anterior** (principio 8).
Antes de tocar la Fase B, comprobar que la Fase A cumple de verdad su "Terminada cuando".
