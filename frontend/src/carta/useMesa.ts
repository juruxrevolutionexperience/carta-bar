import { useCallback, useEffect, useState } from "react";

import { entrarMesa, miMesa } from "./api";
import type { MiMesa } from "./types";

// Mientras el camarero no ha aceptado (o no ha llegado la cuenta), el cliente
// quiere verlo sin tener que recargar: igual de a menudo que la pantalla
// Servicio del gerente (SeccionServicio.tsx, REFRESCO_MS).
const REFRESCO_MS = 5000;

// Si la carta se abre con "?mesa=<token>" (el QR de la mesa), entra o se une
// a su sesión. Si no lleva ese parámetro pero ya hay una cookie de comensal
// (recarga de página, o se volvió a abrir la carta desde el mismo móvil), se
// recupera igualmente. Sin ninguna de las dos cosas, sigue como carta normal
// y no hay nada que refrescar.
export function useMesa(): MiMesa | null {
  const [mesa, setMesa] = useState<MiMesa | null>(null);

  const refrescar = useCallback(() => {
    miMesa().then(setMesa);
  }, []);

  useEffect(() => {
    let activo = true;
    const url = new URL(window.location.href);
    const token = url.searchParams.get("mesa");

    (async () => {
      let resultado: MiMesa | null;
      if (token) {
        const idioma = (navigator.language || "es").slice(0, 2);
        resultado = await entrarMesa(token, idioma);
        // El token no vuelve a hacer falta en la URL: ya quedó la cookie.
        url.searchParams.delete("mesa");
        window.history.replaceState(null, "", url.toString());
      } else {
        resultado = await miMesa();
      }
      if (activo) setMesa(resultado);
    })();

    return () => {
      activo = false;
    };
  }, []);

  // Solo se sondea si hay una mesa que mirar: un cliente que abre la carta
  // sin escanear nada no genera tráfico de más.
  useEffect(() => {
    if (!mesa || mesa.estado === "cerrada") return;
    const id = window.setInterval(() => {
      if (!document.hidden) refrescar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [mesa, refrescar]);

  return mesa;
}
