import { useEffect, useRef } from "react";

import { SECCIONES, type Seccion } from "./secciones";

interface Props {
  activa: Seccion;
  abierto: boolean;
  onCambiar: (seccion: Seccion) => void;
  onCerrar: () => void;
}

export function MenuLateral({ activa, abierto, onCambiar, onCerrar }: Props) {
  const panel = useRef<HTMLElement>(null);

  // Escape cierra el menú: en escritorio es el gesto esperado, y el menú tapa
  // media pantalla mientras está abierto.
  useEffect(() => {
    if (!abierto) return;
    const alPulsar = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCerrar();
    };
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [abierto, onCerrar]);

  let grupoAnterior = "";

  return (
    <>
      {/* El velo solo existe mientras el menú está abierto: si no, taparía la
          página entera e impediría tocar nada. En escritorio no se muestra. */}
      {abierto && (
        <div className="velo-menu visible" onClick={onCerrar} aria-hidden="true" />
      )}
      <nav
        ref={panel}
        className={"menu-lateral" + (abierto ? " abierto" : "")}
        aria-label="Secciones del panel"
        // Oculto al lector de pantalla mientras está cerrado en móvil; en
        // escritorio la hoja de estilos lo deja siempre visible y esto no aplica.
        aria-hidden={abierto ? undefined : "true"}
      >
        <div className="cabecera-menu">
          <div className="nombre">Carta Bar</div>
          <div className="sub">Panel de gestión</div>
        </div>

        {SECCIONES.map((s) => {
          const cabecera = s.grupo !== grupoAnterior ? s.grupo : null;
          grupoAnterior = s.grupo;
          return (
            <div key={s.id}>
              {cabecera && <div className="grupo-menu">{cabecera}</div>}
              <button
                type="button"
                className={"item-menu" + (s.id === activa ? " activo" : "")}
                aria-current={s.id === activa ? "page" : undefined}
                tabIndex={abierto ? undefined : -1}
                onClick={() => {
                  onCambiar(s.id);
                  onCerrar();
                }}
              >
                {s.icono}
                {s.texto}
              </button>
            </div>
          );
        })}
      </nav>
    </>
  );
}
