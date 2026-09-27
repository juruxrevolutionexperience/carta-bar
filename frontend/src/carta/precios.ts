import type { Plato } from "./types";

export function importe(precio: number, moneda: string): string {
  return precio.toFixed(2).replace(".", ",") + " " + moneda;
}

// "Tapa 3,00 € · Ración 10,00 €" si el plato tiene formatos; si no, su precio
// de siempre (o "consultar"). Para donde solo cabe una linea (visor de fotos).
export function textoPrecio(p: Plato, moneda: string, consultar: string): string {
  if (p.formatos && p.formatos.length > 0) {
    return p.formatos.map((f) => `${f.nombre} ${importe(f.precio, moneda)}`).join(" · ");
  }
  return p.precio == null ? consultar : importe(Number(p.precio), moneda);
}
