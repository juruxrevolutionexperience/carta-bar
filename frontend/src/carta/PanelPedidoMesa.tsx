import { useState } from "react";

import { useCartaContext } from "./CartaContext";
import { useMesaContext } from "./MesaContext";
import { importe } from "./precios";
import type { Propuesta } from "./types";

const TEXTO_ESTADO: Record<string, string> = {
  por_confirmar: "Esperando a que el camarero acepte la mesa",
  abierta: "Mesa abierta",
  cuenta_pedida: "Cuenta pedida",
};

function lineaTexto(p: Propuesta): string {
  const partes = [p.formato, ...p.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${p.nombre_plato} (${partes.join(", ")})` : p.nombre_plato;
}

// Lo que ve cualquiera de la mesa: las propuestas de todos, quien puede
// quitar que (el suyo, o cualquiera si es anfitrion) y confirmar (solo el
// anfitrion). Sin esto proponer no serviria de nada: es donde se ve y se
// manda el pedido (docs/PEDIDO-EN-MESA.md, seccion 11.1).
export function PanelPedidoMesa() {
  const { config } = useCartaContext();
  const { mesa, propuestas, quitar, confirmar } = useMesaContext();
  const [abierto, setAbierto] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const moneda = config.moneda || "€";

  if (!mesa || mesa.estado === "cerrada") return null;

  const activas = propuestas.filter((p) => p.estado !== "retirada");
  const pendientes = activas.filter((p) => p.estado === "pendiente");
  const total = activas.reduce((suma, p) => suma + p.total, 0);
  const soyAnfitrion = mesa.rol === "anfitrion";

  async function confirmarPedido() {
    setConfirmando(true);
    await confirmar();
    setConfirmando(false);
  }

  return (
    <>
      <button
        type="button"
        className="lanzador lanzador-lista"
        onClick={() => setAbierto(true)}
        aria-label="Pedido de la mesa"
      >
        🍽️
        {activas.length > 0 && <span className="cuenta-lista">{activas.length}</span>}
      </button>

      <div className={"panel" + (abierto ? " abierto" : "")}>
        <div className="panel-top">
          <h2>Mesa {mesa.mesa}</h2>
          <button
            type="button"
            className="cerrar"
            aria-label="Cerrar"
            onClick={() => setAbierto(false)}
          >
            ×
          </button>
        </div>
        <p className="estado-mesa">{TEXTO_ESTADO[mesa.estado] ?? mesa.estado}</p>

        <div className="hilo-lista">
          {activas.length === 0 && <p className="vacio">Aún no habéis pedido nada.</p>}
          {activas.map((p) => (
            <div className="fila-lista" key={p.id}>
              <div className="fila-lista-info">
                <span className="fila-lista-nombre">
                  {lineaTexto(p)} × {p.cantidad}
                  {p.estado === "confirmada" && <span className="chip-confirmada"> · pedido</span>}
                </span>
                <span className="fila-lista-quien">{p.comensal_nombre}</span>
                <span className="fila-lista-precio">{importe(p.total, moneda)}</span>
              </div>
              {p.estado === "pendiente" && (soyAnfitrion || p.comensal_id === mesa.comensal_id) && (
                <button
                  type="button"
                  className="quitar-propuesta"
                  aria-label={`Quitar ${p.nombre_plato}`}
                  onClick={() => quitar(p.id)}
                >
                  Quitar
                </button>
              )}
            </div>
          ))}
        </div>

        {activas.length > 0 && (
          <div className="pie-lista">
            <div className="total-lista">
              <span>Total</span>
              <strong>{importe(total, moneda)}</strong>
            </div>
            {soyAnfitrion ? (
              pendientes.length > 0 && (
                <button
                  type="button"
                  className="boton-proponer"
                  disabled={confirmando}
                  onClick={confirmarPedido}
                >
                  Confirmar pedido ({pendientes.length})
                </button>
              )
            ) : (
              <p className="aviso-lista">
                {pendientes.length > 0
                  ? `${mesa.comensales[0] ?? "El anfitrión"} confirma los pedidos de la mesa`
                  : "El anfitrión ya ha confirmado este pedido"}
              </p>
            )}
          </div>
        )}
      </div>
    </>
  );
}
