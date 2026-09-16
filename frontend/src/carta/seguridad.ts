// La carta la escribe cada restaurante (dato no fiable), y acaba en el
// navegador de sus comensales. El texto ya lo escapa JSX solo; esto protege
// lo que JSX NO sanea: valores que se usan como src= o dentro de style=.

// Para src de imagenes: corta javascript:, vbscript: y data: que no sea imagen.
export function urlSegura(u: string | null | undefined): string {
  const s = String(u || "").trim();
  const permitida =
    /^https?:\/\//i.test(s) ||
    /^data:image\/(png|jpe?g|gif|webp|svg\+xml);/i.test(s) ||
    /^\/[^/\\]/.test(s);
  return permitida ? s : "";
}

// Para colores que se inyectan en CSS: solo hex y rgb()/hsl().
export function colorSeguro(c: string | null | undefined): string {
  const s = String(c || "").trim();
  const valido = /^#[0-9a-f]{3,8}$/i.test(s) || /^(rgb|hsl)a?\([0-9\s.,%/]+\)$/i.test(s);
  return valido ? s : "";
}
