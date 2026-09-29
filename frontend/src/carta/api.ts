import type {
  Categoria,
  Config,
  Grupo,
  Idiomas,
  MiMesa,
  Plato,
  Propuesta,
  TurnoHistorial,
} from "./types";

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
export async function entrarMesa(
  tokenQr: string,
  idioma: string,
  nombre?: string
): Promise<MiMesa | null> {
  try {
    const r = await fetch("/api/mesa/entrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ token_qr: tokenQr, idioma, nombre: nombre || undefined }),
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

// Aparte de /carta a proposito (ver api.py): solo hace falta al pulsar
// "Pedir" en un plato concreto.
export async function cargarGruposDePlato(platoId: string): Promise<Grupo[]> {
  return (await pedir<Grupo[]>(`/platos/${encodeURIComponent(platoId)}/grupos`)) ?? [];
}

export interface NuevaPropuesta {
  plato_id: string;
  formato?: string | null;
  opciones?: string[];
  cantidad?: number;
  nota?: string | null;
}

async function conCookie<T>(
  metodo: string,
  url: string,
  cuerpo?: unknown
): Promise<{ ok: boolean; status: number; datos: T | null }> {
  try {
    const r = await fetch(url, {
      method: metodo,
      credentials: "same-origin",
      headers: cuerpo === undefined ? undefined : { "Content-Type": "application/json" },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
    const datos = r.status === 204 ? null : ((await r.json().catch(() => null)) as T | null);
    return { ok: r.ok, status: r.status, datos };
  } catch {
    return { ok: false, status: 0, datos: null };
  }
}

export async function crearPropuesta(
  datos: NuevaPropuesta
): Promise<{ ok: boolean; status: number; propuesta: Propuesta | null }> {
  const r = await conCookie<Propuesta>("POST", "/api/mesa/propuestas", datos);
  return { ok: r.ok, status: r.status, propuesta: r.datos };
}

export async function listarPropuestas(): Promise<Propuesta[]> {
  const r = await conCookie<Propuesta[]>("GET", "/api/mesa/propuestas");
  return r.datos ?? [];
}

export async function quitarPropuesta(id: string): Promise<boolean> {
  const r = await conCookie("DELETE", `/api/mesa/propuestas/${encodeURIComponent(id)}`);
  return r.ok;
}

export async function confirmarPropuestas(): Promise<boolean> {
  const r = await conCookie("POST", "/api/mesa/propuestas/confirmar");
  return r.ok;
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
