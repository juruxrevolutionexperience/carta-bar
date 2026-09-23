import { useCallback, useEffect, useState } from "react";

// "Mi lista": un recordatorio personal del cliente mientras mira la carta, no
// un pedido. Vive solo en su movil (localStorage), nunca en el servidor: no es
// el primer ladrillo de las comandas (docs/APARCADO-PEDIDO-EN-MESA.md), es una
// cosa mas pequena que no depende de esperar a que se cumpla ese requisito.
const CLAVE_BASE = "carta_lista_";

function clave(): string {
  return CLAVE_BASE + location.hostname;
}

function leer(): Record<string, number> {
  try {
    const guardado = localStorage.getItem(clave());
    return guardado ? JSON.parse(guardado) : {};
  } catch {
    return {};
  }
}

export function useListaCliente() {
  const [cantidades, setCantidades] = useState<Record<string, number>>(() => leer());

  useEffect(() => {
    try {
      localStorage.setItem(clave(), JSON.stringify(cantidades));
    } catch {
      // Sin sitio (modo privado, cuota llena...): la lista sigue funcionando
      // en memoria durante la visita, solo no sobrevive a recargar.
    }
  }, [cantidades]);

  const anadir = useCallback((platoId: string) => {
    setCantidades((actual) => ({ ...actual, [platoId]: (actual[platoId] || 0) + 1 }));
  }, []);

  const cambiar = useCallback((platoId: string, cantidad: number) => {
    setCantidades((actual) => {
      if (cantidad <= 0) {
        const { [platoId]: _fuera, ...resto } = actual;
        return resto;
      }
      return { ...actual, [platoId]: cantidad };
    });
  }, []);

  const vaciar = useCallback(() => setCantidades({}), []);

  const total = Object.values(cantidades).reduce((n, c) => n + c, 0);

  return { cantidades, total, anadir, cambiar, vaciar };
}
