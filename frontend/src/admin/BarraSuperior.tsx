interface Props {
  titulo: string;
  onAbrirMenu: () => void;
}

export function BarraSuperior({ titulo, onAbrirMenu }: Props) {
  return (
    <header className="barra-superior">
      <button
        type="button"
        className="boton-menu"
        aria-label="Abrir el menú"
        onClick={onAbrirMenu}
      >
        <svg viewBox="0 0 24 24">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>
      <span className="titulo-barra">{titulo}</span>
      <span className="marca-barra">Carta Bar</span>
    </header>
  );
}
