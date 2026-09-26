import type { DatosQr } from "../shared/HojaQR";
import type { FormaMesa } from "./planoUtil";
import type { Alergeno, Categoria, ConfigMarca, Etiqueta, Plato, TipoImagenMarca } from "./types";

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

export async function cargarMarca(): Promise<ConfigMarca> {
  const resp = await fetch("/config");
  return resp.json();
}

export async function cambiarNombre(nombre: string): Promise<Response> {
  return apiFetch("/admin/api/marca", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  });
}

export async function subirImagenMarca(tipo: TipoImagenMarca, imagen: Blob): Promise<Response> {
  const formData = new FormData();
  formData.append("foto", imagen, `${tipo}.jpg`);
  return apiFetch(`/admin/api/marca/${tipo}`, { method: "POST", body: formData });
}

export async function quitarImagenMarca(tipo: TipoImagenMarca): Promise<Response> {
  return apiFetch(`/admin/api/marca/${tipo}`, { method: "DELETE" });
}

export async function cargarQr(): Promise<DatosQr> {
  const resp = await apiFetch("/admin/api/qr");
  return resp.json();
}

export async function guardarTextoQr(texto: string): Promise<Response> {
  return apiFetch("/admin/api/qr-texto", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto }),
  });
}

export interface Zona {
  id: string;
  nombre: string;
  orden: number;
}

export interface Mesa {
  id: string;
  nombre: string;
  token_qr: string;
  activa: boolean;
  zona_id: string | null;
  forma: FormaMesa;
  x: number;
  y: number;
  ancho: number;
  alto: number;
  rotacion: number;
  capacidad: number;
  // Hay clientes sentados. Lo calcula el servidor al listar; no se edita.
  ocupada?: boolean;
  // Igual que `ocupada`, calculado al listar: estado de su sesión, comensales
  // dentro y desde cuándo está abierta (ISO). Lo usa la pantalla de Servicio.
  estado?: EstadoMesa;
  comensales?: number;
  abierta_en?: string | null;
}

// "por_confirmar": la abrió un cliente con el QR y el camarero aún no ha salido
// a aceptarla. Nada de esa mesa llega a cocina hasta que la acepte.
export type EstadoMesa = "libre" | "por_confirmar" | "abierta" | "cuenta_pedida";

export interface SesionMesa {
  id: string;
  mesa_id: string;
  estado: Exclude<EstadoMesa, "libre"> | "cerrada";
  abierta_por: "cliente" | "personal";
  comensales_declarados: number | null;
  abierta_en: string | null;
  confirmada_en: string | null;
}

export interface Comensal {
  id: string;
  nombre: string;
  rol: "anfitrion" | "invitado";
  idioma: string;
  creado_en: string | null;
  expulsado_en: string | null;
}

export interface SesionConComensales {
  sesion: SesionMesa;
  comensales: Comensal[];
}

// Lo que se puede cambiar de una mesa desde el plano (el token y el estado no).
export type CambiosMesa = Partial<
  Pick<Mesa, "nombre" | "zona_id" | "forma" | "x" | "y" | "ancho" | "alto" | "rotacion" | "capacidad">
>;

export async function cargarMesas(): Promise<Mesa[]> {
  const resp = await apiFetch("/admin/api/mesas");
  return resp.json();
}

export async function cargarZonas(): Promise<Zona[]> {
  const resp = await apiFetch("/admin/api/zonas");
  return resp.json();
}

export async function crearZona(nombre: string): Promise<Response> {
  return apiFetch("/admin/api/zonas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  });
}

export async function renombrarZona(id: string, nombre: string): Promise<Response> {
  return apiFetch(`/admin/api/zonas/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  });
}

export async function ordenarZonas(ids: string[]): Promise<Response> {
  return apiFetch("/admin/api/orden-zonas", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
}

export async function eliminarZona(id: string): Promise<Response> {
  return apiFetch(`/admin/api/zonas/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function crearMesa(
  cuerpo: CambiosMesa & { nombre: string }
): Promise<Response> {
  return apiFetch("/admin/api/mesas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function actualizarMesa(id: string, cambios: CambiosMesa): Promise<Response> {
  return apiFetch(`/admin/api/mesas/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cambios),
  });
}

export async function eliminarMesa(id: string): Promise<Response> {
  return apiFetch(`/admin/api/mesas/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---- servicio: abrir, aceptar y liberar mesas, y quitar a un comensal

export async function cargarSesionMesa(mesaId: string): Promise<SesionConComensales | null> {
  const resp = await apiFetch(`/admin/api/mesas/${encodeURIComponent(mesaId)}/sesion`);
  // 404 = la mesa está libre (o se acaba de liberar): no es un error.
  if (resp.status === 404) return null;
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

export async function abrirMesa(mesaId: string, comensales: number | null): Promise<Response> {
  return apiFetch(`/admin/api/mesas/${encodeURIComponent(mesaId)}/abrir`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comensales }),
  });
}

export async function confirmarMesa(mesaId: string): Promise<Response> {
  return apiFetch(`/admin/api/mesas/${encodeURIComponent(mesaId)}/confirmar`, { method: "POST" });
}

export async function liberarMesa(mesaId: string): Promise<Response> {
  return apiFetch(`/admin/api/mesas/${encodeURIComponent(mesaId)}/liberar`, { method: "POST" });
}

export async function expulsarComensal(comensalId: string): Promise<Response> {
  return apiFetch(`/admin/api/comensales/${encodeURIComponent(comensalId)}/expulsar`, {
    method: "POST",
  });
}

export async function regenerarQrMesa(mesaId: string): Promise<Response> {
  return apiFetch(`/admin/api/mesas/${encodeURIComponent(mesaId)}/regenerar-qr`, {
    method: "POST",
  });
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
  alergenos_confirmados: boolean;
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

export async function crearPlato(cuerpo: CuerpoPlato & { categoria: string }): Promise<Response> {
  return apiFetch("/admin/api/platos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function crearCategoria(nombre: string): Promise<Response> {
  return apiFetch("/admin/api/categorias", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  });
}

export async function renombrarCategoria(id: string, nombre: string): Promise<Response> {
  return apiFetch(`/admin/api/categorias/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre }),
  });
}

export async function ordenarCategorias(ids: string[]): Promise<Response> {
  return apiFetch("/admin/api/orden-categorias", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
}

export async function eliminarCategoria(id: string): Promise<Response> {
  return apiFetch(`/admin/api/categorias/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function crearEspecial(cuerpo: CuerpoPlato): Promise<Response> {
  return apiFetch("/admin/api/platos/especiales", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function eliminarPlato(platoId: string): Promise<Response> {
  return apiFetch(`/admin/api/platos/${encodeURIComponent(platoId)}`, {
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
