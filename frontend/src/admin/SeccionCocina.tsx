import { useCallback, useEffect, useState } from "react";

import { anularLinea, cambiarEstadoTicket, cargarTickets, type Destino, type Ticket } from "./api";

const REFRESCO_MS = 5000;

const TODOS = "todos";
type Filtro = Destino | typeof TODOS;

const TEXTO_DESTINO: Record<Destino, string> = { cocina: "Cocina", barra: "Barra" };

function lineaTexto(l: Ticket["lineas"][number]): string {
  const partes = [l.formato, ...l.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${l.nombre_plato} (${partes.join(", ")})` : l.nombre_plato;
}

// La pantalla que mas importa en el dia a dia (docs/PEDIDO-EN-MESA.md,
// seccion 11.2): tarjetas grandes, una por ticket, para leerlas de pie y con
// prisa. De momento vive en el /admin del gerente; el acceso propio del
// camarero llega despues (bloque 3, "rol camarero"), sin tener que rehacer
// esto.
export function SeccionCocina() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState(false);
  const [filtro, setFiltro] = useState<Filtro>(TODOS);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const recargar = useCallback(() => {
    cargarTickets()
      .then((t) => {
        setTickets(t);
        setError(false);
      })
      .catch(() => setError(true));
  }, []);

  useEffect(recargar, [recargar]);
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) recargar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [recargar]);

  // Un solo toque: de pendiente a servida. Antes habia un paso "Empezar" que
  // obligaba a alguien a pulsar cada comanda al llegar, y en hora punta eso
  // es tiempo perdido (decidido con el dueno el 2026-10-04). El cliente ve
  // "en preparacion" desde que se envia hasta que se marca como lista.
  async function marcarLista(ticket: Ticket) {
    setOcupado(ticket.id);
    try {
      const r = await cambiarEstadoTicket(ticket.id, "servida");
      if (r.ok) recargar();
    } finally {
      setOcupado(null);
    }
  }

  async function anular(ticket: Ticket, lineaId: string) {
    const motivo = window.prompt("¿Por qué se anula? (lo verá el gerente)");
    if (!motivo || !motivo.trim()) return;
    setOcupado(ticket.id);
    try {
      const r = await anularLinea(ticket.id, lineaId, motivo.trim());
      if (r.ok) recargar();
    } finally {
      setOcupado(null);
    }
  }

  if (tickets === null) {
    return (
      <div className="tarjeta">
        <p>{error ? "No se pudieron cargar las comandas." : "Cargando…"}</p>
      </div>
    );
  }

  // Del mas antiguo al mas nuevo (ya viene asi del servidor): lo que lleva
  // mas tiempo esperando, arriba. Incluye los que quedaran "en preparacion"
  // de antes de quitar el paso "Empezar".
  const visibles = tickets.filter((t) => filtro === TODOS || t.destino === filtro);

  return (
    <div className="cocina">
      <div className="pestanas-zona" role="tablist">
        {([TODOS, "cocina", "barra"] as const).map((d) => (
          <button
            key={d}
            type="button"
            role="tab"
            aria-selected={filtro === d}
            className={"pestana-zona" + (filtro === d ? " activa" : "")}
            onClick={() => setFiltro(d)}
          >
            {d === TODOS ? "Todo" : TEXTO_DESTINO[d]}
          </button>
        ))}
        {error && <span className="chip-resumen sin-conexion">Sin conexión</span>}
        <a href="/admin/impresion" target="_blank" rel="noreferrer" className="enlace-impresion">
          Pantalla de impresión ↗
        </a>
      </div>

      <p className="ayuda-campo">
        Para imprimir solas en cocina y barra, hace falta un aparato aparte dedicado a esto —
        nunca el TPV principal del bar. Ver "Pantalla de impresión" arriba.
      </p>

      {visibles.length === 0 && <p className="cargando">Sin comandas pendientes.</p>}

      <div className="lista-cocina">
        {visibles.map((t) => (
          <TarjetaTicket
            key={t.id}
            ticket={t}
            ocupado={ocupado === t.id}
            onLista={marcarLista}
            onAnular={anular}
          />
        ))}
      </div>
    </div>
  );
}

interface PropsTarjeta {
  ticket: Ticket;
  ocupado: boolean;
  onLista: (ticket: Ticket) => void;
  onAnular: (ticket: Ticket, lineaId: string) => void;
}

function TarjetaTicket({ ticket, ocupado, onLista, onAnular }: PropsTarjeta) {
  return (
    <article className={"tarjeta-ticket destino-" + ticket.destino}>
      <div className="cabecera-ticket">
        <span className="mesa-ticket">{ticket.mesa_nombre}</span>
        <span className="numero-ticket">Comanda {ticket.numero_comanda}</span>
      </div>
      <ul className="lineas-ticket">
        {ticket.lineas.map((l) => (
          <li
            key={l.id}
            className={(l.alcohol ? "con-alcohol " : "") + (l.anulada ? "anulada" : "")}
          >
            <span className="cantidad-linea">{l.cantidad}×</span>
            <span className="texto-linea">
              {lineaTexto(l)}
              {l.alcohol && <span className="chip-alcohol">alcohol</span>}
            </span>
            {l.anulada ? (
              <span className="nota-linea">Anulada: {l.motivo_anulacion}</span>
            ) : (
              <>
                {l.nota && <span className="nota-linea">{l.nota}</span>}
                <button
                  type="button"
                  className="anular-linea"
                  disabled={ocupado}
                  onClick={() => onAnular(ticket, l.id)}
                >
                  Anular
                </button>
              </>
            )}
            <span className="quien-linea">{l.pedido_por_nombre}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="primario boton-avanzar"
        disabled={ocupado}
        onClick={() => onLista(ticket)}
      >
        Listo
      </button>
    </article>
  );
}
