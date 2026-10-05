// Copia deliberada de los tipos de carta_bar/comandas.py y carta_bar/cuentas.py
// (via admin/api.ts): esta pantalla vive en un aparato aparte, normalmente el
// mas modesto del bar, y conviene que no dependa del bundle grande del panel
// de gestion.
export type Destino = "cocina" | "barra";

// Que imprime este aparato: lo mismo que Destino, mas la cuenta. Aparte de
// Destino porque un Ticket nunca tiene destino "cuenta" (eso no existe en el
// backend); esto es solo la eleccion de la pantalla.
export type PantallaImpresion = Destino | "cuenta";

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
  anulada: boolean;
  motivo_anulacion: string | null;
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

export interface LineaCuenta {
  nombre_plato: string;
  formato: string | null;
  opciones: OpcionElegida[];
  cantidad: number;
  precio_unitario: number;
  total: number;
  pedido_por_nombre: string;
}

export interface ResumenPersonaCuenta {
  nombre: string;
  total: number;
}

// No es una factura (sin NIF ni numeracion fiscal): un resumen para que el
// cliente vea lo que paga. Nace al cobrar una mesa (carta_bar/cuentas.py).
export interface Cuenta {
  id: string;
  mesa_nombre: string;
  lineas: LineaCuenta[];
  por_persona: ResumenPersonaCuenta[];
  total: number;
  creada_en: string;
}
