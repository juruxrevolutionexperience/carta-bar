import { useState } from "react";

import { aplicarTema, guardarTema, temaGuardado, type Tema } from "./tema";

interface Props {
  titulo: string;
  onAbrirMenu: () => void;
}

export function BarraSuperior({ titulo, onAbrirMenu }: Props) {
  const [tema, setTema] = useState<Tema>(temaGuardado);

  function alternar() {
    const nuevo: Tema = tema === "claro" ? "oscuro" : "claro";
    aplicarTema(nuevo);
    guardarTema(nuevo);
    setTema(nuevo);
  }

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
      <button
        type="button"
        className="boton-tema"
        aria-label={tema === "claro" ? "Cambiar al tema oscuro" : "Cambiar al tema claro"}
        title={tema === "claro" ? "Tema oscuro" : "Tema claro"}
        onClick={alternar}
      >
        {tema === "claro" ? (
          <svg viewBox="0 0 24 24">
            <path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6L7 7M17 17l1.4 1.4M5.6 18.4L7 17M17 7l1.4-1.4" />
          </svg>
        )}
      </button>
    </header>
  );
}
