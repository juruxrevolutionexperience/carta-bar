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
- 🔍 Límite de peticiones por cliente. Detrás de nginx necesita `CONFIAR_PROXY=true`:
  ya está puesto (sin él, todos los comensales compartían cupo). Falta comprobarlo
  con peticiones reales desde dos IPs
- ✅ Tope de gasto diario de 5 USD (el chat pasa a "consulta al personal", la carta sigue)
- 🔍 Registro por llamada: pregunta, idioma, tokens, fecha. Se comprueba con la primera
  pregunta real en producción
- ✅ Aviso de alérgenos visible en la carta
- ✅ Ni la página ni la carta se guardan en caché: un cambio llega al desplegar
- ⬜ Probar el chat en producción con una pregunta real (no se ha hecho: gasta)

### Se ve bien (arreglos, no funciones nuevas)
Los 🔍 están desplegados; se dan por buenos al probarlos en el iPhone.
- 🔍 El botón del chat no tapa el último plato
- 🔍 El selector de idioma no muestra "ES ES"
- 🔍 Tarjetas de categoría alineadas
- 🔍 Barra de categorías fija al hacer scroll
- 🔍 Escala fija en móvil: sin zoom de pellizco ni de doble toque
- 🔍 Safari no amplía la página al tocar el campo del chat
- 🔍 El botón del micrófono se retira si el navegador deniega el permiso
- ⬜ Fotos reales de los platos, comprimidas. El campo `foto` y la carga diferida ya
  están: falta que el restaurante pase las fotos
- 🔍 Tocar la foto abre un visor. Abrir y cerrar con la X, comprobado; tocar fuera y
  "atrás", hechos pero sin probar en el iPhone
- ⬜ Quitar la foto de prueba de la Burger La Catedral

### Despliegue
- ✅ Servidor y app funcionando con HTTPS
- ✅ Claves y conexión a BD en variables de entorno, fuera del código
- 🔍 Modelo de embeddings dentro de la imagen, no se descarga al arrancar. Pero el
  arranque aún consulta Hugging Face (aviso en los logs): falta `HF_HUB_OFFLINE=1`
- ⬜ Desplegar desde GitHub, no copiando desde el portátil
- ⬜ Dockerfile con dependencias y modelo antes que el código (build de ~6 min a ~30 s)
- ⬜ Copia de seguridad diaria de datos/
- ⬜ Probado en móvil, con datos móviles, en los 4 idiomas
- ⬜ QR generado
- ⬜ Parar gym-app, que sigue corriendo sin dominio (sus datos quedan en su volumen)

---

## FASE 2 · Prueba real en La CatedRal (1 semana)

**Terminada cuando:** hay una semana de datos y una conversación con la gerente.

- ⬜ Acordar con la gerente qué indica éxito (menos preguntas a camareros, escaneos, conversaciones/día)
- ⬜ Anotar número de mesas y rotaciones
- ⬜ Calcular coste real por conversación y conversaciones por mesa/día
- ⬜ Fijar el precio con esos números

---

## FASE 3 · Panel de gestión (Bloque 2)

**Se empieza solo si:** la Fase 2 da señal positiva.

### Cimientos, antes de la primera pantalla
- ⬜ La carta pasa de ficheros a la base de datos: cambiar un precio sin redesplegar
- ⬜ Quitar `la-catedral` escrito en el código
- ⬜ Almacenamiento para las fotos
- ⬜ Desplegar sin caída (hoy ~25 s mientras arranca el contenedor)

### Pantallas
- ⬜ Login por restaurante
- ⬜ CRUD de platos con checkboxes de alérgenos y etiquetas
- ⬜ Gestión de categorías
- ⬜ Subida de fotos
- ⬜ Guardar y traducir
- ⬜ Configuración de marca
- ⬜ Métricas básicas

---

## FASE 4 · SaaS multi-cliente (Bloque 3)

**Se empieza cuando:** hay un cliente de pago y llega el 2º o 3º.

- ⬜ Alta automática · facturación · panel superadmin
- ⬜ Aislamiento verificado con tests · subdominios · logs por restaurante

---

## APARCADO (ideas, no tareas)

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
