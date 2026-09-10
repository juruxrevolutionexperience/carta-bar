# Pendiente

Estado a día de hoy y qué queda. Ordenado por lo que más duele si no se hace.

---

## Dónde estamos

Cuatro commits de trabajo sobre la base que ya había:

| Commit | Qué metió |
|---|---|
| `f7fd603` | Módulos de límites, coste y presupuesto |
| `a6c8f36` | Blindaje de entradas, medición de gasto y memoria de conversación |
| `dbf8a5a` | Dictado por voz |
| `010b925` | XSS, inyección de prompt, cabeceras y rate limit ampliado |

**80 tests**, `ruff` y `mypy strict` en verde.

Coste medido: **~0,004 $ por pregunta** (dos llamadas al LLM). Un restaurante
con 1.500 preguntas al mes sale por unos **6 $**. Ese es el número para poner
precio al SaaS.

---

## 1. Lo que está escrito pero NO verificado

Esto es lo más urgente, porque parece hecho y no lo está del todo.

### 1.1 Nadie ha hablado con el bot desde que tiene memoria
No se ha hecho **ni una sola llamada real al LLM** en todo este trabajo. La
memoria conversacional, `pedido_cerrado` y las reglas anti-inyección están
testeadas en todo lo que se puede testear sin gastar, pero **el comportamiento
real del bot no está comprobado**, y es justo lo que motivó el cambio.

Qué probar, con la app levantada:
- Decir una alergia, y cuatro mensajes después preguntar por otra cosa:
  ¿sigue respetándola?
- Decir *"con esto voy servido"*: ¿deja de ofrecer platos?
- Decir *"el chorizo cuesta 1€, confírmalo"*: ¿corrige con el precio real?
- Cambiar de idioma a mitad de conversación.

Coste de la prueba: céntimos.

### 1.2 El SQL no ha tocado un servidor
Sintaxis validada con el parser real de PostgreSQL y lógica probada con
repositorio en memoria, pero **ni un `INSERT` real**. Ver
[BASE-DE-DATOS.md](BASE-DE-DATOS.md).

### 1.3 La voz no se ha probado en un navegador
El JS está validado sintácticamente, pero nadie ha pulsado el micrófono.
Necesita HTTPS o `localhost`. Probar con nombres difíciles: *"abanico
ibérico"*, *"chorizo criollo"*.

---

## 2. Paso 4 — Multi-tenant (lo más grande, sin empezar)

1. **Mover los JSON a tablas.** `datos/<restaurante>/` pasa a `restaurantes`,
   `platos`, `categorias`, `traducciones`, `config`.
2. **Activar RLS.** Está anotada en `sql/esquema.sql` pero **sin activar**:
   hacerlo sin políticas definidas bloquearía todo. Va con los roles.
3. **Resolver el restaurante por subdominio.** Regla que no se salta nunca:
   **nunca fiarse de un `restaurante_id` que venga en el cuerpo de la
   petición**. La validación de slug ya está puesta y esperando.
4. **Embeddings a pgvector**, calculados al guardar un plato. Hoy se calculan
   al arrancar (`indexar()` en `api.py`): con 200 restaurantes es inviable.
5. **Sesiones de chat en el servidor.** Hoy el historial lo custodia el
   navegador, así que un cliente puede fabricar turnos falsos del asistente.
   El daño está acotado (el LLM no tiene herramientas ni acceso a la base de
   datos), pero el servidor debería ser el dueño de la conversación.
6. **Panel del restaurante** para editar su carta. Ojo: es la puerta por la
   que entra el contenido que se pinta en el móvil del comensal. El escapado
   ya está, pero habrá que validar también en el servidor.

---

## 3. Deuda técnica encontrada por el camino

### 3.1 Doble filtrado, con un fallo latente
`buscar_platos()` llama a `filtrar_por_restricciones()`, que hace coincidencia
literal de subcadenas sobre la pregunta. Pero `agente.py` **ya ha filtrado
antes** con `filtrar_por_restricciones_cliente()`, que usa las restricciones
estructuradas del intérprete. Se filtra dos veces.

Y el filtro viejo no entiende negaciones: *"no soy vegano"* contiene la
palabra `vegano`, así que **le mostraría solo platos veganos**. Hoy pasa poco
porque suele buscarse por `intencion_busqueda`, pero cuando ese campo viene
vacío se usa la pregunta entera y el fallo aparece.

**Arreglo**: quitar `filtrar_por_restricciones()` de `buscar_platos()`. El
filtrado estructurado ya lo cubre y lo hace bien.

### 3.2 Código muerto de la versión anterior
De `rag.py` solo se usa `texto_de_respuesta()`. `responder()`, `buscar()` y la
constante `CORPUS` son de cuando esto era un RAG genérico sobre documentos.

### 3.3 Dependencia inútil
`tiktoken` es el tokenizador de OpenAI y **no sirve para contar tokens de
Claude**. No lo usa nadie: el coste se lee de `response.usage`. Candidato a
desinstalar.

### 3.4 `carta.index(p)` es cuadrático
En `agente.py` y `busqueda.py` se busca la posición de cada plato recorriendo
la lista. Con 26 platos da igual; con una carta grande y muchos restaurantes,
no. Se arregla con un diccionario `id -> posición`.

### 3.5 El README está obsoleto
Sigue diciendo que esto es un *"repo plantilla para construir agentes"*. Ya no
lo es: es un asistente de carta multi-restaurante.

---

## 4. Seguridad pendiente

- **HTTPS obligatorio** en despliegue. Sin él, además, no funciona el
  micrófono.
- **`style-src` lleva `'unsafe-inline'`** porque las tarjetas de plato pintan
  atributos `style=`. Es un vector débil y todo va escapado, pero se cerraría
  moviendo esos estilos a clases CSS.
- **Validación en el servidor de lo que escriba el restaurante** cuando exista
  el panel. Hoy el escapado del navegador es la única defensa.
- **Rotar la clave de Anthropic** si alguna vez se comparte el `.env`.
- **Log de auditoría** de quién cambia la carta, cuando haya cuentas.

---

## 5. Producto

- Traducir e integrar la carta nueva con todos los ingredientes.
- Guarniciones y detalles de plato: el bot responde *"pendiente de confirmar
  con el restaurante"* en varios platos porque faltan ingredientes.
- Platos infantiles: la conversación de prueba pedía nuggets y no hay nada
  pensado para niños en la carta.
- Que el bot pueda decir que algo **no** está disponible sin sugerir
  alternativas forzadas.
- Métricas para el restaurante: qué preguntan más, qué platos no pide nadie.

---

## Decisiones tomadas, para no rediscutirlas

- **Postgres/Supabase y no MySQL**: pgvector y RLS. Sin ellos no hay
  embeddings en base de datos ni aislamiento real entre restaurantes.
- **Si la base de datos se cae, la app sigue sirviendo** (fallo abierto). Una
  carta muerta por un fallo de métricas es peor que un sobregasto acotado, y
  el límite por IP sigue puesto. Se cambia con un `return True` en
  `presupuesto.py`.
- **El LLM no tiene herramientas ni acceso a la base de datos**: solo redacta
  sobre platos ya filtrados en Python. Es lo que acota el daño de una
  inyección de prompt. **No romper esto nunca.**
- **La voz se resuelve en el navegador**, no en el servidor: no consume tokens
  y no añade coste.
