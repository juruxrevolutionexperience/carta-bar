import { useEffect, useState } from "react";

import type { MiMesa, ResumenComanda } from "./types";

// Lo que el cliente ve de su propia comanda una vez confirmada: solo si va o
// no va ("Comanda 5 · en preparación" / "servido"), por SSE, igual que las
// propuestas (usePropuestas.ts).
export function useComandas(mesa: MiMesa | null): ResumenComanda[] {
  const [comandas, setComandas] = useState<ResumenComanda[]>([]);
  const activa = mesa !== null && mesa.estado !== "cerrada";

  useEffect(() => {
    if (!activa) {
      setComandas([]);
      return;
    }
    const fuente = new EventSource("/api/mesa/comandas/eventos");
    fuente.onmessage = (evento) => {
      try {
        const datos = JSON.parse(evento.data);
        if (Array.isArray(datos)) setComandas(datos);
      } catch {
        // Comentario de "sigo viva": se ignora.
      }
    };
    return () => fuente.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activa]);

  return comandas;
}
