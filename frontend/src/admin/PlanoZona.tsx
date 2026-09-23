import { useRef, useState, type CSSProperties, type PointerEvent } from "react";

import type { Mesa } from "./api";
import { SillasMesa } from "./SillasMesa";
import {
  CELDA,
  COLUMNAS,
  FILAS,
  alinear,
  detalleVisible,
  limitarPosicion,
  limitarTamano,
  pisaAlguna,
  type Caja,
} from "./planoUtil";

interface Props {
  mesas: Mesa[];
  seleccionada: string | null;
  zoom: number;
  bloqueado: boolean;
  onSeleccionar: (id: string | null) => void;
  // Se llama una sola vez al soltar, con lo que cambió (posición o tamaño).
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

// Por debajo de estos píxeles de desplazamiento es un toque, no un arrastre.
const UMBRAL_ARRASTRE = 4;

function IconoPersonas() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M16 5.2a3.2 3.2 0 010 5.6M18 14.4c1.8.9 3 2.7 3 5.6" />
    </svg>
  );
}

export function PlanoZona({
  mesas,
  seleccionada,
  zoom,
  bloqueado,
  onSeleccionar,
  onCambio,
}: Props) {
  const [gesto, setGestoEstado] = useState<Gesto | null>(null);
  // Copia síncrona del gesto: entre dos eventos seguidos (un movimiento y el
  // soltar, por ejemplo) React puede no haber repintado aún, y el manejador
  // leería una posición un paso atrasada.
  const gestoRef = useRef<Gesto | null>(null);

  function setGesto(nuevo: Gesto | null) {
    gestoRef.current = nuevo;
    setGestoEstado(nuevo);
  }

  function empezar(e: PointerEvent<HTMLElement>, mesa: Mesa, modo: Gesto["modo"]) {
    if (bloqueado) {
      onSeleccionar(mesa.id);
      return;
    }
    e.stopPropagation();
    // La captura hace que el arrastre siga aunque el dedo salga de la mesa.
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
    // Con el plano reducido, un mismo recorrido del dedo son más casillas.
    const paso = CELDA * zoom;
    const dx = (e.clientX - gesto.inicioX) / paso;
    const dy = (e.clientY - gesto.inicioY) / paso;
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
      gesto.movido ||
      Math.hypot(e.clientX - gesto.inicioX, e.clientY - gesto.inicioY) > UMBRAL_ARRASTRE;
    // Si ahi pisaria otra mesa, se queda en la ultima posicion buena en vez de
    // montarse encima: el plano se siente firme y no hay que deshacer nada.
    const otras = mesas.filter((m) => m.id !== gesto.id);
    const libre = !pisaAlguna(actual, otras);
    setGesto({ ...gesto, actual: libre ? actual : gesto.actual, movido });
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
      {/* El marco ocupa el tamaño ya escalado: es lo que hace que la barra de
          desplazamiento sepa cuánto plano hay al ampliar. */}
      <div
        style={{
          width: COLUMNAS * CELDA * zoom,
          height: FILAS * CELDA * zoom,
        }}
      >
        <div
          className={"plano" + (bloqueado ? " bloqueado" : "")}
          style={
            {
              width: COLUMNAS * CELDA,
              height: FILAS * CELDA,
              transform: `scale(${zoom})`,
              backgroundSize: `${CELDA}px ${CELDA}px`,
              // Los textos y el tirador se dividen por --z para conservar su
              // tamaño en pantalla aunque el plano esté reducido.
              "--z": zoom,
            } as CSSProperties
          }
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
            const detalle = detalleVisible(c.ancho, c.alto, zoom);
            return (
              <div
                key={m.id}
                className={
                  `mesa-plano forma-${m.forma}` +
                  (detalle === "minimo" ? " mini" : "") +
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
                <SillasMesa
                  forma={m.forma}
                  capacidad={m.capacidad}
                  ancho={c.ancho}
                  alto={c.alto}
                />
                {/* Contra-gira para leerse siempre derecho aunque la mesa no lo esté. */}
                <div className="mesa-cabecera" style={{ transform: `rotate(${-m.rotacion}deg)` }}>
                  <span className="mesa-etiqueta">{m.nombre}</span>
                  {detalle === "completo" && (
                    <span className="mesa-aforo">
                      <IconoPersonas />
                      {m.capacidad}
                    </span>
                  )}
                </div>
                {elegida && !bloqueado && (
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
    </div>
  );
}
