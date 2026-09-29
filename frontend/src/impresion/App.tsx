import { useEffect, useRef, useState } from "react";

import "./estilos.css";
import { ReciboTicket } from "./ReciboTicket";
import type { Destino, Ticket } from "./types";

const CLAVE_DESTINO = "impresion_destino";
const CLAVE_IMPRESOS = "impresion_impresos";
const CLAVE_HISTORIAL = "impresion_historial";
const MAX_IMPRESOS_GUARDADOS = 300;
const MAX_HISTORIAL_GUARDADO = 50;
const ESPERA_ENTRE_IMPRESIONES_MS = 1200;

interface Impreso {
  ticket: Ticket;
  impreso_en: string;
}

function cargarImpresos(): Set<string> {
  try {
    const guardado = localStorage.getItem(CLAVE_IMPRESOS);
    return new Set(guardado ? (JSON.parse(guardado) as string[]) : []);
  } catch {
    return new Set();
  }
}

function guardarImpresos(ids: Set<string>) {
  const lista = [...ids].slice(-MAX_IMPRESOS_GUARDADOS);
  try {
    localStorage.setItem(CLAVE_IMPRESOS, JSON.stringify(lista));
  } catch {
    // Sin sitio en localStorage: se sigue imprimiendo, solo que si se
    // recarga la pagina podria repetir algun ticket antiguo.
  }
}

function cargarHistorial(): Impreso[] {
  try {
    const guardado = localStorage.getItem(CLAVE_HISTORIAL);
    return guardado ? (JSON.parse(guardado) as Impreso[]) : [];
  } catch {
    return [];
  }
}

function guardarHistorial(historial: Impreso[]) {
  try {
    localStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(historial.slice(0, MAX_HISTORIAL_GUARDADO)));
  } catch {
    // Sin sitio en localStorage: el historial de esta sesion se pierde al
    // recargar, pero la impresion en si no se ve afectada.
  }
}

function hora(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

// Pensada para un aparato aparte y modesto, dedicado solo a esto (ver
// docs/PEDIDO-EN-MESA.md, "Impresion en cocina/barra"): nunca en el TPV
// principal del bar. Elige una vez si es la de cocina o la de barra, y desde
// ahi imprime sola cada ticket nuevo que le llega por SSE, sin que nadie
// tenga que tocar nada.
//
// El historial de abajo (mesa, comanda, hora, con su "Reimprimir") existe
// sobre todo por lo siguiente: hasta que el navegador de este aparato se
// abra con --kiosk-printing, cada ticket saca el dialogo de imprimir de
// Windows, y si alguien le da a Cancelar por error la comanda no debe
// perderse en silencio — aqui se puede volver a mandar.
export function App() {
  const [destino, setDestino] = useState<Destino | null>(
    () => (localStorage.getItem(CLAVE_DESTINO) as Destino | null) ?? null
  );
  const [conectado, setConectado] = useState(false);
  const [enCola, setEnCola] = useState(0);
  const [historial, setHistorial] = useState<Impreso[]>(() => cargarHistorial());
  const impresos = useRef<Set<string>>(cargarImpresos());
  const cola = useRef<Ticket[]>([]);
  const imprimiendo = useRef(false);
  const [ticketVisible, setTicketVisible] = useState<Ticket | null>(null);

  function elegirDestino(d: Destino) {
    localStorage.setItem(CLAVE_DESTINO, d);
    setDestino(d);
  }

  function registrarImpreso(ticket: Ticket) {
    setHistorial((actual) => {
      const nuevo = [{ ticket, impreso_en: new Date().toISOString() }, ...actual].slice(
        0,
        MAX_HISTORIAL_GUARDADO
      );
      guardarHistorial(nuevo);
      return nuevo;
    });
  }

  function procesarCola() {
    if (imprimiendo.current || cola.current.length === 0) return;
    imprimiendo.current = true;
    const ticket = cola.current.shift()!;
    setEnCola(cola.current.length);
    setTicketVisible(ticket);
    // Un respiro para que el DOM pinte el recibo antes de imprimir.
    setTimeout(() => {
      window.print();
      impresos.current.add(ticket.id);
      guardarImpresos(impresos.current);
      registrarImpreso(ticket);
      setTimeout(() => {
        imprimiendo.current = false;
        procesarCola();
      }, ESPERA_ENTRE_IMPRESIONES_MS);
    }, 80);
  }

  // Reimprimir es siempre un gesto manual y puntual (alguien canceló el
  // diálogo, o quiere una copia más): se salta la cola en vez de competir con
  // lo que vaya llegando por SSE.
  function reimprimir(ticket: Ticket) {
    if (imprimiendo.current) return;
    imprimiendo.current = true;
    setTicketVisible(ticket);
    setTimeout(() => {
      window.print();
      setTimeout(() => {
        imprimiendo.current = false;
        procesarCola();
      }, ESPERA_ENTRE_IMPRESIONES_MS);
    }, 80);
  }

  useEffect(() => {
    if (!destino) return;
    const fuente = new EventSource(`/admin/api/tickets/eventos?destino=${destino}`);
    fuente.onopen = () => setConectado(true);
    fuente.onerror = () => setConectado(false);
    fuente.onmessage = (evento) => {
      try {
        const tickets = JSON.parse(evento.data) as Ticket[];
        if (!Array.isArray(tickets)) return;
        const nuevos = tickets.filter((t) => !impresos.current.has(t.id));
        for (const t of nuevos) {
          if (!cola.current.some((c) => c.id === t.id)) cola.current.push(t);
        }
        setEnCola(cola.current.length);
        procesarCola();
      } catch {
        // Comentario de "sigo viva": se ignora.
      }
    };
    return () => fuente.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [destino]);

  if (!destino) {
    return (
      <div className="elegir-destino">
        <h1>¿Qué impresora es esta?</h1>
        <button type="button" onClick={() => elegirDestino("cocina")}>
          Cocina
        </button>
        <button type="button" onClick={() => elegirDestino("barra")}>
          Barra
        </button>
      </div>
    );
  }

  return (
    <div className="pantalla-impresion">
      <h1>Impresión — {destino === "cocina" ? "Cocina" : "Barra"}</h1>
      <p className={"estado" + (conectado ? " ok" : " sin-conexion")}>
        {conectado ? "Conectado" : "Sin conexión — reintentando…"}
      </p>
      <p>Pendientes de imprimir: {enCola}</p>

      {historial.length > 0 && (
        <table className="historial-impresion">
          <thead>
            <tr>
              <th>Mesa</th>
              <th>Comanda</th>
              <th>Hora</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {historial.map((h) => (
              <tr key={h.ticket.id + h.impreso_en}>
                <td>{h.ticket.mesa_nombre}</td>
                <td>{h.ticket.numero_comanda}</td>
                <td>{hora(h.impreso_en)}</td>
                <td>
                  <button type="button" onClick={() => reimprimir(h.ticket)}>
                    Reimprimir
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <button
        type="button"
        className="cambiar-destino"
        onClick={() => {
          localStorage.removeItem(CLAVE_DESTINO);
          setDestino(null);
        }}
      >
        Cambiar impresora
      </button>
      {ticketVisible && <ReciboTicket ticket={ticketVisible} />}
    </div>
  );
}
