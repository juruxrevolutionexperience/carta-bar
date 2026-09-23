import { useRef, useState, type PointerEvent } from "react";

import type { Mesa } from "./api";
import { CELDA, COLUMNAS, FILAS, alinear, limitarPosicion, limitarTamano, type Caja } from "./planoUtil";

interface Props {
  mesas: Mesa[];
  seleccionada: string | null;
  onSeleccionar: (id: string | null) => void;
  // Se llama una sola vez al soltar, con lo que cambio (posicion o tamano).
  onCambio: (mesa: Mesa, cambios: Partial<Caja>) => void;
}

interface Gesto {
  id: string;
  modo: "mover" | "tamano";
  inicioX: number;
  inicioY: number;
  origen: Caja;
  actual: Caja;
  movido: boolean;
}

// Por debajo de estos pixeles de desplazamiento es un toque, no un arrastre.
const UMBRAL_ARRASTRE = 4;

export function PlanoZona({ mesas, seleccionada, onSeleccionar, onCambio }: Props) {
  const [gesto, setGestoEstado] = useState<Gesto | null>(null);
  // Copia sincrona del gesto: entre dos eventos seguidos (un movimiento y el
  // soltar, por ejemplo) React puede no haber repintado aun, y el manejador
  // leeria una posicion un paso atrasada.
  const gestoRef = useRef<Gesto | null>(null);

  function setGesto(nuevo: Gesto | null) {
    gestoRef.current = nuevo;
    setGestoEstado(nuevo);
  }

  function empezar(e: PointerEvent<HTMLElement>, mesa: Mesa, modo: Gesto["modo"]) {
    e.stopPropagation();
    // La captura hace que el arrastre siga funcionando aunque el dedo salga de la mesa.
    e.currentTarget.setPointerCapture(e.pointerId);
    onSeleccionar(mesa.id);
    const origen = { x: mesa.x, y: mesa.y, ancho: mesa.ancho, alto: mesa.alto };
    setGesto({
      id: mesa.id,
      modo,
      inicioX: e.clientX,
      inicioY: e.clientY,
      origen,
      actual: origen,
      movido: false,
    });
  }

  function arrastrar(e: PointerEvent<HTMLElement>) {
    const gesto = gestoRef.current;
    if (!gesto) return;
    const dx = (e.clientX - gesto.inicioX) / CELDA;
    const dy = (e.clientY - gesto.inicioY) / CELDA;
    const { origen } = gesto;
    const actual: Caja =
      gesto.modo === "mover"
        ? {
            ...origen,
            ...limitarPosicion(
              alinear(origen.x + dx),
              alinear(origen.y + dy),
              origen.ancho,
              origen.alto
            ),
          }
        : {
            ...origen,
            ...limitarTamano(
              origen.x,
              origen.y,
              alinear(origen.ancho + dx),
              alinear(origen.alto + dy)
            ),
          };
    const movido =
      gesto.movido || Math.hypot(e.clientX - gesto.inicioX, e.clientY - gesto.inicioY) > UMBRAL_ARRASTRE;
    setGesto({ ...gesto, actual, movido });
  }

  function soltar() {
    const gesto = gestoRef.current;
    if (!gesto) return;
    const { id, modo, origen, actual, movido } = gesto;
    setGesto(null);
    if (!movido) return;
    const mesa = mesas.find((m) => m.id === id);
    if (!mesa) return;
    if (modo === "mover" && (actual.x !== origen.x || actual.y !== origen.y)) {
      onCambio(mesa, { x: actual.x, y: actual.y });
    } else if (modo === "tamano" && (actual.ancho !== origen.ancho || actual.alto !== origen.alto)) {
      onCambio(mesa, { ancho: actual.ancho, alto: actual.alto });
    }
  }

  return (
    <div className="plano-scroll">
      <div
        className="plano"
        style={{
          width: COLUMNAS * CELDA,
          height: FILAS * CELDA,
          backgroundSize: `${CELDA}px ${CELDA}px`,
        }}
        onPointerDown={(e) => {
          if (e.target === e.currentTarget) onSeleccionar(null);
        }}
        onPointerMove={arrastrar}
        onPointerUp={soltar}
        onPointerCancel={soltar}
      >
        {mesas.map((m) => {
          const c: Caja = gesto?.id === m.id ? gesto.actual : m;
          const elegida = seleccionada === m.id;
          return (
            <div
              key={m.id}
              className={
                `mesa-plano forma-${m.forma}` +
                (elegida ? " seleccionada" : "") +
                (gesto?.id === m.id ? " moviendo" : "")
              }
              style={{
                left: c.x * CELDA,
                top: c.y * CELDA,
                width: c.ancho * CELDA,
                height: c.alto * CELDA,
                transform: `rotate(${m.rotacion}deg)`,
              }}
              onPointerDown={(e) => empezar(e, m, "mover")}
            >
              {/* El texto contra-gira para leerse siempre derecho. */}
              <span className="mesa-nombre" style={{ transform: `rotate(${-m.rotacion}deg)` }}>
                {m.nombre}
              </span>
              {elegida && (
                <span
                  className="mesa-tirador"
                  aria-label="Cambiar el tamaño"
                  onPointerDown={(e) => empezar(e, m, "tamano")}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
