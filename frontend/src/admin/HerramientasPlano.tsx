import { ZOOM_MAX, ZOOM_MIN } from "./planoUtil";

interface Props {
  zoom: number;
  bloqueado: boolean;
  onZoom: (zoom: number) => void;
  onAjustar: () => void;
  onBloquear: () => void;
}

const PASO = 0.15;

export function HerramientasPlano({ zoom, bloqueado, onZoom, onAjustar, onBloquear }: Props) {
  return (
    <div className="herramientas-plano">
      <button
        type="button"
        className="boton-herramienta"
        aria-label="Alejar"
        disabled={zoom <= ZOOM_MIN}
        onClick={() => onZoom(zoom - PASO)}
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
        onClick={() => onZoom(zoom + PASO)}
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

      <span className="separador" />

      {/* Una vez el plano está montado, el gerente entra a diario a ver mesas,
          no a recolocarlas: el candado evita moverlas de un roce. */}
      <button
        type="button"
        className={"boton-herramienta" + (bloqueado ? " encendido" : "")}
        aria-label={bloqueado ? "Desbloquear el plano para mover mesas" : "Bloquear el plano"}
        aria-pressed={bloqueado}
        onClick={onBloquear}
      >
        {bloqueado ? (
          <svg viewBox="0 0 24 24">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 018 0v4" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 017.5-2" />
          </svg>
        )}
      </button>
    </div>
  );
}
