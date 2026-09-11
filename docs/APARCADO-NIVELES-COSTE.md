# Aparcado · Reducir coste del chat por niveles

**No construir aún.** Decidir con el coste real medido en Fase 2 (prueba
con La CatedRal).

## Idea central

Dejar de pensar en un chatbot y pensar en una carta que responde
preguntas. El LLM no conversa libremente: solo interviene cuando los
datos y los filtros no pueden resolver la pregunta solos. Cuanto menos
decide el modelo, menos puede equivocarse, y menos cuesta.

Cada pregunta pasa por estos niveles en orden y se queda en el primero
que la resuelve:

```
Pregunta del cliente
   │
   ├─ Nivel 0 · Botones y filtros ─────────── 0 €   (sin LLM)
   │    "Sin gluten", "Vegetariano", categoría, precio
   │
   ├─ Nivel 1 · Preguntas sobre un plato ──── ~0 €   (sin LLM generativo)
   │    "¿Qué lleva el salmorejo?" "¿El pulpo tiene gluten?"
   │    → respuesta con plantilla desde los datos del plato
   │
   ├─ Nivel 2 · Caché ─────────────────────── 0 €
   │    Misma pregunta + mismas restricciones + mismo idioma
   │
   └─ Nivel 3 · LLM ───────────────────────── lo único que cuesta
        "¿Qué me recomiendas para compartir entre 4?"
        → búsqueda + filtro → 5 platos → respuesta corta en JSON
```

- **Nivel 0** — el filtro determinista ya existe (`filtrar_por_restricciones_cliente`).
  Solo falta ponerlo como botones visibles en la carta.
- **Nivel 1** — detectar el plato mencionado (nombre aproximado o los
  embeddings que ya existen) y qué se pregunta (ingredientes, alérgenos,
  precio), y responder con plantilla traducida a los 4 idiomas: "El
  salmorejo contiene: gluten, huevo". Gratis, instantáneo, exacto.
- **Nivel 2** — clave de caché = pregunta normalizada + restricciones +
  idioma + hash de la carta (el sistema de hash ya existe, para las
  traducciones). Si la carta cambia, la caché se invalida sola.
- **Nivel 3** — solo aquí se llama al modelo, y de forma acotada (ver
  abajo).

## Cómo acotar el LLM cuando sí se usa

1. **Estado estructurado en vez de historial.** No mandar la conversación
   entera. Guardar `RestriccionesCliente` en la sesión y actualizarlo en
   cada mensaje. Al LLM se le manda ese objeto (pocas decenas de tokens),
   no todos los mensajes anteriores.
2. **Respuesta en JSON, no en texto libre.**
   ```json
   { "platos": ["pulpo_brasa", "croquetas_jamon", "ensalada_mango"],
     "motivo": "Buenos para compartir y sin gluten." }
   ```
   El frontend pinta las tarjetas con los datos de `Plato` (precio,
   alérgenos, foto) — nunca con texto del LLM. 30-50 tokens en vez de 300.
   Si un id no existe en la carta, se descarta: grounding garantizado por
   código.
3. **Fuera de tema → respuesta fija**, sin llamar al modelo generativo.
   Se puede clasificar en la misma llamada barata de structured output
   que ya se usa para extraer restricciones, sin llamada extra.

## Orden sugerido cuando se active

1. Registrar tokens y tipo de pregunta en cada llamada, para saber qué
   niveles merecen la pena (p.ej. si el 60% son preguntas de alérgenos,
   el nivel 1 resuelve casi todo).
2. Botones de filtro en la carta (nivel 0) — lo más rápido, lo que más
   ahorra.
3. Estado estructurado + salida en JSON — baja el coste de cada llamada
   que quede.
4. Caché con el hash de la carta.
5. Plantillas de nivel 1, cuando los registros digan cuáles son las
   preguntas frecuentes.

## Conexión con el currículum (Módulo 3)

Para elegir el modelo más barato con criterio: preparar un conjunto de
30-50 preguntas reales con la respuesta esperada (platos que deberían
salir, platos que nunca deberían salir por alérgenos) y comparar modelos
contra él. Es la evaluación formal del Módulo 3, aplicada a un problema
real.
