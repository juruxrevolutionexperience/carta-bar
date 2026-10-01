import type { Ticket } from "./types";

function lineaTexto(l: Ticket["lineas"][number]): string {
  const partes = [l.formato, ...l.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${l.nombre_plato} (${partes.join(", ")})` : l.nombre_plato;
}

// Lo unico que existe en pantalla mientras se imprime: el resto de la pagina
// se oculta con @media print (ver estilos.css). Formato de recibo de 80 mm,
// pensado para una termica de cocina/barra, no para un folio.
export function ReciboTicket({ ticket }: { ticket: Ticket }) {
  return (
    <div id="recibo">
      <h1>{ticket.mesa_nombre}</h1>
      <p className="numero">Comanda {ticket.numero_comanda}</p>
      <p className="destino">{ticket.destino === "cocina" ? "COCINA" : "BARRA"}</p>
      <hr />
      <ul>
        {ticket.lineas.map((l) => (
          <li key={l.id} className={l.alcohol ? "alcohol" : undefined}>
            <span className="cantidad">{l.cantidad}×</span> {lineaTexto(l)}
            {l.alcohol && <strong> · ALCOHOL</strong>}
            {l.anulada ? (
              <div className="nota">ANULADA: {l.motivo_anulacion}</div>
            ) : (
              l.nota && <div className="nota">Nota: {l.nota}</div>
            )}
            <div className="quien">{l.pedido_por_nombre}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
