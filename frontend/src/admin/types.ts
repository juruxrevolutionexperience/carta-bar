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
  // El restaurante ha revisado los alergenos y la dieta. Sin esto la carta
  // muestra "consultar alergenos" y el chat no lo recomienda ante una alergia.
  alergenos_confirmados: boolean;
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
    alergenos_confirmados: false,
  };
}

// Lo que el panel edita de /config: el resto (color, moneda...) no se toca aqui.
export interface ConfigMarca {
  nombre?: string;
  logo?: string;
  foto_portada?: string;
}

export type TipoImagenMarca = "logo" | "portada";
