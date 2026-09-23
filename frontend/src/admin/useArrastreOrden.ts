import { useRef, useState, type PointerEvent } from "react";

// Reordenar una lista vertical arrastrando con el dedo (o el raton) el asa de
// cada fila. Lo comparten las categorias y las zonas del plano: la fila sobre
// la que esta el puntero pasa a ser el destino de la arrastrada, y el orden
// definitivo solo se entrega al soltar.
interface Arrastre {
  id: string;
  orden: string[];
}

export function useArrastreOrden<T extends { id: string }>(
  base: T[],
  alSoltar: (ordenados: T[]) => void,
  bloqueado: boolean
) {
  // Orden provisional (ids) mientras dura el arrastre; null = sin arrastre.
  const [arrastre, setArrastreEstado] = useState<Arrastre | null>(null);
  // Copia sincrona: el soltar puede llegar antes de que React repinte el ultimo
  // movimiento, y no debe guardar un orden un paso atrasado.
  const arrastreRef = useRef<Arrastre | null>(null);
  const filas = useRef<Map<string, HTMLElement>>(new Map());

  const lista = arrastre
    ? arrastre.orden.map((id) => base.find((x) => x.id === id)).filter((x): x is T => !!x)
    : base;

  function setArrastre(nuevo: Arrastre | null) {
    arrastreRef.current = nuevo;
    setArrastreEstado(nuevo);
  }

  function refFila(id: string) {
    return (el: HTMLElement | null) => {
      if (el) filas.current.set(id, el);
      else filas.current.delete(id);
    };
  }

  function empezar(e: PointerEvent<HTMLElement>, id: string) {
    if (bloqueado) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    setArrastre({ id, orden: base.map((x) => x.id) });
  }

  function mover(e: PointerEvent<HTMLElement>) {
    const arrastre = arrastreRef.current;
    if (!arrastre) return;
    const destino = arrastre.orden.find((id) => {
      const caja = filas.current.get(id)?.getBoundingClientRect();
      return caja !== undefined && e.clientY >= caja.top && e.clientY <= caja.bottom;
    });
    if (destino === undefined || destino === arrastre.id) return;
    const siguiente = arrastre.orden.filter((id) => id !== arrastre.id);
    siguiente.splice(arrastre.orden.indexOf(destino), 0, arrastre.id);
    setArrastre({ id: arrastre.id, orden: siguiente });
  }

  function soltar() {
    const arrastre = arrastreRef.current;
    if (!arrastre) return;
    const nuevoOrden = arrastre.orden;
    setArrastre(null);
    if (nuevoOrden.every((id, i) => id === base[i]?.id)) return;
    alSoltar(nuevoOrden.map((id) => base.find((x) => x.id === id)!));
  }

  // Propiedades para el boton "asa" de cada fila.
  function asa(id: string) {
    return {
      onPointerDown: (e: PointerEvent<HTMLElement>) => empezar(e, id),
      onPointerMove: mover,
      onPointerUp: soltar,
      onPointerCancel: soltar,
    };
  }

  return { lista, arrastrandoId: arrastre?.id ?? null, refFila, asa };
}
