import type { Categoria, Config, Idiomas, Plato, TurnoHistorial } from "./types";

async function pedir<T>(url: string): Promise<T | null> {
  try {
    const r = await fetch(url);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

export async function cargarCarta(idioma?: string): Promise<Plato[] | null> {
  return pedir<Plato[]>(idioma ? `/carta?idioma=${idioma}` : "/carta");
}

export async function cargarCategorias(): Promise<Categoria[] | null> {
  return pedir<Categoria[]>("/categorias");
}

export async function cargarConfig(): Promise<Config | null> {
  return pedir<Config>("/config");
}

export async function cargarIdiomas(): Promise<Idiomas | null> {
  return pedir<Idiomas>("/idiomas");
}

export async function preguntar(
  texto: string,
  idioma: string,
  historial: TurnoHistorial[]
): Promise<string> {
  const r = await fetch("/preguntar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // El historial va SIN el mensaje actual: el backend lo recibe aparte.
    body: JSON.stringify({ texto, idioma, historial }),
  });
  const d = await r.json();
  return d.respuesta;
}
