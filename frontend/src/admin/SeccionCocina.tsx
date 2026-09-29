import { useCallback, useEffect, useState } from "react";

import { cambiarEstadoTicket, cargarTickets, type Destino, type Ticket } from "./api";

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

  async function avanzar(ticket: Ticket) {
    const siguiente = ticket.estado === "recibida" ? "en_preparacion" : "servida";
    setOcupado(ticket.id);
    try {
      const r = await cambiarEstadoTicket(ticket.id, siguiente);
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

  const visibles = tickets.filter((t) => filtro === TODOS || t.destino === filtro);
  const recibidas = visibles.filter((t) => t.estado === "recibida");
  const enPreparacion = visibles.filter((t) => t.estado === "en_preparacion");

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

      <div className="columnas-cocina">
        <section className="columna-cocina">
          <h2>Nuevas ({recibidas.length})</h2>
          {recibidas.map((t) => (
            <TarjetaTicket key={t.id} ticket={t} ocupado={ocupado === t.id} onAvanzar={avanzar} />
          ))}
        </section>
        <section className="columna-cocina">
          <h2>En preparación ({enPreparacion.length})</h2>
          {enPreparacion.map((t) => (
            <TarjetaTicket key={t.id} ticket={t} ocupado={ocupado === t.id} onAvanzar={avanzar} />
          ))}
        </section>
      </div>
    </div>
  );
}

interface PropsTarjeta {
  ticket: Ticket;
  ocupado: boolean;
  onAvanzar: (ticket: Ticket) => void;
}

function TarjetaTicket({ ticket, ocupado, onAvanzar }: PropsTarjeta) {
  return (
    <article className={"tarjeta-ticket destino-" + ticket.destino}>
      <div className="cabecera-ticket">
        <span className="mesa-ticket">{ticket.mesa_nombre}</span>
        <span className="numero-ticket">Comanda {ticket.numero_comanda}</span>
      </div>
      <ul className="lineas-ticket">
        {ticket.lineas.map((l) => (
          <li key={l.id} className={l.alcohol ? "con-alcohol" : undefined}>
            <span className="cantidad-linea">{l.cantidad}×</span>
            <span className="texto-linea">
              {lineaTexto(l)}
              {l.alcohol && <span className="chip-alcohol">alcohol</span>}
            </span>
            {l.nota && <span className="nota-linea">{l.nota}</span>}
            <span className="quien-linea">{l.pedido_por_nombre}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="primario boton-avanzar"
        disabled={ocupado}
        onClick={() => onAvanzar(ticket)}
      >
        {ticket.estado === "recibida" ? "Empezar" : "Servida"}
      </button>
    </article>
  );
}
