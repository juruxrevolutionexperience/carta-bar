// Tema del panel: claro por defecto, oscuro si el gerente lo elige. Se guarda
// en este navegador (no en el servidor): cada aparato tiene el suyo, y el TPV
// del bar puede ir oscuro mientras el móvil del dueño va claro.
export type Tema = "claro" | "oscuro";

const CLAVE = "carta_tema_admin";

export function temaGuardado(): Tema {
  try {
    return localStorage.getItem(CLAVE) === "oscuro" ? "oscuro" : "claro";
  } catch {
    // Modo privado o almacenamiento bloqueado: se queda el claro de siempre.
    return "claro";
  }
}

// El claro es la ausencia de atributo: es lo que ya define :root en estilos.css.
export function aplicarTema(tema: Tema): void {
  if (tema === "oscuro") document.documentElement.dataset.tema = "oscuro";
  else delete document.documentElement.dataset.tema;
}

export function guardarTema(tema: Tema): void {
  try {
    localStorage.setItem(CLAVE, tema);
  } catch {
    // No se pudo recordar: el cambio vale igualmente hasta recargar.
  }
}
