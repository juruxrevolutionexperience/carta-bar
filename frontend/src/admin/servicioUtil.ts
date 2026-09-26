import type { EstadoMesa, Mesa, Zona } from "./api";

// Cómo se dice cada estado en la tarjeta. "Por aceptar" y no "por confirmar":
// es lo que hace el camarero, salir a la mesa y aceptarla.
export const TEXTO_ESTADO: Record<EstadoMesa, string> = {
  libre: "Libre",
  por_confirmar: "Por aceptar",
  abierta: "Abierta",
  cuenta_pedida: "Pide la cuenta",
};

export function estadoDe(mesa: Mesa): EstadoMesa {
  return mesa.estado ?? (mesa.ocupada ? "abierta" : "libre");
}

// "Mesa 2" antes que "Mesa 10", como las numeraría cualquiera.
const ORDEN_NATURAL = new Intl.Collator("es", { numeric: true, sensitivity: "base" });

export interface GrupoZona {
  zona: Zona;
  mesas: Mesa[];
}

export function agruparPorZona(zonas: Zona[], mesas: Mesa[]): GrupoZona[] {
  return [...zonas]
    .sort((a, b) => a.orden - b.orden)
    .map((zona) => ({
      zona,
      mesas: mesas
        .filter((m) => m.zona_id === zona.id)
        .sort((a, b) => ORDEN_NATURAL.compare(a.nombre, b.nombre)),
    }));
}

export function contarPorEstado(mesas: Mesa[]): Record<EstadoMesa, number> {
  const cuenta: Record<EstadoMesa, number> = {
    libre: 0,
    por_confirmar: 0,
    abierta: 0,
    cuenta_pedida: 0,
  };
  for (const m of mesas) cuenta[estadoDe(m)] += 1;
  return cuenta;
}

// "3 min", "1 h 20". Lo justo para saber de un vistazo qué mesa lleva más rato.
export function tiempoDesde(iso: string | null | undefined, ahora: number): string {
  if (!iso) return "";
  const minutos = Math.max(0, Math.floor((ahora - new Date(iso).getTime()) / 60000));
  if (minutos < 1) return "ahora";
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas} h` : `${horas} h ${String(resto).padStart(2, "0")}`;
}

export function personas(n: number): string {
  return `${n} ${n === 1 ? "persona" : "personas"}`;
}
