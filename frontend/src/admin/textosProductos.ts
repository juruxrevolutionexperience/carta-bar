import type { DatosGrupo } from "./api";

// "Obligatorio · elige 1", "Opcional · hasta 3": cómo se lee un grupo de un vistazo.
export function resumenGrupo(g: Pick<DatosGrupo, "minimo" | "maximo">): string {
  if (g.minimo === 0) return g.maximo === 1 ? "opcional · uno" : `opcional · hasta ${g.maximo}`;
  if (g.minimo === g.maximo) return `obligatorio · elige ${g.minimo}`;
  return `obligatorio · de ${g.minimo} a ${g.maximo}`;
}

export function textoPrecio(precio: number): string {
  return precio === 0 ? "gratis" : `+${precio.toFixed(2).replace(".", ",")} €`;
}
