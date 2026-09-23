// Reglas del plano, sin React: medidas de la cuadricula, tamanos de partida por
// forma y las cuentas de "donde cabe" y "como se llama la siguiente mesa".
// Aparte de los componentes para poder probarlas sin navegador.

export type FormaMesa = "redonda" | "cuadrada" | "rectangular" | "barril" | "taburete";

// El plano de cada zona es una cuadricula fija: cada casilla mide CELDA px.
export const COLUMNAS = 24;
export const FILAS = 18;
export const CELDA = 32;

// Mismos valores que DISENO_POR_FORMA en src/carta_bar/mesas.py.
export const DISENO: Record<
  FormaMesa,
  { ancho: number; alto: number; capacidad: number; etiqueta: string }
> = {
  redonda: { ancho: 2, alto: 2, capacidad: 4, etiqueta: "Redonda" },
  cuadrada: { ancho: 2, alto: 2, capacidad: 4, etiqueta: "Cuadrada" },
  rectangular: { ancho: 4, alto: 2, capacidad: 6, etiqueta: "Rectangular" },
  barril: { ancho: 1, alto: 1, capacidad: 2, etiqueta: "Barril" },
  taburete: { ancho: 1, alto: 1, capacidad: 1, etiqueta: "Taburete" },
};

export const FORMAS = Object.keys(DISENO) as FormaMesa[];

export interface Caja {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

// Las mesas se colocan y miden en casillas enteras: el "iman" a la cuadricula.
export function alinear(valor: number): number {
  return Math.round(valor);
}

export function limitarPosicion(x: number, y: number, ancho: number, alto: number) {
  return {
    x: Math.min(Math.max(x, 0), Math.max(COLUMNAS - ancho, 0)),
    y: Math.min(Math.max(y, 0), Math.max(FILAS - alto, 0)),
  };
}

// Tamano minimo de una casilla y sin salirse del plano desde su esquina.
export function limitarTamano(x: number, y: number, ancho: number, alto: number) {
  return {
    ancho: Math.min(Math.max(ancho, 1), COLUMNAS - x),
    alto: Math.min(Math.max(alto, 1), FILAS - y),
  };
}

function seSolapan(a: Caja, b: Caja): boolean {
  return a.x < b.x + b.ancho && b.x < a.x + a.ancho && a.y < b.y + b.alto && b.y < a.y + a.alto;
}

// Primer hueco libre (de arriba a abajo, de izquierda a derecha) donde cabe
// una mesa nueva sin taparse con otra. Si el plano esta lleno, la esquina.
export function huecoLibre(existentes: Caja[], ancho: number, alto: number) {
  for (let y = 0; y + alto <= FILAS; y++) {
    for (let x = 0; x + ancho <= COLUMNAS; x++) {
      const candidata = { x, y, ancho, alto };
      if (!existentes.some((otra) => seSolapan(candidata, otra))) return { x, y };
    }
  }
  return { x: 0, y: 0 };
}

// "Mesa N" con el menor N libre. Cuenta como usado tanto "Mesa 3" como un
// simple "3": hay bares que numeran sus mesas sin mas.
export function siguienteNombre(nombres: string[]): string {
  const usados = new Set<number>();
  for (const nombre of nombres) {
    const m = /^(?:mesa\s*)?(\d+)$/i.exec(nombre.trim());
    if (m) usados.add(Number(m[1]));
  }
  let n = 1;
  while (usados.has(n)) n++;
  return `Mesa ${n}`;
}

// Cuantos giros de 45 grados, siempre entre 0 y 359.
export function girar(rotacion: number, grados: number): number {
  return (((rotacion + grados) % 360) + 360) % 360;
}
