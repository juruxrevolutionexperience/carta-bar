import { useEffect, useRef, useState } from "react";

import "./estilos.css";
import { ReciboCuenta } from "./ReciboCuenta";
import { ReciboTicket } from "./ReciboTicket";
import type { Cuenta, PantallaImpresion, Ticket } from "./types";

type Imprimible = Ticket | Cuenta;

function esTicket(item: Imprimible): item is Ticket {
  return "destino" in item;
}

function euros(n: number): string {
  return n.toFixed(2).replace(".", ",") + " €";
}

const CLAVE_DESTINO = "impresion_destino";
const CLAVE_IMPRESOS = "impresion_impresos";
const CLAVE_HISTORIAL = "impresion_historial";
const MAX_IMPRESOS_GUARDADOS = 300;
const MAX_HISTORIAL_GUARDADO = 50;
const ESPERA_ENTRE_IMPRESIONES_MS = 1200;

interface Impreso {
  item: Imprimible;
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
    localStorage.setItem(
      CLAVE_HISTORIAL,
      JSON.stringify(historial.slice(0, MAX_HISTORIAL_GUARDADO))
    );
  } catch {
    // Sin sitio en localStorage: el historial de esta sesion se pierde al
    // recargar, pero la impresion en si no se ve afectada.
  }
}

function hora(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}

function tituloDestino(d: PantallaImpresion): string {
  if (d === "cocina") return "Cocina";
  if (d === "barra") return "Barra";
  return "Cuenta";
}

function urlEventos(d: PantallaImpresion): string {
  return d === "cuenta"
    ? "/admin/api/cuentas/eventos"
    : `/admin/api/tickets/eventos?destino=${d}`;
}

// Pensada para un aparato aparte y modesto, dedicado solo a esto (ver
// docs/PEDIDO-EN-MESA.md, "Impresion en cocina/barra"): nunca en el TPV
// principal del bar. Elige una vez que imprime este aparato (cocina, barra o
// la cuenta) y desde ahi imprime solo cada cosa nueva que le llega por SSE,
// sin que nadie tenga que tocar nada.
//
// El historial de abajo (mesa, hora, con su "Reimprimir") existe sobre todo
// por lo siguiente: hasta que el navegador de este aparato se abra con
// --kiosk-printing, cada papel saca el dialogo de imprimir de Windows, y si
// alguien le da a Cancelar por error no debe perderse en silencio — aqui se
// puede volver a mandar.
export function App() {
  const [destino, setDestino] = useState<PantallaImpresion | null>(
    () => (localStorage.getItem(CLAVE_DESTINO) as PantallaImpresion | null) ?? null
  );
  const [conectado, setConectado] = useState(false);
  const [enCola, setEnCola] = useState(0);
  const [historial, setHistorial] = useState<Impreso[]>(() => cargarHistorial());
  const impresos = useRef<Set<string>>(cargarImpresos());
  const cola = useRef<Imprimible[]>([]);
  const imprimiendo = useRef(false);
  const [itemVisible, setItemVisible] = useState<Imprimible | null>(null);

  function elegirDestino(d: PantallaImpresion) {
    localStorage.setItem(CLAVE_DESTINO, d);
    setDestino(d);
  }

  function registrarImpreso(item: Imprimible) {
    setHistorial((actual) => {
      const nuevo = [{ item, impreso_en: new Date().toISOString() }, ...actual].slice(
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
    const item = cola.current.shift()!;
    setEnCola(cola.current.length);
    setItemVisible(item);
    // Un respiro para que el DOM pinte el recibo antes de imprimir.
    setTimeout(() => {
      window.print();
      impresos.current.add(item.id);
      guardarImpresos(impresos.current);
      registrarImpreso(item);
      setTimeout(() => {
        imprimiendo.current = false;
        procesarCola();
      }, ESPERA_ENTRE_IMPRESIONES_MS);
    }, 80);
  }

  // Reimprimir es siempre un gesto manual y puntual (alguien canceló el
  // diálogo, o quiere una copia más): se salta la cola en vez de competir con
  // lo que vaya llegando por SSE.
  function reimprimir(item: Imprimible) {
    if (imprimiendo.current) return;
    imprimiendo.current = true;
    setItemVisible(item);
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
    const fuente = new EventSource(urlEventos(destino));
    fuente.onopen = () => setConectado(true);
    fuente.onerror = () => setConectado(false);
    fuente.onmessage = (evento) => {
      try {
        const items = JSON.parse(evento.data) as Imprimible[];
        if (!Array.isArray(items)) return;
        const nuevos = items.filter((t) => !impresos.current.has(t.id));
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
        <h1>¿Qué imprime este aparato?</h1>
        <button type="button" onClick={() => elegirDestino("cocina")}>
          Cocina
        </button>
        <button type="button" onClick={() => elegirDestino("barra")}>
          Barra
        </button>
        <button type="button" onClick={() => elegirDestino("cuenta")}>
          Cuenta
        </button>
      </div>
    );
  }

  return (
    <div className="pantalla-impresion">
      <h1>Impresión — {tituloDestino(destino)}</h1>
      <p className={"estado" + (conectado ? " ok" : " sin-conexion")}>
        {conectado ? "Conectado" : "Sin conexión — reintentando…"}
      </p>
      <p>Pendientes de imprimir: {enCola}</p>

      {historial.length > 0 && (
        <table className="historial-impresion">
          <thead>
            <tr>
              <th>Mesa</th>
              <th>{destino === "cuenta" ? "Total" : "Comanda"}</th>
              <th>Hora</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {historial.map((h) => (
              <tr key={h.item.id + h.impreso_en}>
                <td>{h.item.mesa_nombre}</td>
                <td>{esTicket(h.item) ? h.item.numero_comanda : euros(h.item.total)}</td>
                <td>{hora(h.impreso_en)}</td>
                <td>
                  <button type="button" onClick={() => reimprimir(h.item)}>
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
      {itemVisible &&
        (esTicket(itemVisible) ? (
          <ReciboTicket ticket={itemVisible} />
        ) : (
          <ReciboCuenta cuenta={itemVisible} />
        ))}
    </div>
  );
}
