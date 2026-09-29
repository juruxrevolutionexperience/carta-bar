import type { Categoria, Config, Idiomas, MiMesa, Plato, TurnoHistorial } from "./types";

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

// Al escanear el QR de una mesa: crea o une la sesión y deja una cookie de
// comensal (httpOnly, la pone el backend). Idempotente: volver a llamar con
// el mismo token de una mesa ya abierta simplemente une a quien pregunta.
export async function entrarMesa(tokenQr: string, idioma: string): Promise<MiMesa | null> {
  try {
    const r = await fetch("/api/mesa/entrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ token_qr: tokenQr, idioma }),
    });
    if (!r.ok) return null;
    return await miMesa();
  } catch {
    return null;
  }
}

// Estado de la mesa de quien pregunta (según la cookie de comensal). 401 (o
// sin cookie) = no está en ninguna mesa: sigue como carta normal.
export async function miMesa(): Promise<MiMesa | null> {
  try {
    const r = await fetch("/api/mesa/yo", { credentials: "same-origin" });
    return r.ok ? ((await r.json()) as MiMesa) : null;
  } catch {
    return null;
  }
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
