import type { ReactElement } from "react";

export type Seccion = "servicio" | "mesas" | "platos" | "especiales" | "marca" | "qr" | "cuenta";

interface Entrada {
  id: Seccion;
  texto: string;
  grupo: string;
  icono: ReactElement;
}

// Un solo sitio donde vive el nombre, el icono y el grupo de cada sección: la
// barra superior y el menú lateral leen de aquí, así que no se pueden
// desincronizar al añadir comandas, cocina o camarero más adelante.
export const SECCIONES: Entrada[] = [
  // La primera es la que se abre al entrar: el día a día, no el montaje.
  {
    id: "servicio",
    texto: "Servicio",
    grupo: "Sala",
    icono: (
      <svg viewBox="0 0 24 24">
        <rect x="3" y="3" width="8" height="8" rx="2" />
        <rect x="13" y="3" width="8" height="8" rx="2" />
        <rect x="3" y="13" width="8" height="8" rx="2" />
        <rect x="13" y="13" width="8" height="8" rx="2" />
      </svg>
    ),
  },
  {
    id: "mesas",
    texto: "Mesas",
    grupo: "Sala",
    icono: (
      <svg viewBox="0 0 24 24">
        <rect x="3" y="4" width="18" height="11" rx="2" />
        <path d="M7 19v-4M17 19v-4" />
      </svg>
    ),
  },
  {
    id: "platos",
    texto: "Platos",
    grupo: "Carta",
    icono: (
      <svg viewBox="0 0 24 24">
        <path d="M4 3v18M4 3c0 4 3 5 3 9s-3 5-3 9M20 3v18M20 8c-3 0-3 2-3 4s0 4 3 4" />
      </svg>
    ),
  },
  {
    id: "especiales",
    texto: "Especiales",
    grupo: "Carta",
    icono: (
      <svg viewBox="0 0 24 24">
        <path d="M12 3l2.6 5.9 6.4.6-4.8 4.3 1.4 6.2L12 16.9 6.4 20l1.4-6.2L3 9.5l6.4-.6z" />
      </svg>
    ),
  },
  {
    id: "marca",
    texto: "Marca",
    grupo: "Negocio",
    icono: (
      <svg viewBox="0 0 24 24">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="9" cy="10" r="2" />
        <path d="M21 16l-5-5-8 9" />
      </svg>
    ),
  },
  {
    id: "qr",
    texto: "Código QR",
    grupo: "Negocio",
    icono: (
      <svg viewBox="0 0 24 24">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <path d="M14 14h3v3h-3zM20 14v3M14 20h3M20 20h1" />
      </svg>
    ),
  },
  {
    id: "cuenta",
    texto: "Mi cuenta",
    grupo: "Negocio",
    icono: (
      <svg viewBox="0 0 24 24">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" />
      </svg>
    ),
  },
];

export function tituloDe(seccion: Seccion): string {
  return SECCIONES.find((s) => s.id === seccion)?.texto ?? "";
}
