import { useEffect, useState } from "react";

import { entrarMesa, miMesa } from "./api";
import type { MiMesa } from "./types";

// Si la carta se abre con "?mesa=<token>" (el QR de la mesa), entra o se une
// a su sesión. Si no lleva ese parámetro pero ya hay una cookie de comensal
// (recarga de página, o se volvió a abrir la carta desde el mismo móvil), se
// recupera igualmente. Sin ninguna de las dos cosas, sigue como carta normal.
export function useMesa(): MiMesa | null {
  const [mesa, setMesa] = useState<MiMesa | null>(null);

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

  return mesa;
}
