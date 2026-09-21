import type { DatosQr } from "../shared/HojaQR";

export interface ResumenRestaurante {
  id: string;
  nombre: string;
  num_platos: number;
}

async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const resp = await fetch(input, init);
  if (resp.status === 401) {
    window.location.href = "/superadmin/login";
    throw new Error("sesion caducada");
  }
  return resp;
}

export async function listarRestaurantes(): Promise<ResumenRestaurante[]> {
  const resp = await apiFetch("/superadmin/api/restaurantes");
  return resp.json();
}

export async function cargarQrRestaurante(id: string): Promise<DatosQr> {
  const resp = await apiFetch(`/superadmin/api/restaurantes/${encodeURIComponent(id)}/qr`);
  if (!resp.ok) throw new Error("qr no disponible");
  return resp.json();
}

export interface MetricasBar {
  restaurante_id: string;
  nombre: string;
  visitas: number;
  preguntas: number;
  conversaciones: number;
  rechazadas: number;
  preguntas_por_idioma: Record<string, number>;
  coste_chat_usd: number;
  coste_traducciones_usd: number;
  coste_por_pregunta_usd: number | null;
}

export async function cargarMetricas(dias: number): Promise<MetricasBar[]> {
  const resp = await apiFetch(`/superadmin/api/metricas?dias=${dias}`);
  if (!resp.ok) throw new Error("metricas no disponibles");
  return resp.json();
}

export interface CuerpoNuevoRestaurante {
  restaurante_id: string;
  nombre: string;
  clave: string;
}

export async function crearRestaurante(cuerpo: CuerpoNuevoRestaurante): Promise<Response> {
  return apiFetch("/superadmin/api/restaurantes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });
}

export async function cerrarSesion(): Promise<void> {
  await fetch("/superadmin/logout", { method: "POST" });
  window.location.href = "/superadmin/login";
}
