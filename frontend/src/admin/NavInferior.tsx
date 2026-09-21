export type Seccion = "platos" | "especiales" | "marca" | "cuenta";

interface Props {
  activa: Seccion;
  onCambiar: (seccion: Seccion) => void;
}

export function NavInferior({ activa, onCambiar }: Props) {
  return (
    <nav className="nav-inferior">
      <button
        type="button"
        className={"nav-item" + (activa === "platos" ? " activo" : "")}
        onClick={() => onCambiar("platos")}
      >
        <svg viewBox="0 0 24 24">
          <path d="M4 3v18M4 3c0 4 3 5 3 9s-3 5-3 9M20 3v18M20 8c-3 0-3 2-3 4s0 4 3 4" />
        </svg>
        Platos
      </button>
      <button
        type="button"
        className={"nav-item" + (activa === "especiales" ? " activo" : "")}
        onClick={() => onCambiar("especiales")}
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 3l2.6 5.9 6.4.6-4.8 4.3 1.4 6.2L12 16.9 6.4 20l1.4-6.2L3 9.5l6.4-.6z" />
        </svg>
        Especiales
      </button>
      <button
        type="button"
        className={"nav-item" + (activa === "marca" ? " activo" : "")}
        onClick={() => onCambiar("marca")}
      >
        <svg viewBox="0 0 24 24">
          <rect x="3" y="4" width="18" height="16" rx="2" />
          <circle cx="9" cy="10" r="2" />
          <path d="M21 16l-5-5-8 9" />
        </svg>
        Marca
      </button>
      <button
        type="button"
        className={"nav-item" + (activa === "cuenta" ? " activo" : "")}
        onClick={() => onCambiar("cuenta")}
      >
        <svg viewBox="0 0 24 24">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" />
        </svg>
        Cuenta
      </button>
    </nav>
  );
}
