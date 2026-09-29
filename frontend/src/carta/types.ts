export interface Plato {
  id: string;
  nombre: string;
  descripcion: string;
  descripcion_i18n?: Record<string, string>;
  precio: number | null;
  categoria: string;
  ingredientes: string[];
  alergenos: string[];
  etiqueta: string | null;
  vegano: boolean;
  vegetariano: boolean;
  sin_gluten: boolean;
  sin_lactosa: boolean;
  disponible: boolean;
  foto: string | null;
  // false = el restaurante aun no ha revisado sus alergenos y su dieta.
  alergenos_confirmados?: boolean;
  // Tapa, media, racion... con su precio. Vacio = se pide a `precio`. Nunca se
  // traducen: se piden al camarero por su nombre, como el plato.
  formatos?: Formato[];
}

export interface Formato {
  nombre: string;
  precio: number;
}

export interface Categoria {
  id: string;
  nombre: string;
  nombre_i18n: Record<string, string>;
  orden: number;
}

export interface Config {
  nombre?: string;
  subtitulo?: string;
  color_marca?: string;
  moneda?: string;
  foto_portada?: string;
  logo?: string;
  aviso_alergenos?: string;
  aviso_alergenos_i18n?: Record<string, string>;
}

export interface TextosIdioma {
  bandera?: string;
  nombre_idioma?: string;
  menu?: string;
  preguntar?: string;
  titulo_chat?: string;
  escribe?: string;
  enviar?: string;
  elige_idioma?: string;
  bienvenida_chat?: string;
  sugerencias?: string[];
  sin_platos?: string;
  precio_consultar?: string;
  consultar_alergenos?: string;
  mi_lista?: string;
  lista_vacia?: string;
  total?: string;
  vaciar_lista?: string;
  aviso_lista?: string;
  platos_uno?: string;
  platos_varios?: string;
  error_chat?: string;
  voz_hablar?: string;
  voz_parar?: string;
  voz_escuchando?: string;
  voz_sin_permiso?: string;
  alergenos?: Record<string, string>;
  etiquetas?: Record<string, string>;
  dietas?: Record<string, string>;
  [clave: string]: unknown;
}

export type Idiomas = Record<string, TextosIdioma>;

// Lo que se manda al backend en /preguntar: coincide con MensajeChat en
// src/carta_bar/modelos.py ("cliente"/"asistente", no confundir con las
// clases CSS .msg.yo/.msg.bot de la burbuja en pantalla).
export interface TurnoHistorial {
  rol: "cliente" | "asistente";
  texto: string;
}

// Una burbuja del hilo de chat en pantalla.
export interface MensajeUI {
  rol: "yo" | "bot";
  texto: string;
  pendiente?: boolean;
}

// Coincide con MiSesion en src/carta_bar/mesas.py.
export type EstadoSesionMesa = "por_confirmar" | "abierta" | "cuenta_pedida" | "cerrada";
export type RolComensal = "anfitrion" | "invitado";

export interface MiMesa {
  mesa: string;
  estado: EstadoSesionMesa;
  rol: RolComensal;
  nombre: string;
  comensales: string[];
}
