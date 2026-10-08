import type { ReactElement } from "react";

import {
  IconBowl,
  IconLayoutGrid,
  IconPhoto,
  IconPlus,
  IconQrcode,
  IconStar,
  IconTable,
  IconToolsKitchen2,
  IconUserCircle,
} from "@tabler/icons-react";

export type Seccion =
  | "servicio"
  | "cocina"
  | "mesas"
  | "platos"
  | "especiales"
  | "extras"
  | "marca"
  | "qr"
  | "cuenta";

interface Entrada {
  id: Seccion;
  texto: string;
  icono: ReactElement;
  // Día a día (Sala): lo que el bar toca cada turno. Montaje (Carta y
  // Negocio): QR, marca, platos... lo configura el equipo de Carta Bar al
  // arrancar, no el camarero a diario, así que el menú lo guarda aparte.
  montaje: boolean;
}

const TAMANO_ICONO = 20;

// Un solo sitio donde vive el nombre, el icono y el grupo de cada sección: la
// barra superior y el menú lateral leen de aquí, así que no se pueden
// desincronizar al añadir comandas, cocina o camarero más adelante.
// Iconos de Tabler (la misma libreria que usa la plantilla Berry).
export const SECCIONES: Entrada[] = [
  // La primera es la que se abre al entrar: el día a día, no el montaje.
  {
    id: "servicio",
    texto: "Servicio",
    icono: <IconLayoutGrid size={TAMANO_ICONO} />,
    montaje: false,
  },
  {
    id: "cocina",
    texto: "Cocina",
    icono: <IconToolsKitchen2 size={TAMANO_ICONO} />,
    montaje: false,
  },
  {
    id: "mesas",
    texto: "Mesas",
    icono: <IconTable size={TAMANO_ICONO} />,
    montaje: false,
  },
  {
    id: "platos",
    texto: "Platos",
    icono: <IconBowl size={TAMANO_ICONO} />,
    montaje: true,
  },
  {
    id: "especiales",
    texto: "Especiales",
    icono: <IconStar size={TAMANO_ICONO} />,
    montaje: true,
  },
  {
    id: "extras",
    texto: "Extras y opciones",
    icono: <IconPlus size={TAMANO_ICONO} />,
    montaje: true,
  },
  {
    id: "marca",
    texto: "Marca",
    icono: <IconPhoto size={TAMANO_ICONO} />,
    montaje: true,
  },
  {
    id: "qr",
    texto: "Código QR",
    icono: <IconQrcode size={TAMANO_ICONO} />,
    montaje: true,
  },
  {
    id: "cuenta",
    texto: "Mi cuenta",
    icono: <IconUserCircle size={TAMANO_ICONO} />,
    montaje: true,
  },
];

export function tituloDe(seccion: Seccion): string {
  return SECCIONES.find((s) => s.id === seccion)?.texto ?? "";
}
