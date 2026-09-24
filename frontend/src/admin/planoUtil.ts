// Reglas del plano, sin React: medidas de la cuadricula, tamanos de partida por
// forma y las cuentas de "donde cabe" y "como se llama la siguiente mesa".
// Aparte de los componentes para poder probarlas sin navegador.

export type FormaMesa = "redonda" | "cuadrada" | "rectangular" | "barril" | "taburete";

// El plano de cada zona mide 48 x 30 unidades y cada unidad son CELDA px a zoom
// 1. Es fino a proposito, como el mapa de mesas de un TPV: el local entero a la
// vista y mesas pequenas (una de 4 mide 3 de 48 unidades, la dieciseisava parte
// del ancho), con sitio para decenas de mesas, barriles y taburetes. En el
// movil se ve entero y se acerca con el zoom para leer o mover algo.
export const COLUMNAS = 48;
export const FILAS = 30;
export const CELDA = 20;

// Mismos valores que DISENO_POR_FORMA en src/carta_bar/mesas.py.
export const DISENO: Record<
  FormaMesa,
  { ancho: number; alto: number; capacidad: number; etiqueta: string }
> = {
  redonda: { ancho: 3, alto: 3, capacidad: 4, etiqueta: "Redonda" },
  cuadrada: { ancho: 3, alto: 3, capacidad: 4, etiqueta: "Cuadrada" },
  rectangular: { ancho: 6, alto: 3, capacidad: 6, etiqueta: "Rectangular" },
  barril: { ancho: 2, alto: 2, capacidad: 2, etiqueta: "Barril" },
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
// El Math.max exterior es obligatorio: con una mesa colocada fuera de la
// cuadricula (por ejemplo, guardada cuando el plano era mas grande),
// COLUMNAS - x sale negativo y devolvia anchos negativos.
export function limitarTamano(x: number, y: number, ancho: number, alto: number) {
  return {
    ancho: Math.max(1, Math.min(Math.max(ancho, 1), COLUMNAS - x)),
    alto: Math.max(1, Math.min(Math.max(alto, 1), FILAS - y)),
  };
}

/**
 * Mete una mesa dentro de la cuadricula actual. Hace falta porque el plano se
 * ha achicado (era de 24x18): una mesa guardada en la esquina de antes caeria
 * fuera y quedaria invisible e imposible de tocar. Devuelve null si ya estaba
 * bien, para no reescribir en el servidor lo que no ha cambiado.
 */
export function corregirSiSeSale(caja: Caja): Caja | null {
  const { ancho, alto } = limitarTamano(
    Math.min(caja.x, COLUMNAS - 1),
    Math.min(caja.y, FILAS - 1),
    caja.ancho,
    caja.alto
  );
  const { x, y } = limitarPosicion(caja.x, caja.y, ancho, alto);
  if (x === caja.x && y === caja.y && ancho === caja.ancho && alto === caja.alto) return null;
  return { x, y, ancho, alto };
}

export function seSolapan(a: Caja, b: Caja): boolean {
  return a.x < b.x + b.ancho && b.x < a.x + a.ancho && a.y < b.y + b.alto && b.y < a.y + a.alto;
}

/** Si la caja pisa alguna de las otras. Las mesas no se montan unas sobre otras. */
export function pisaAlguna(caja: Caja, otras: Caja[]): boolean {
  return otras.some((otra) => seSolapan(caja, otra));
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

// --------------------------------------------------------------- zoom

// El minimo deja ver el plano entero en un movil estrecho (unos 360 px de
// ancho dan 0,37); el maximo, leer y mover una mesa con el dedo.
export const ZOOM_MIN = 0.2;
export const ZOOM_MAX = 3;
// Cada pulsacion de acercar/alejar multiplica: con un rango tan grande, sumar
// una cantidad fija se quedaria corto al alejar y se pasaria al acercar.
export const ZOOM_FACTOR = 1.25;

export function limitarZoom(z: number): number {
  return Math.min(Math.max(z, ZOOM_MIN), ZOOM_MAX);
}

// Zoom al que el plano entero cabe en el hueco disponible. Mira el alto ademas
// del ancho: en una pantalla apaisada solo el ancho daba un zoom tan grande que
// las mesas de abajo quedaban cortadas. Se redondea hacia abajo a centesimas
// para que no asome una franja por un pixel de redondeo.
export function zoomQueCabe(anchoDisponible: number, altoDisponible: number): number {
  const porAncho = anchoDisponible / (COLUMNAS * CELDA);
  const porAlto = altoDisponible / (FILAS * CELDA);
  return limitarZoom(Math.floor(Math.min(porAncho, porAlto) * 100) / 100);
}

// --------------------------------------------- que cabe escrito en una mesa

/** Ancho que ocupa una mesa en la pantalla, ya contando el zoom. */
export function anchoEnPantalla(anchoCasillas: number, zoom: number): number {
  return anchoCasillas * CELDA * zoom;
}

/**
 * Que se puede escribir dentro de una mesa segun el sitio que tenga en
 * pantalla. Sin esto, con el plano alejado el nombre y el aforo se pisaban y
 * quedaban en "T..." y una rayita.
 */
export function detalleVisible(
  anchoCasillas: number,
  altoCasillas: number,
  zoom: number
): "completo" | "solo-nombre" | "minimo" {
  const ancho = anchoEnPantalla(anchoCasillas, zoom);
  const alto = anchoEnPantalla(altoCasillas, zoom);
  // Como en un TPV: lo normal es solo el nombre (el numero) en el centro; el
  // aforo, solo en mesas grandes; y en las diminutas nada (sale al acercar).
  if (ancho < 26 || alto < 20) return "minimo";
  if (ancho < 90 || alto < 44) return "solo-nombre";
  return "completo";
}

/**
 * Lo que se escribe dentro de la mesa en el plano. Como en un TPV: solo el
 * numero ("4"), no "Mesa 4". El nombre completo sigue en el panel de la mesa y
 * en el texto que ve el lector de pantalla; otros nombres ("Terraza 4",
 * "Barra") se ven tal cual.
 */
export function etiquetaPlano(nombre: string): string {
  const m = /^mesa\s*(\d+)$/i.exec(nombre.trim());
  return m ? m[1] : nombre;
}

/**
 * Nombre que se propone al soltar una forma nueva. Un barril o un taburete
 * ocupan una casilla y ahi no cabe "Mesa 6": se quedan en el numero pelado.
 */
export function nombreParaForma(forma: FormaMesa, nombresUsados: string[]): string {
  const propuesto = siguienteNombre(nombresUsados);
  if (forma === "barril" || forma === "taburete") {
    return propuesto.replace(/^Mesa\s*/i, "");
  }
  return propuesto;
}

// ------------------------------------------------------------------ sillas

/**
 * Cuantas sillas van en cada lado (arriba, derecha, abajo, izquierda) de una
 * mesa rectangular. Se reparten en proporcion a lo que mide cada lado, asi que
 * una mesa alargada pone casi todas arriba y abajo, como en la vida real.
 *
 * Dibujar las sillas es lo que permite ver de un golpe si una mesa es de 2 o
 * de 6, sin tener que leer el numero.
 */
export function repartirSillas(
  capacidad: number,
  ancho: number,
  alto: number
): [number, number, number, number] {
  const n = Math.max(0, Math.min(Math.round(capacidad), 24));
  if (n === 0) return [0, 0, 0, 0];

  // Peso de cada lado: arriba y abajo miden `ancho`; los costados, `alto`.
  const pesos = [ancho, alto, ancho, alto];
  const total = pesos.reduce((a, b) => a + b, 0);
  const exactos = pesos.map((p) => (n * p) / total);
  const lados = exactos.map(Math.floor);

  // Las que sobran por el redondeo van a los lados con mas resto pendiente,
  // para que la suma sea exactamente la capacidad y no una aproximacion.
  // A igualdad de resto se prefieren lados opuestos (arriba/abajo antes que
  // los costados): una mesa de 2 queda con las sillas enfrentadas, como se
  // sienta la gente, y no las dos en esquina.
  const preferencia = [0, 2, 1, 3]; // arriba, abajo, derecha, izquierda
  let faltan = n - lados.reduce((a, b) => a + b, 0);
  const orden = exactos
    .map((valor, i) => ({ i, resto: valor - Math.floor(valor) }))
    .sort((a, b) => b.resto - a.resto || preferencia.indexOf(a.i) - preferencia.indexOf(b.i));
  let k = 0;
  while (faltan > 0) {
    lados[orden[k % 4].i] += 1;
    faltan -= 1;
    k += 1;
  }
  return lados as [number, number, number, number];
}

/** Posiciones (0..1) de `n` sillas repartidas a lo largo de un lado. */
export function repartirALoLargo(n: number): number[] {
  return Array.from({ length: n }, (_, i) => (i + 1) / (n + 1));
}
