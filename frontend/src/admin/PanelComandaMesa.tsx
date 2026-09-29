import { useCallback, useEffect, useState } from "react";

import {
  ajustarPrecioLinea,
  anadirAComanda,
  cargarComandaMesa,
  confirmarComandaMesa,
  quitarDeComanda,
  type ComandaMesa,
  type NuevaLineaComanda,
  type Propuesta,
} from "./api";
import { SelectorTPV } from "./SelectorTPV";

const REFRESCO_MS = 5000;

function lineaTexto(p: Propuesta): string {
  const partes = [p.formato, ...p.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${p.nombre_plato} (${partes.join(", ")})` : p.nombre_plato;
}

function importe(n: number): string {
  return n.toFixed(2).replace(".", ",") + " €";
}

interface Props {
  mesaId: string;
}

// Lo que pide el camarero/gerente: entrar en la mesa y ver todo el pedido,
// quien pidio que, el total, cuanto le toca a cada uno, y poder anadir,
// quitar o ajustar un precio sin salir de aqui (docs/PEDIDO-EN-MESA.md,
// "Gestion de la comanda desde la mesa").
export function PanelComandaMesa({ mesaId }: Props) {
  const [comanda, setComanda] = useState<ComandaMesa | null>(null);
  const [error, setError] = useState(false);
  const [anadiendo, setAnadiendo] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [editando, setEditando] = useState<string | null>(null);
  const [precioEditado, setPrecioEditado] = useState("");

  const recargar = useCallback(() => {
    cargarComandaMesa(mesaId)
      .then((c) => {
        setComanda(c);
        setError(c === null);
      })
      .catch(() => setError(true));
  }, [mesaId]);

  useEffect(recargar, [recargar]);
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) recargar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [recargar]);

  async function anadir(datos: NuevaLineaComanda): Promise<boolean> {
    const r = await anadirAComanda(mesaId, datos);
    if (r.ok) recargar();
    return r.ok;
  }

  async function quitar(propuestaId: string) {
    setOcupado(true);
    try {
      await quitarDeComanda(mesaId, propuestaId);
      recargar();
    } finally {
      setOcupado(false);
    }
  }

  async function guardarPrecio(propuestaId: string) {
    const nuevo = Number(precioEditado.replace(",", "."));
    if (!Number.isFinite(nuevo) || nuevo < 0) return;
    setOcupado(true);
    try {
      await ajustarPrecioLinea(mesaId, propuestaId, nuevo);
      setEditando(null);
      recargar();
    } finally {
      setOcupado(false);
    }
  }

  async function confirmar() {
    if (!window.confirm("¿Mandar esto a cocina/barra?")) return;
    setOcupado(true);
    try {
      await confirmarComandaMesa(mesaId);
      recargar();
    } finally {
      setOcupado(false);
    }
  }

  if (error && comanda === null) {
    return <p className="explicacion">No se pudo cargar la comanda.</p>;
  }
  if (comanda === null) {
    return <p className="explicacion">Cargando…</p>;
  }

  const activas = comanda.propuestas.filter((p) => p.estado !== "retirada");
  const pendientes = activas.filter((p) => p.estado === "pendiente");

  return (
    <div className="panel-comanda-mesa">
      <h4 className="titulo-comensales">Comanda</h4>

      {activas.length === 0 && <p className="explicacion">Nada pedido todavía.</p>}

      {activas.length > 0 && (
        <ul className="lineas-comanda-mesa">
          {activas.map((p) => (
            <li key={p.id}>
              <div className="fila-linea-comanda">
                <span>
                  {p.cantidad}× {lineaTexto(p)}
                  {p.estado === "confirmada" && <span className="chip-confirmada"> · pedido</span>}
                </span>
                {editando === p.id ? (
                  <span className="editor-precio-linea">
                    <input
                      type="number"
                      step="0.01"
                      min={0}
                      value={precioEditado}
                      onChange={(e) => setPrecioEditado(e.target.value)}
                      autoFocus
                    />
                    <button type="button" onClick={() => void guardarPrecio(p.id)}>
                      OK
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="precio-linea-editable"
                    onClick={() => {
                      setEditando(p.id);
                      setPrecioEditado(String(p.precio_unitario));
                    }}
                  >
                    {importe(p.total)}
                  </button>
                )}
              </div>
              <div className="fila-linea-comanda-quien">
                <span>{p.comensal_nombre}</span>
                {p.estado === "pendiente" && (
                  <button type="button" disabled={ocupado} onClick={() => void quitar(p.id)}>
                    Quitar
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {comanda.por_persona.length > 1 && (
        <ul className="por-persona-comanda">
          {comanda.por_persona.map((r) => (
            <li key={r.nombre}>
              <span>{r.nombre}</span>
              <span>{importe(r.total)}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="total-comanda-mesa">
        <span>Total</span>
        <strong>{importe(comanda.total)}</strong>
      </div>

      <button
        type="button"
        className="secundario boton-servicio"
        onClick={() => setAnadiendo(true)}
      >
        Añadir a la mesa
      </button>

      {pendientes.length > 0 && (
        <button
          type="button"
          className="primario boton-servicio"
          disabled={ocupado}
          onClick={() => void confirmar()}
        >
          Confirmar comanda ({pendientes.length})
        </button>
      )}

      {anadiendo && <SelectorTPV onElegir={anadir} onCerrar={() => setAnadiendo(false)} />}
    </div>
  );
}
