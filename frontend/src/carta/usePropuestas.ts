import { useEffect, useState } from "react";

import { confirmarPropuestas, crearPropuesta, quitarPropuesta, type NuevaPropuesta } from "./api";
import type { MiMesa, Propuesta } from "./types";

interface UsoPropuestas {
  propuestas: Propuesta[];
  proponer: (datos: NuevaPropuesta) => Promise<{ ok: boolean; status: number }>;
  quitar: (id: string) => Promise<boolean>;
  confirmar: () => Promise<boolean>;
}

// Tiempo real por SSE (docs/PEDIDO-EN-MESA.md, seccion 10): en cuanto alguien
// de la mesa propone o quita algo, el navegador reconecta solo si se corta.
export function usePropuestas(mesa: MiMesa | null): UsoPropuestas {
  const [propuestas, setPropuestas] = useState<Propuesta[]>([]);
  // useMesa() da un objeto nuevo en cada sondeo (cada 5 s): sin esto, el
  // EventSource se cerraria y volveria a abrir todo el rato.
  const activa = mesa !== null && mesa.estado !== "cerrada";

  useEffect(() => {
    if (!activa) {
      setPropuestas([]);
      return;
    }
    const fuente = new EventSource("/api/mesa/propuestas/eventos");
    fuente.onmessage = (evento) => {
      try {
        const datos = JSON.parse(evento.data);
        if (Array.isArray(datos)) setPropuestas(datos);
      } catch {
        // Comentario de "sigo viva" u otro dato que no es la lista: se ignora.
      }
    };
    return () => fuente.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activa]);

  return {
    propuestas,
    proponer: async (datos) => {
      const r = await crearPropuesta(datos);
      return { ok: r.ok, status: r.status };
    },
    quitar: quitarPropuesta,
    confirmar: confirmarPropuestas,
  };
}
