import { ZOOM_FACTOR, ZOOM_MAX, ZOOM_MIN } from "./planoUtil";

interface Props {
  zoom: number;
  onZoom: (zoom: number) => void;
  onAjustar: () => void;
}

// Solo mueven la vista del plano; qué se puede tocar lo decide el modo (ojo o
// lápiz), no esta barra.
export function HerramientasPlano({ zoom, onZoom, onAjustar }: Props) {
  return (
    <div className="herramientas-plano">
      <button
        type="button"
        className="boton-herramienta"
        aria-label="Alejar"
        disabled={zoom <= ZOOM_MIN}
        onClick={() => onZoom(zoom / ZOOM_FACTOR)}
      >
        <svg viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-4.3-4.3M8 11h6" />
        </svg>
      </button>
      <span className="nivel-zoom">{Math.round(zoom * 100)}%</span>
      <button
        type="button"
        className="boton-herramienta"
        aria-label="Acercar"
        disabled={zoom >= ZOOM_MAX}
        onClick={() => onZoom(zoom * ZOOM_FACTOR)}
      >
        <svg viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-4.3-4.3M8 11h6M11 8v6" />
        </svg>
      </button>
      <button
        type="button"
        className="boton-herramienta"
        aria-label="Ver el plano entero"
        onClick={onAjustar}
      >
        <svg viewBox="0 0 24 24">
          <path d="M4 9V5a1 1 0 011-1h4M15 4h4a1 1 0 011 1v4M20 15v4a1 1 0 01-1 1h-4M9 20H5a1 1 0 01-1-1v-4" />
        </svg>
      </button>
    </div>
  );
}
