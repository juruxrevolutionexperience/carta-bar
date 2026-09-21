import { useEffect, useState } from "react";

import { cargarMetricas, type MetricasBar } from "./api";

const PERIODOS = [7, 30] as const;

const entero = (n: number) => n.toLocaleString("es-ES");
const dolares = (n: number, decimales: number) =>
  `${n.toLocaleString("es-ES", { minimumFractionDigits: decimales, maximumFractionDigits: decimales })} $`;

function idiomas(porIdioma: Record<string, number>): string {
  const partes = Object.entries(porIdioma)
    .sort((a, b) => b[1] - a[1])
    .map(([idioma, n]) => `${idioma.toUpperCase()} ${n}`);
  return partes.length ? partes.join(" · ") : "—";
}

export function PanelMetricas() {
  const [dias, setDias] = useState<number>(7);
  const [filas, setFilas] = useState<MetricasBar[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setFilas(null);
    setError(false);
    cargarMetricas(dias)
      .then(setFilas)
      .catch(() => setError(true));
  }, [dias]);

  const total = (campo: "visitas" | "preguntas" | "conversaciones" | "rechazadas") =>
    (filas ?? []).reduce((suma, f) => suma + f[campo], 0);
  const costeChat = (filas ?? []).reduce((suma, f) => suma + f.coste_chat_usd, 0);
  const costeTraducciones = (filas ?? []).reduce((suma, f) => suma + f.coste_traducciones_usd, 0);

  return (
    <div className="panel-tarjeta">
      <div className="cabecera-metricas">
        <h2>Métricas</h2>
        <div className="periodos">
          {PERIODOS.map((p) => (
            <button
              key={p}
              type="button"
              className="secundario"
              aria-pressed={dias === p}
              onClick={() => setDias(p)}
            >
              {p} días
            </button>
          ))}
        </div>
      </div>

      {error && <p className="cargando">No se pudieron cargar las métricas.</p>}
      {!error && filas === null && <p className="cargando">Cargando…</p>}

      {!error && filas !== null && (
        <>
          <div className="resumen-metricas">
            <div>
              <strong>{entero(total("visitas"))}</strong>
              <span>visitas</span>
            </div>
            <div>
              <strong>{entero(total("preguntas"))}</strong>
              <span>preguntas</span>
            </div>
            <div>
              <strong>{entero(total("conversaciones"))}</strong>
              <span>conversaciones</span>
            </div>
            <div>
              <strong>{dolares(costeChat, 2)}</strong>
              <span>coste del chat</span>
            </div>
          </div>

          <div className="tabla-scroll">
            <table>
              <thead>
                <tr>
                  <th>Bar</th>
                  <th>Visitas</th>
                  <th>Preguntas</th>
                  <th>Conv.</th>
                  <th>Idiomas</th>
                  <th>Sin cupo</th>
                  <th>Chat</th>
                  <th>Traduc.</th>
                  <th>Por pregunta</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => (
                  <tr key={f.restaurante_id}>
                    <td>{f.nombre}</td>
                    <td>{entero(f.visitas)}</td>
                    <td>{entero(f.preguntas)}</td>
                    <td>{entero(f.conversaciones)}</td>
                    <td>{idiomas(f.preguntas_por_idioma)}</td>
                    <td className={f.rechazadas > 0 ? "alerta" : undefined}>
                      {entero(f.rechazadas)}
                    </td>
                    <td>{dolares(f.coste_chat_usd, 3)}</td>
                    <td>{dolares(f.coste_traducciones_usd, 3)}</td>
                    <td>
                      {f.coste_por_pregunta_usd === null
                        ? "—"
                        : dolares(f.coste_por_pregunta_usd, 4)}
                    </td>
                  </tr>
                ))}
              </tbody>
              {filas.length > 1 && (
                <tfoot>
                  <tr>
                    <td>Total</td>
                    <td>{entero(total("visitas"))}</td>
                    <td>{entero(total("preguntas"))}</td>
                    <td>{entero(total("conversaciones"))}</td>
                    <td></td>
                    <td>{entero(total("rechazadas"))}</td>
                    <td>{dolares(costeChat, 3)}</td>
                    <td>{dolares(costeTraducciones, 3)}</td>
                    <td></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          <p className="nota-metricas">
            Visitas: cargas de la carta sin robots ni el gerente con sesión abierta (una
            persona que recarga cuenta dos veces). Conversación: pregunta que llega sin
            historial, aproximada. Sin cupo: preguntas cortadas por el tope diario de gasto.
            Días en hora de España.
          </p>
        </>
      )}
    </div>
  );
}
