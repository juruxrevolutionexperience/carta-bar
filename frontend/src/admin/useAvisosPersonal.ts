import { useEffect, useRef, useState } from "react";

import { cargarMesas } from "./api";
import { estadoDe } from "./servicioUtil";

const REFRESCO_MS = 5000;

export interface AvisoPersonal {
  clave: string;
  mesaId: string;
  nombre: string;
  tipo: "nueva" | "cuenta";
}

// Pitido corto generado al vuelo (sin archivo de audio que mantener). Si el
// navegador bloquea el audio por no haber habido todavia un toque del
// usuario, falla en silencio: el aviso visual sigue funcionando igual.
function pitido() {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const ganancia = ctx.createGain();
    osc.connect(ganancia);
    ganancia.connect(ctx.destination);
    osc.frequency.value = 880;
    ganancia.gain.setValueAtTime(0.0001, ctx.currentTime);
    ganancia.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.01);
    ganancia.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.3);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
    osc.onended = () => void ctx.close();
  } catch {
    // Sin audio: no pasa nada, el aviso visual (la lista de abajo) sigue.
  }
}

// Mesa nueva por aceptar, o que pide la cuenta: vivo en todo el panel (se
// monta una vez en App.tsx, no por seccion), para que suene este donde este
// el camarero: en Servicio, en Mesas o en Cocina. Refleja el estado actual,
// no un historial: en cuanto se acepta o se cobra, el aviso desaparece solo.
export function useAvisosPersonal(): AvisoPersonal[] {
  const [activos, setActivos] = useState<AvisoPersonal[]>([]);
  const vistos = useRef<Set<string>>(new Set());
  const primera = useRef(true);

  useEffect(() => {
    let cancelado = false;

    async function sondear() {
      const mesas = await cargarMesas().catch(() => null);
      if (!mesas || cancelado) return;

      const actuales: AvisoPersonal[] = [];
      for (const m of mesas) {
        const estado = estadoDe(m);
        if (estado === "por_confirmar") {
          actuales.push({ clave: `${m.id}:nueva`, mesaId: m.id, nombre: m.nombre, tipo: "nueva" });
        }
        if (estado === "cuenta_pedida") {
          actuales.push({ clave: `${m.id}:cuenta`, mesaId: m.id, nombre: m.nombre, tipo: "cuenta" });
        }
      }

      // Solo pita por lo que es nuevo desde el ultimo sondeo, no cada vez que
      // refresca con lo mismo de antes todavia pendiente.
      if (!primera.current) {
        const hayNuevos = actuales.some((a) => !vistos.current.has(a.clave));
        if (hayNuevos) pitido();
      }
      primera.current = false;
      vistos.current = new Set(actuales.map((a) => a.clave));
      setActivos(actuales);
    }

    void sondear();
    const id = window.setInterval(() => {
      if (!document.hidden) void sondear();
    }, REFRESCO_MS);
    return () => {
      cancelado = true;
      window.clearInterval(id);
    };
  }, []);

  return activos;
}
