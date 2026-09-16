export type Alergeno =
  | "gluten"
  | "crustaceos"
  | "huevos"
  | "pescado"
  | "cacahuetes"
  | "soja"
  | "lacteos"
  | "frutos_cascara"
  | "apio"
  | "mostaza"
  | "sesamo"
  | "sulfitos"
  | "altramuces"
  | "moluscos";

export type Etiqueta =
  | "mas_vendido"
  | "recomendacion_chef"
  | "nuevo"
  | "picante"
  | "para_compartir"
  | "temporada";

export interface Plato {
  id: string | null; // null solo mientras un especial nuevo no se ha guardado todavia
  nombre: string;
  descripcion: string;
  precio: number | null;
  categoria: string;
  ingredientes: string[];
  alergenos: Alergeno[];
  etiqueta: Etiqueta | null;
  vegano: boolean;
  vegetariano: boolean;
  sin_gluten: boolean;
  sin_lactosa: boolean;
  disponible: boolean;
  foto: string | null;
}

export interface Categoria {
  id: string;
  nombre: string;
  nombre_i18n: Record<string, string>;
  orden: number;
}

export const CATEGORIA_ESPECIALES = "especial-de-hoy";

export function platoVacio(): Plato {
  return {
    id: null,
    nombre: "",
    descripcion: "",
    precio: null,
    categoria: CATEGORIA_ESPECIALES,
    ingredientes: [],
    alergenos: [],
    etiqueta: null,
    vegano: false,
    vegetariano: false,
    sin_gluten: false,
    sin_lactosa: false,
    disponible: true,
    foto: null,
  };
}
