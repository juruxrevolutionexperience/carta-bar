import type { ReactNode } from "react";

// Convierte "**texto**" en <strong>texto</strong> sin dangerouslySetInnerHTML:
// JSX escapa cada fragmento de texto solo, así que no hace falta escapar a mano.
export function formatearNegritas(texto: string): ReactNode[] {
  const partes = texto.split(/\*\*(.+?)\*\*/g);
  return partes.map((parte, i) => (i % 2 === 1 ? <strong key={i}>{parte}</strong> : parte));
}
