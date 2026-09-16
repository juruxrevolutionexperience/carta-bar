import type { Alergeno, Etiqueta } from "./types";

// Mismo texto que ya usa datos/idiomas.json (es.alergenos) y web/index.html
// (es.etiquetas) para el cliente. El panel es solo en espanol, sin pedirlo
// aparte a /idiomas.
export const TEXTO_ALERGENO: Record<Alergeno, string> = {
  gluten: "Gluten",
  crustaceos: "Crustáceos",
  huevos: "Huevo",
  pescado: "Pescado",
  cacahuetes: "Cacahuete",
  soja: "Soja",
  lacteos: "Lácteos",
  frutos_cascara: "Frutos secos",
  apio: "Apio",
  mostaza: "Mostaza",
  sesamo: "Sésamo",
  sulfitos: "Sulfitos",
  altramuces: "Altramuces",
  moluscos: "Moluscos",
};

export const TEXTO_ETIQUETA: Record<Etiqueta, string> = {
  mas_vendido: "Más vendido",
  recomendacion_chef: "Recomendación del chef",
  nuevo: "Nuevo",
  picante: "Picante",
  para_compartir: "Para compartir",
  temporada: "De temporada",
};

export const TEXTO_DIETA = {
  vegano: "Vegano",
  vegetariano: "Vegetariano",
  sin_gluten: "Sin gluten",
  sin_lactosa: "Sin lactosa",
} as const;

export type ClaveDieta = keyof typeof TEXTO_DIETA;
