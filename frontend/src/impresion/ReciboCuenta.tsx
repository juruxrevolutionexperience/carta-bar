import type { Cuenta } from "./types";

function lineaTexto(l: Cuenta["lineas"][number]): string {
  const partes = [l.formato, ...l.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${l.nombre_plato} (${partes.join(", ")})` : l.nombre_plato;
}

function euros(n: number): string {
  return n.toFixed(2).replace(".", ",") + " €";
}

// Mismo formato de 80 mm que ReciboTicket, pero con precios: un resumen para
// el cliente, nunca una factura (sin NIF ni numeracion fiscal, ver
// carta_bar/cuentas.py). El desglose por persona es informativo: hoy se
// cobra junto, no en partes (docs/PEDIDO-EN-MESA.md).
export function ReciboCuenta({ cuenta }: { cuenta: Cuenta }) {
  return (
    <div id="recibo">
      <h1>{cuenta.mesa_nombre}</h1>
      <p className="destino">RESUMEN DE CUENTA</p>
      <p className="aviso-no-factura">No es un documento fiscal</p>
      <hr />
      <ul>
        {cuenta.lineas.map((l, i) => (
          <li key={i}>
            <div className="fila-cuenta">
              <span>
                <span className="cantidad">{l.cantidad}×</span> {lineaTexto(l)}
              </span>
              <span className="precio">{euros(l.total)}</span>
            </div>
            <div className="quien">{l.pedido_por_nombre}</div>
          </li>
        ))}
      </ul>
      <hr />
      {cuenta.por_persona.length > 1 && (
        <>
          <ul className="por-persona">
            {cuenta.por_persona.map((p) => (
              <li key={p.nombre} className="fila-cuenta">
                <span>{p.nombre}</span>
                <span className="precio">{euros(p.total)}</span>
              </li>
            ))}
          </ul>
          <hr />
        </>
      )}
      <p className="fila-cuenta total">
        <span>Total</span>
        <span>{euros(cuenta.total)}</span>
      </p>
    </div>
  );
}
