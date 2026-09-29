import { useCallback, useEffect, useState } from "react";

import { entrarMesa, miMesa } from "./api";
import type { MiMesa } from "./types";

// Mientras el camarero no ha aceptado (o no ha llegado la cuenta), el cliente
// quiere verlo sin tener que recargar: igual de a menudo que la pantalla
// Servicio del gerente (SeccionServicio.tsx, REFRESCO_MS).
const REFRESCO_MS = 5000;

export interface UsoMesa {
  mesa: MiMesa | null;
  // Hay un "?mesa=" en la URL sin resolver todavia: hace falta preguntar el
  // nombre antes de entrar (para saber quien pidio que en el pedido de la
  // mesa), con EntrarMesaDialog.tsx.
  pidiendoNombre: boolean;
  entrar: (nombre: string) => void;
}

// Si la carta se abre con "?mesa=<token>" (el QR de la mesa), pide el nombre
// y entra o se une a la sesion. Si no lleva ese parametro pero ya hay una
// cookie de comensal (recarga de pagina, o se volvio a abrir la carta desde
// el mismo movil), se recupera sin volver a preguntar. Sin ninguna de las dos
// cosas, sigue como carta normal y no hay nada que refrescar.
export function useMesa(): UsoMesa {
  const [mesa, setMesa] = useState<MiMesa | null>(null);
  const [tokenPendiente, setTokenPendiente] = useState<string | null>(null);

  const refrescar = useCallback(() => {
    miMesa().then(setMesa);
  }, []);

  useEffect(() => {
    let activo = true;
    const url = new URL(window.location.href);
    const token = url.searchParams.get("mesa");

    if (token) {
      // No se entra todavia: EntrarMesaDialog llama a entrar() con el nombre
      // (o vacio, si prefiere no decirlo) y ahi se hace la peticion de verdad.
      setTokenPendiente(token);
      return;
    }
    miMesa().then((resultado) => activo && setMesa(resultado));
    return () => {
      activo = false;
    };
  }, []);

  const entrar = useCallback(
    (nombre: string) => {
      if (!tokenPendiente) return;
      const idioma = (navigator.language || "es").slice(0, 2);
      entrarMesa(tokenPendiente, idioma, nombre.trim()).then(setMesa);
      const url = new URL(window.location.href);
      url.searchParams.delete("mesa");
      window.history.replaceState(null, "", url.toString());
      setTokenPendiente(null);
    },
    [tokenPendiente]
  );

  // Solo se sondea si hay una mesa que mirar: un cliente que abre la carta
  // sin escanear nada no genera trafico de mas.
  useEffect(() => {
    if (!mesa || mesa.estado === "cerrada") return;
    const id = window.setInterval(() => {
      if (!document.hidden) refrescar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [mesa, refrescar]);

  return { mesa, pidiendoNombre: tokenPendiente !== null, entrar };
}
