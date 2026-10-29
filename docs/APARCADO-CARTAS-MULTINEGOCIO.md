# Aparcado · Cartas de distintos negocios

**No construir aún.** Se activa cuando llegue un cliente cuya carta no encaje
en el modelo actual (raciones, tamaños, extras, menú del día...), o cuando
meter cartas a mano sea el cuello de botella (2º-3er cliente).

**Regla:** solo se añade una pieza cuando un cliente real la necesite. No
construir extras ni combos por adelantado.

## Idea central

Un solo código para todos los negocios; lo que cambia entre ellos va en
datos (carta, categorías, `config.json`), nunca en código (`if
restaurante_id == "..."` no debería existir nunca).

## Lo que ya es universal (no hace falta tocar)

- Los 14 alérgenos del enum (obligatorios por ley en toda la UE).
- El filtro determinista de alérgenos/dietas.
- Los botones de filtro (se generan desde los datos de cada carta).
- El prompt del LLM (uno solo, genérico; se le inyectan negocio + candidatos).
- La caché por hash de carta (cuando exista) — la clave ya incluiría
  `restaurante_id`.

## Lo que sí cambia entre negocios

| Tipo de negocio | Qué necesita |
|---|---|
| Bar de tapas | Tapa, media ración y ración, con precios distintos |
| Pizzería | Tamaños, añadir ingredientes |
| Japonés / asiático | Nivel de picante, pescado crudo, número de piezas |
| Cafetería / brunch | Horarios (desayunos hasta las 12), cambiar la leche |
| Coctelería | Con o sin alcohol |
| Menú del día | Combos de primero, segundo y postre |

Lo más delicado son los extras que cambian los alérgenos ("leche de avena",
"base sin gluten"): una opción **solo puede añadir alérgenos, nunca
quitarlos**. Al principio, lo seguro es filtrar por el plato base y mostrar
"consulta las opciones al personal" en vez de calcular combinaciones.

## Modelo de datos propuesto (piezas genéricas)

```python
class Variante(BaseModel):
    nombre: str                  # "Tapa", "Ración", "Grande"
    precio: Decimal

class Opcion(BaseModel):
    nombre: str                  # "Leche de avena", "Extra de queso"
    precio_extra: Decimal = Decimal("0")
    alergenos_anade: set[Alergeno] = set()

class GrupoModificadores(BaseModel):
    nombre: str                  # "Tipo de leche", "Extras"
    opciones: list[Opcion]
    min: int = 0
    max: int = 1

class Plato(BaseModel):
    id: str
    nombre: str
    descripcion: str
    categoria_id: str
    alergenos: set[Alergeno]
    trazas: set[Alergeno] = set()
    alergenos_confirmados: bool = False   # clave para el transformador
    variantes: list[Variante]             # precio único = 1 variante
    modificadores: list[GrupoModificadores] = []
    atributos: dict[str, int | bool | str] = {}
    horario_id: str | None = None
    disponible: bool = True

class PasoCombo(BaseModel):
    nombre: str                  # "Primero"
    platos_ids: list[str]
    elegir: int = 1

class Combo(BaseModel):          # menú del día
    nombre: str
    precio: Decimal
    pasos: list[PasoCombo]
```

El Restaurante X seguiría funcionando igual: sus platos serían platos con una
sola variante y sin modificadores.

Los atributos (picante, crudo, alcohol...) no se programan: cada negocio
los declara en su `config.json`, y Pydantic valida los platos contra esa
definición al cargar la carta. Ejemplo:

```json
{
  "tipo_negocio": "japones",
  "atributos": {
    "picante": { "tipo": "escala", "min": 0, "max": 3, "icono": "🌶", "filtrable": true },
    "crudo":   { "tipo": "bool", "etiqueta": { "es": "Pescado crudo", "en": "Raw fish" } }
  },
  "horarios": { "desayuno": { "desde": "08:00", "hasta": "12:00" } }
}
```

El frontend pinta esto de forma genérica: selector si hay varias variantes,
botón de filtro si un atributo es `filtrable`, icono si lo tiene. No se
toca código por cliente.

**Plantillas por tipo de negocio** (`plantillas/bar_tapas.json`,
`pizzeria.json`...): configs de partida con variantes, atributos,
categorías y tono de prompt típicos. Al dar de alta un negocio se copia
una plantilla a `datos/{restaurante_id}/` y el dueño la ajusta.

## El transformador de cartas

Esto es lo que de verdad hace escalable el alta de un cliente nuevo:

```
PDF / foto / Word / web
   │
   ├─ 1. Extracción ──── LLM con visión + structured output
   │                     (usa la plantilla como guía: "esto es un bar de
   │                      tapas, busca tapa/media/ración")
   ├─ 2. Normalización ── ids, precios a Decimal, categorías, unificar nombres
   ├─ 3. Validación ───── Pydantic contra el modelo + atributos del config
   ├─ 4. Borrador ──────  todo con alergenos_confirmados = False
   ├─ 5. Revisión ──────  el restaurante confirma alérgenos en el panel
   └─ 6. Publicar ──────  traducción incremental por hash (ya existe)
```

Reglas importantes:

- Un plato con `alergenos_confirmados = False` **nunca** sale como apto en
  ningún filtro — como mucho, "consulta al personal". El LLM propone, el
  restaurante decide con checkboxes.
- Con cartas largas, extraer por página o por sección — la calidad cae si
  se mete el PDF entero de golpe.
- Es un coste puntual por cliente, cubierto por la cuota de configuración.

## Cómo comprobar que de verdad es genérico

Se creo 3-4 cartas de prueba inventadas (pizzería, japonés, cafetería) dentro
de `datos/`, se realizo  los mismos tests y el mismo conjunto de preguntas de
evaluación por todas. Lo que falle con la pizzería es la parte del código
que tiene el Bar X metida dentro sin darse cuenta. Aproveche para
añadir tests de aislamiento: una petición de un restaurante nunca debe
devolver platos de otro.

## Orden, cuando se active (no ahora)

1. Ajustar el modelo (variantes como lista, atributos, `alergenos_confirmados`)
   y migrar La CatedRal — barato, evita rehacer cosas luego.
2. El transformador — porque meter cartas a mano es el cuello de botella
   real al 2º-3er cliente.
3. Modificadores, combos y horarios, solo cuando un cliente concreto los
   pida — el modelo ya los admite, solo falta pintarlos y filtrarlos.
