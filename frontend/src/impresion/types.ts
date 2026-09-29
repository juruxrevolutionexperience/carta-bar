// Copia deliberada de los tipos de carta_bar/comandas.py (via admin/api.ts):
// esta pantalla vive en un aparato aparte, normalmente el mas modesto del
// bar, y conviene que no dependa del bundle grande del panel de gestion.
export type Destino = "cocina" | "barra";

export interface OpcionElegida {
  nombre: string;
  precio: number;
}

export interface LineaTicket {
  id: string;
  nombre_plato: string;
  formato: string | null;
  cantidad: number;
  opciones: OpcionElegida[];
  nota: string | null;
  alcohol: boolean;
  pedido_por_nombre: string;
}

export interface Ticket {
  id: string;
  mesa_nombre: string;
  numero_comanda: number;
  destino: Destino;
  lineas: LineaTicket[];
  estado: "recibida" | "en_preparacion" | "servida";
  creado_en: string;
}
