# Plan de cobro por suscripción · Carta Bar

Estado: **plan, sin código**. Decidir antes de tocar nada: proveedor (Stripe o
GoCardless), cuota, y respuestas de la gestoría (sección 7).

## 1. Idea general

El dinero y los datos de tarjeta o IBAN los guarda el proveedor. Carta Bar solo
guarda quién está al día y qué restaurante tiene acceso.

## 2. Flujo para el bar (paso a paso)

1. El bar entra en la landing y pulsa "Empezar".
2. Rellena: nombre del bar, email del gerente, CIF o NIF, y el subdominio que
   quiere (`micasa.jurux.app`).
3. Carta Bar crea el restaurante en estado `pendiente_pago` y el usuario gerente.
4. Carta Bar pide al proveedor una sesión de pago para el plan elegido y
   redirige al bar a la página de pago del proveedor.
5. El bar paga (tarjeta o domiciliación SEPA). Los datos no pasan por Carta Bar.
6. El proveedor avisa a Carta Bar por webhook (`checkout.session.completed`).
   Carta Bar verifica la firma y pone el restaurante en `activo`.
7. El bar vuelve a una página de "¡Listo!" con el enlace al panel.

## 3. Flujo mensual (automático)

- El proveedor cobra cada mes sin intervención.
- `invoice.paid` → el restaurante sigue `activo`.
- `invoice.payment_failed` → aviso al bar; periodo de gracia a decidir (ej. 7 días).
- `customer.subscription.deleted` → el restaurante pasa a `suspendido`, sin borrar datos.

## 4. Baja y cambios

- Portal de cliente del proveedor: cambiar tarjeta, ver recibos, darse de baja.
  Sin código propio. Confirmar que cumple el derecho de baja.

## 5. Lo que hay que construir en Carta Bar

- Landing con formulario de alta y página de "¡Listo!".
- Tabla de restaurantes con `estado` (`pendiente_pago`, `activo`, `suspendido`)
  y el id de cliente del proveedor.
- Endpoint `/webhooks/stripe` (o equivalente) con verificación de firma e
  idempotencia (un aviso puede llegar dos veces).
- Comprobación de `estado` al entrar al panel y a la carta del bar.
- Enlace al portal de cliente desde el panel del gerente.

## 6. Pruebas (antes de cobrar un euro)

- Modo de pruebas del proveedor con tarjetas de prueba: alta correcta, pago
  fallido, baja, aviso repetido.
- Test automatizado por cada aviso (pagado, fallido, cancelado) y por cada
  estado de restaurante.

## 7. Preguntas para la gestoría (antes de empezar)

- ¿Autónomo o sociedad para cobrar cuotas a bares?
- ¿Qué factura emitir a cada bar y con qué programa (VeriFactu)?
- ¿Cómo tratar el IVA de la cuota (21 %)?
- ¿Qué contrato y qué términos de uso necesito para los bares?
- ¿Qué cláusulas de protección de datos (encargado del tratamiento)?

## 8. Orden propuesto

1. Gestoría: respuestas de la sección 7.
2. Piloto con 1-2 bares cobrando por transferencia o domiciliación manual.
3. Elegir proveedor y probar en modo de pruebas.
4. Implementar landing, webhook y estados.
5. Pasar a cobro real con un bar piloto y vigilar una semana.
