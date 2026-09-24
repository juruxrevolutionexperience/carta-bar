import {
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent,
  type TouchEvent,
} from "react";

import type { Mesa } from "./api";
import { SillasMesa } from "./SillasMesa";
import {
  CELDA,
  COLUMNAS,
  FILAS,
  alinear,
  detalleVisible,
  etiquetaPlano,
  limitarPosicion,
  limitarZoom,
  pisaAlguna,
  type Caja,
} from "./planoUtil";

interface Props {
  mesas: Mesa[];
  seleccionada: string | null;
  zoom: number;
  // Cada vez que cambia, el plano se centra en las mesas de la zona (al abrir
  // en el móvil, donde no cabe entero con las mesas legibles).
  centrar: number;
  // Modo lápiz: se mueven mesas y se ve la guía. Sin él (modo ojo, el de
  // servicio) las mesas solo se tocan para ver sus datos.
  editando: boolean;
  onSeleccionar: (id: string | null) => void;
  // Un toque en una mesa al editar (sin arrastrarla). `yaElegida` dice si ya lo
  // estaba antes de tocar: así el primer toque solo la elige y el segundo abre
  // sus datos, y arrastrar no abre nada.
  onToque: (id: string, yaElegida: boolean) => void;
  // Zoom pedido con los dedos (pellizco).
  onZoom: (zoom: number) => void;
  // Se llama una sola vez al soltar, con la posición nueva.
  onCambio: (mesa: Mesa, cambios: Partial<Caja>) => void;
}

interface Gesto {
  id: string;
  inicioX: number;
  inicioY: number;
  origen: Caja;
  actual: Caja;
  movido: boolean;
  // Ya estaba elegida antes de tocarla: un segundo toque (sin arrastrar) abre
  // sus datos; el primero solo la elige.
  yaElegida: boolean;
}

// Recorrer el plano con un dedo y acercar/alejar con dos. Se hace a mano (con
// touch-action: none en el marco) para que funcione igual en el móvil y en la
// pantalla táctil del bar, y para que arrastrar una mesa no mueva el plano.
type Dedos =
  | { modo: "desplazar"; x: number; y: number; izquierda: number; arriba: number }
  | {
      modo: "pellizco";
      distancia: number;
      zoomInicio: number;
      // Punto del plano (sin zoom) que había bajo los dedos al empezar: se
      // mantiene bajo los dedos mientras se acerca o aleja.
      px: number;
      py: number;
    };

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

function distancia(e: TouchEvent<HTMLElement>): number {
  const [a, b] = [e.touches[0], e.touches[1]];
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
}

function medio(e: TouchEvent<HTMLElement>): { x: number; y: number } {
  const [a, b] = [e.touches[0], e.touches[1]];
  return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 };
}

export function PlanoZona({
  mesas,
  seleccionada,
  zoom,
  centrar,
  editando,
  onSeleccionar,
  onToque,
  onZoom,
  onCambio,
}: Props) {
  const [gesto, setGestoEstado] = useState<Gesto | null>(null);
  // Copia síncrona del gesto: entre dos eventos seguidos (un movimiento y el
  // soltar, por ejemplo) React puede no haber repintado aún, y el manejador
  // leería una posición un paso atrasada.
  const gestoRef = useRef<Gesto | null>(null);
  const marco = useRef<HTMLDivElement>(null);
  const dedos = useRef<Dedos | null>(null);
  // Dónde tiene que quedar el plano tras el próximo cambio de zoom del pellizco.
  const ancla = useRef<{ px: number; py: number; mx: number; my: number } | null>(null);
  const ultimoCentrado = useRef(-1);

  function setGesto(nuevo: Gesto | null) {
    gestoRef.current = nuevo;
    setGestoEstado(nuevo);
  }

  // Con el zoom ya aplicado (el marco ya mide lo nuevo), se coloca el plano:
  // bajo los dedos si viene de un pellizco, o centrado en las mesas si se pidió.
  useLayoutEffect(() => {
    const el = marco.current;
    if (!el) return;
    const a = ancla.current;
    if (a) {
      el.scrollLeft = a.px * zoom - a.mx;
      el.scrollTop = a.py * zoom - a.my;
      ancla.current = null;
      return;
    }
    if (centrar === ultimoCentrado.current) return;
    ultimoCentrado.current = centrar;
    let cx = (COLUMNAS * CELDA) / 2;
    let cy = (FILAS * CELDA) / 2;
    if (mesas.length > 0) {
      const minX = Math.min(...mesas.map((m) => m.x));
      const maxX = Math.max(...mesas.map((m) => m.x + m.ancho));
      const minY = Math.min(...mesas.map((m) => m.y));
      const maxY = Math.max(...mesas.map((m) => m.y + m.alto));
      cx = ((minX + maxX) / 2) * CELDA;
      cy = ((minY + maxY) / 2) * CELDA;
    }
    el.scrollLeft = cx * zoom - el.clientWidth / 2;
    el.scrollTop = cy * zoom - el.clientHeight / 2;
  }, [zoom, centrar, mesas]);

  function tocarMarco(e: TouchEvent<HTMLDivElement>) {
    const el = marco.current;
    if (!el) return;
    if (e.touches.length >= 2) {
      // Si un dedo empezó sobre una mesa (al editar), el pellizco manda.
      if (gestoRef.current) setGesto(null);
      const caja = el.getBoundingClientRect();
      const m = medio(e);
      dedos.current = {
        modo: "pellizco",
        distancia: distancia(e),
        zoomInicio: zoom,
        px: (el.scrollLeft + m.x - caja.left) / zoom,
        py: (el.scrollTop + m.y - caja.top) / zoom,
      };
      return;
    }
    // Al editar, un dedo sobre una mesa la arrastra: el plano no se mueve.
    const sobreMesa = (e.target as HTMLElement).closest(".mesa-plano");
    if (editando && sobreMesa) {
      dedos.current = null;
      return;
    }
    const t = e.touches[0];
    dedos.current = {
      modo: "desplazar",
      x: t.clientX,
      y: t.clientY,
      izquierda: el.scrollLeft,
      arriba: el.scrollTop,
    };
  }

  function moverDedos(e: TouchEvent<HTMLDivElement>) {
    const el = marco.current;
    const d = dedos.current;
    if (!el || !d) return;
    if (d.modo === "pellizco" && e.touches.length >= 2) {
      const nuevo = limitarZoom((d.zoomInicio * distancia(e)) / d.distancia);
      const caja = el.getBoundingClientRect();
      const m = medio(e);
      ancla.current = { px: d.px, py: d.py, mx: m.x - caja.left, my: m.y - caja.top };
      onZoom(nuevo);
    } else if (d.modo === "desplazar") {
      const t = e.touches[0];
      el.scrollLeft = d.izquierda - (t.clientX - d.x);
      el.scrollTop = d.arriba - (t.clientY - d.y);
    }
  }

  function levantarDedos(e: TouchEvent<HTMLDivElement>) {
    const el = marco.current;
    if (!el || e.touches.length === 0) {
      dedos.current = null;
      return;
    }
    // Queda un dedo tras el pellizco: sigue desplazando desde ahí, sin saltos.
    const t = e.touches[0];
    dedos.current = {
      modo: "desplazar",
      x: t.clientX,
      y: t.clientY,
      izquierda: el.scrollLeft,
      arriba: el.scrollTop,
    };
  }

  function empezar(e: PointerEvent<HTMLElement>, mesa: Mesa) {
    // En servicio el toque lo recoge onClick: así el dedo puede recorrer el
    // plano aunque empiece encima de una mesa.
    if (!editando) return;
    e.stopPropagation();
    // La captura hace que el arrastre siga aunque el dedo salga de la mesa.
    e.currentTarget.setPointerCapture(e.pointerId);
    const yaElegida = seleccionada === mesa.id;
    onSeleccionar(mesa.id);
    const origen = { x: mesa.x, y: mesa.y, ancho: mesa.ancho, alto: mesa.alto };
    setGesto({
      id: mesa.id,
      inicioX: e.clientX,
      inicioY: e.clientY,
      origen,
      actual: origen,
      movido: false,
      yaElegida,
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
    const actual: Caja = {
      ...origen,
      ...limitarPosicion(alinear(origen.x + dx), alinear(origen.y + dy), origen.ancho, origen.alto),
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
    const { id, origen, actual, movido, yaElegida } = gesto;
    setGesto(null);
    if (!movido) {
      onToque(id, yaElegida);
      return;
    }
    const mesa = mesas.find((m) => m.id === id);
    if (mesa && (actual.x !== origen.x || actual.y !== origen.y)) {
      onCambio(mesa, { x: actual.x, y: actual.y });
    }
  }

  return (
    <div
      className="plano-scroll"
      ref={marco}
      onTouchStart={tocarMarco}
      onTouchMove={moverDedos}
      onTouchEnd={levantarDedos}
      onTouchCancel={levantarDedos}
    >
      {/* El marco ocupa el tamaño ya escalado: es lo que hace que la barra de
          desplazamiento sepa cuánto plano hay al ampliar. */}
      <div
        style={{
          width: COLUMNAS * CELDA * zoom,
          height: FILAS * CELDA * zoom,
          // Si sobra ancho (pantalla muy apaisada), el plano queda centrado.
          margin: "0 auto",
        }}
      >
        <div
          className={"plano" + (editando ? " edicion" : "")}
          style={
            {
              width: COLUMNAS * CELDA,
              height: FILAS * CELDA,
              transform: `scale(${zoom})`,
              // Guía cada 4 unidades y solo al editar: en servicio el plano es
              // un local limpio, sin cuadrícula.
              backgroundSize: `${CELDA * 4}px ${CELDA * 4}px`,
              // Los textos se dividen por --z para conservar su tamaño en
              // pantalla aunque el plano esté reducido.
              "--z": zoom,
            } as CSSProperties
          }
          // onClick y no onPointerDown: un toque para recorrer el plano no debe
          // cerrar la mesa elegida; el navegador solo da click si no hubo arrastre.
          onClick={(e) => {
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
                  (m.ocupada ? " ocupada" : "") +
                  (gesto?.id === m.id ? " moviendo" : "")
                }
                title={m.nombre}
                style={{
                  left: c.x * CELDA,
                  top: c.y * CELDA,
                  width: c.ancho * CELDA,
                  height: c.alto * CELDA,
                  transform: `rotate(${m.rotacion}deg)`,
                }}
                onPointerDown={(e) => empezar(e, m)}
                onClick={() => {
                  if (!editando) onSeleccionar(m.id);
                }}
              >
                <SillasMesa
                  forma={m.forma}
                  capacidad={m.capacidad}
                  ancho={c.ancho}
                  alto={c.alto}
                />
                {/* Contra-gira para leerse siempre derecho aunque la mesa no lo esté.
                    Nombre centrado, como en un TPV; el aforo solo en las grandes y,
                    si hay clientes, el icono de personas en la esquina. */}
                {detalle !== "minimo" && (
                  <div className="mesa-centro" style={{ transform: `rotate(${-m.rotacion}deg)` }}>
                    <span className="mesa-etiqueta">{etiquetaPlano(m.nombre)}</span>
                    {detalle === "completo" && (
                      <span className="mesa-aforo">
                        <IconoPersonas />
                        {m.capacidad}
                      </span>
                    )}
                  </div>
                )}
                {m.ocupada && detalle !== "minimo" && (
                  <span className="mesa-ocupada-icono" title="Con clientes">
                    <IconoPersonas />
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
