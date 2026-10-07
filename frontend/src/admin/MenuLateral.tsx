import { useEffect, useRef, useState } from "react";

import { SECCIONES, type Seccion } from "./secciones";

interface Props {
  activa: Seccion;
  abierto: boolean;
  onCambiar: (seccion: Seccion) => void;
  onCerrar: () => void;
}

const CLAVE_MONTAJE_ABIERTO = "cartaBar.menu.montajeAbierto";

function item(
  s: (typeof SECCIONES)[number],
  activa: Seccion,
  abierto: boolean,
  onElegir: () => void,
) {
  return (
    <button
      key={s.id}
      type="button"
      className={
        "item-menu" +
        (s.id === activa ? " activo" : "") +
        // Mesas es para montar el local: en el movil no aporta nada que no
        // tenga ya Servicio, y el plano ahi no se maneja bien con el dedo.
        (s.id === "mesas" ? " solo-escritorio" : "")
      }
      aria-current={s.id === activa ? "page" : undefined}
      tabIndex={abierto ? undefined : -1}
      onClick={onElegir}
    >
      {s.icono}
      {s.texto}
    </button>
  );
}

export function MenuLateral({ activa, abierto, onCambiar, onCerrar }: Props) {
  const panel = useRef<HTMLElement>(null);
  // Montaje (QR, marca, platos...) lo deja listo el equipo de Carta Bar al
  // arrancar: el camarero no lo toca a diario, así que empieza plegado y
  // fuera de en medio del día a día (Servicio, Cocina, Mesas).
  const [montajeAbierto, setMontajeAbierto] = useState(() => {
    try {
      return localStorage.getItem(CLAVE_MONTAJE_ABIERTO) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(CLAVE_MONTAJE_ABIERTO, montajeAbierto ? "1" : "0");
    } catch {
      // Sin almacenamiento: no pasa nada, simplemente no se recuerda entre visitas.
    }
  }, [montajeAbierto]);

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

  const diaADia = SECCIONES.filter((s) => !s.montaje);
  const montaje = SECCIONES.filter((s) => s.montaje);

  function elegir(id: Seccion) {
    onCambiar(id);
    onCerrar();
  }

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

        {diaADia.map((s) => item(s, activa, abierto, () => elegir(s.id)))}

        <button
          type="button"
          className="toggle-montaje"
          aria-expanded={montajeAbierto}
          tabIndex={abierto ? undefined : -1}
          onClick={() => setMontajeAbierto((v) => !v)}
        >
          <span>Montaje</span>
          <svg
            viewBox="0 0 24 24"
            className={montajeAbierto ? "giro" : ""}
            aria-hidden="true"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        {montajeAbierto &&
          montaje.map((s) => item(s, activa, abierto, () => elegir(s.id)))}
      </nav>
    </>
  );
}
