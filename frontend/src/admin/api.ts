import type { Alergeno, Categoria, Etiqueta, Plato } from "./types";

// Centraliza lo que en la version anterior se repetia en cada fetch: si la
// sesion caduco a mitad de uso, el servidor devuelve 401 y aqui se manda a
// login una sola vez, en vez de en cada llamada por separado.
async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const resp = await fetch(input, init);
  if (resp.status === 401) {
    window.location.href = "/admin/login";
    // La redireccion es async: esto evita que el resto del codigo intente
    // seguir usando una respuesta que ya sabemos que no sirve.
    throw new Error("sesion caducada");
  }
  return resp;
}

export async function cargarCarta(): Promise<Plato[]> {
  const resp = await fetch("/carta");
  return resp.json();
}

export async function cargarCategorias(): Promise<Categoria[]> {
  const resp = await fetch("/categorias");
  return resp.json();
}

export async function actualizarDisponibilidad(
  platoId: string,
  disponible: boolean
): Promise<Response> {
  return apiFetch(`/admin/api/platos/${encodeURIComponent(platoId)}/disponibilidad`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ disponible }),
  });
}

export interface CuerpoPlato {
  nombre: string;
  descripcion: string;
  precio: number | null;
  ingredientes: string[];
  alergenos: Alergeno[];
  etiqueta: Etiqueta | null;
  vegano: boolean;
  vegetariano: boolean;
  sin_gluten: boolean;
  sin_lactosa: boolean;
}

export async function guardarPlatoExistente(
  platoId: string,
  cuerpo: CuerpoPlato
): Promise<Response> {
  return apiFetch(`/admin/api/platos/${encodeURIComponent(platoId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function crearEspecial(cuerpo: CuerpoPlato): Promise<Response> {
  return apiFetch("/admin/api/platos/especiales", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function eliminarEspecial(platoId: string): Promise<Response> {
  return apiFetch(`/admin/api/platos/especiales/${encodeURIComponent(platoId)}`, {
    method: "DELETE",
  });
}

export async function subirFoto(platoId: string, foto: Blob): Promise<Response> {
  const formData = new FormData();
  formData.append("foto", foto, `${platoId}.jpg`);
  return apiFetch(`/admin/api/platos/${encodeURIComponent(platoId)}/foto`, {
    method: "POST",
    body: formData,
  });
}

export async function borrarFoto(platoId: string): Promise<Response> {
  return apiFetch(`/admin/api/platos/${encodeURIComponent(platoId)}/foto`, {
    method: "DELETE",
  });
}

export async function cambiarClave(
  claveActual: string,
  claveNueva: string
): Promise<Response> {
  return fetch("/admin/cambiar-clave", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clave_actual: claveActual, clave_nueva: claveNueva }),
  });
}

export async function cerrarSesion(): Promise<void> {
  await fetch("/admin/logout", { method: "POST" });
  window.location.href = "/admin/login";
}
