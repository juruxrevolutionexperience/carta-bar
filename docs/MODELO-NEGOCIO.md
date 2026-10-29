# Modelo de negocio · Carta Bar

Borrador para decidir, no compromiso. Todo número marcado **(supuesto)** hay
que confirmarlo antes de cobrar nada. Los precios de proveedores cambian: revisar
sus webs en el momento de decidir.

## 1. Qué se vende

Un sistema para bares y restaurantes que incluye:
- Carta digital con QR y en varios idiomas.
- Pedido en mesa desde el móvil del cliente, o tomado por el camarero.
- Cocina y barra: comandas impresas en su impresora, con estados.
- Panel de Servicio y plano de mesas.
- Cierre de cuenta y resumen impreso (no es factura).
- Chat de preguntas de los clientes con respuestas sobre la carta.

Fuera de alcance por ahora: cobro con tarjeta desde la app, pagos, stock,
proveedores (ver `docs/PENDIENTE.md`, sección APARCADO).

## 2. Costes fijos mensuales (todos los bares juntos)

| Concepto | Coste | Nota |
|---|---|---|
| Servidor compartido (Hetzner) | ~8 €/mes | Dato del usuario, verificar plan |
| Base de datos en el mismo servidor | 0 € | Frente a Supabase, a decidir |
| Copias de seguridad externas | ~3-5 €/mes | **(supuesto)** |
| Dominio jurux.app | ~1 €/mes | **(supuesto)**, ~12 €/año |
| Gestoría | ? €/mes | Pedir presupuesto a 2-3 |

Coste fijo aproximado: **15-20 €/mes + gestoría**, con el servidor sirviendo a
todos los bares.

## 3. Costes variables por bar

- **IA (Anthropic):** chat de clientes (modelo pequeño) y traducciones de la
  carta (se pagan una vez por plato). **(supuesto)** Se mide con los primeros
  bares reales. Cada bar tiene tope en `presupuesto.py`.
- **Comisión de cobro recurrente:** según el proveedor de pagos. **(supuesto)**
  Verificar en la web del proveedor.
- **Hardware:** impresoras, aparato dedicado para imprimir y, si hace falta,
  adaptador de red (15-20 €). Lo paga el bar o se incluye en la cuota de alta.
- **Tu tiempo de alta:** 2-4 h por bar según el usuario, probablemente más la
  primera vez. Cuenta en horas, no en euros, hasta tener plantilla.

## 4. Cuota de alta y mensualidad (propuesta, a decidir)

- **Alta por bar:** cubre el montaje (carta, plano, QR, impresoras, formación).
  Punto de partida: 100-300 € **(propuesta)**.
- **Mensualidad:** un único plan con todo incluido. Punto de partida: 40-60 €/mes
  **(propuesta)**, a validar con los primeros bares.

## 5. Escenarios (mensualidad 50 €, alta 150 €, supuestos los de arriba)

Coste fijo: 15 € servidor+dominio+copias + gestoría (supuesto 30 €/mes) = **~45 €/mes**.

| Bares | Ingreso mensual | Coste fijo | Margen mensual aprox. |
|---|---|---|---|
| 1 | 50 € | ~45 € | ~5 € |
| 5 | 250 € | ~45 € + IA y tiempo | ~200 € antes de tu tiempo |
| 10 | 500 € | ~45 € + IA y tiempo | ~450 € antes de tu tiempo |

Con 1 bar apenas cubres costes: el negocio empieza a tener sentido con varios
bares, no con uno. Tu tiempo de alta es el coste que más pesa al principio.

## 6. Costes que no son de servidor pero hay que contar

- Gestoría: alta de la actividad, facturas con IVA, declaraciones, contratos.
- VeriFactu: la factura que emitís a cada bar tiene que cumplirlo. Calendario
  vigente según RD-ley 15/2025: sociedades desde 1 ene 2027, autónomos desde
  1 jul 2027 (verificar).
- Protección de datos: contrato de encargado del tratamiento con cada bar y lista
  de proveedores que procesan datos (Hetzner, Anthropic, y Supabase si se queda).
  Hay datos de salud (alergias): protección reforzada. Revisar con abogado o
  gestoría.
- Seguro de responsabilidad civil profesional: **(a valorar)**.

##  7. Lo que falta medir

- Consumo real de IA por bar (los primeros 2-3 bares).
- Tiempo real de alta por bar (anotarlo en el primero).
- Memoria del servidor con el modelo de embeddings cargado.
- Respuestas de la gestoría sobre sociedad o autónomo y VeriFactu.
