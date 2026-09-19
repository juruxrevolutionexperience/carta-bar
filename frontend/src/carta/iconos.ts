import type { Plato } from "./types";

export const ICONO_CAT: Record<string, string> = {
  ensaladas: "🥗",
  tierra_y_mar: "🥩",
  hamburguesas: "🍔",
  postres: "🍰",
  tostas: "🥪",
  entrantes: "🫒",
  principales: "🍽️",
  panes: "🥖",
  bebidas: "🍷",
  brunch: "🍳",
  arroces: "🥘",
  pescados: "🐟",
  "especial-de-hoy": "⭐",
};

/* icono por palabra clave del plato, más específico que el de categoría */
const PISTAS: [RegExp, string][] = [
  [/salm[oó]n|lubina|rosada|boquer|atun|atún|ventresca|pescado/i, "🐟"],
  [/gamba|langostino|marisco|crust/i, "🦐"],
  [/queso|brie|cabra|mozzar|parmes|burrata|philad/i, "🧀"],
  [/huevo|tortilla|revuelto/i, "🥚"],
  [/jam[oó]n|ib[eé]rico|lomo|cerdo|morcilla|chorizo/i, "🥓"],
  [/angus|ternera|solomillo|costill|toro|carne/i, "🥩"],
  [/pollo|pavo/i, "🍗"],
  [/hamburgu|smash/i, "🍔"],
  [/ensalad|brotes|lechuga|caprese/i, "🥗"],
  [/aguacate|guacamole/i, "🥑"],
  [/tomate/i, "🍅"],
  [/brownie|chocolate/i, "🍫"],
  [/tarta|cheesecake|lotus/i, "🍰"],
  [/helado|sorbete/i, "🍨"],
  [/pan\b|tosta|picatos/i, "🥖"],
  [/patata/i, "🥔"],
  [/nuez|nueces|almendra/i, "🌰"],
  [/mermelada|miel/i, "🍯"],
];

const TONO: Record<string, [number, number]> = {
  ensaladas: [140, 42],
  tierra_y_mar: [8, 55],
  hamburguesas: [34, 72],
  postres: [318, 40],
  tostas: [36, 32],
  entrantes: [95, 38],
  principales: [262, 32],
  panes: [33, 38],
  bebidas: [290, 28],
  brunch: [38, 68],
};

export const ICONO_ETQ: Record<string, string> = {
  mas_vendido: "🔥",
  recomendacion_chef: "👨‍🍳",
  nuevo: "✨",
  picante: "🌶️",
  para_compartir: "🍽️",
  temporada: "🍂",
};

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

// Categorias fuera de TONO (nombres propios de cada restaurante, no se
// pueden prever todos) reciben un tono derivado de su propio id en vez de
// caer todas en el mismo color por defecto.
function tonoBase(catId: string): [number, number] {
  return TONO[catId] || [hash(catId) % 360, 38];
}

/* cada plato recibe una variación del tono de su categoría */
export function degradado(catId: string, semilla?: string): string {
  const base = tonoBase(catId);
  const giro = semilla ? (hash(semilla) % 26) - 13 : 0;
  const h = (base[0] + giro + 360) % 360;
  const s = base[1];
  return (
    "linear-gradient(140deg,hsl(" +
    h +
    " " +
    s +
    "% 92%) 0%,hsl(" +
    h +
    " " +
    s +
    "% 82%) 100%)"
  );
}

// Color solido (no degradado) para distinguir categorias en listas, no en
// tarjetas: mismo tono que degradado(), pensado para un borde o una insignia.
export function colorCategoria(catId: string): string {
  const [h, s] = tonoBase(catId);
  return `hsl(${h} ${s}% 45%)`;
}

export function iconoPlato(p: Plato): string {
  const texto = p.nombre + " " + (p.ingredientes || []).join(" ");
  for (const [re, ico] of PISTAS) if (re.test(texto)) return ico;
  return ICONO_CAT[p.categoria] || "🍽️";
}
