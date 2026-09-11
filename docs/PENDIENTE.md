# PENDIENTE · Carta Bar

Leyenda: ✅ hecho y probado · 🔍 hecho, falta verificar · ⬜ pendiente

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
- ✅ Ingredientes de la carta confirmados (reemplazada por la carta oficial de 28 platos)
- ✅ Un plato sin alérgenos confirmados nunca aparece como apto (filtro determinista;
  4 platos tienen alérgenos estimados por falta de descripción de origen, no confirmados
  por el restaurante — pendiente confirmar con ellos)
- ✅ Límite de peticiones por IP/sesión y de longitud del mensaje
- ✅ Tope de gasto diario (el chat pasa a "consulta al personal", la carta sigue)
- ✅ Registro por llamada: pregunta, idioma, tokens, fecha (sin datos personales)
- ✅ Aviso de alérgenos visible en la carta

### Se ve bien (arreglos, no funciones nuevas)
- ⬜ El botón del chat no tapa el último plato
- ⬜ El selector de idioma no muestra "ES ES"
- ⬜ Tarjetas de categoría alineadas
- ⬜ Barra de categorías fija al hacer scroll
- ⬜ Fotos reales de los platos (comprimidas, con carga diferida)
- ⬜ Tocar la foto abre un visor (se cierra con X, tocando fuera y con "atrás")

### Despliegue
- ⬜ Servidor elegido y app funcionando con HTTPS
- ⬜ Claves y conexión a BD en variables de entorno, fuera del código
- ⬜ Modelo de embeddings guardado en el servidor, no descargado al arrancar
- ⬜ Copia de seguridad diaria de datos/
- ⬜ Probado en móvil, con datos móviles, en los 4 idiomas
- ⬜ QR generado

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
- Revisar qué va en BD y qué en ficheros → al empezar el panel
- VeriFactu → al montar la facturación

## EN PARALELO (días separados)

- Currículum: Módulo 2 y evaluación formal del Módulo 3
