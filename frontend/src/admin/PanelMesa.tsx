import { useState } from "react";

import type { DatosQr } from "../shared/HojaQR";
import type { CambiosMesa, Mesa, Zona } from "./api";
import { PanelComandaMesa } from "./PanelComandaMesa";
import { TIPOS, girar, tipoDe } from "./planoUtil";
import { QrMesa } from "./QrMesa";

interface Props {
  mesa: Mesa;
  zonas: Zona[];
  qr: DatosQr;
  // Modo lápiz: se puede cambiar todo. En modo ojo solo se ve el estado y el QR.
  editando: boolean;
  // En el móvil el panel es una hoja que tapa el plano: solo se ve si se abrió.
  abiertoEnMovil: boolean;
  ocupado: boolean;
  onCambio: (cambios: CambiosMesa) => void;
  onEliminar: () => void;
  onCerrar: () => void;
  onRegenerar: (mesa: Mesa) => void;
}

// Datos de la mesa seleccionada en el plano. Se monta con key={mesa.id}: al
// tocar otra mesa el formulario arranca limpio.
export function PanelMesa({
  mesa,
  zonas,
  qr,
  editando,
  abiertoEnMovil,
  ocupado,
  onCambio,
  onEliminar,
  onCerrar,
  onRegenerar,
}: Props) {
  const [nombre, setNombre] = useState(mesa.nombre);

  function guardarNombre() {
    const limpio = nombre.trim();
    if (!limpio) {
      setNombre(mesa.nombre);
      return;
    }
    if (limpio !== mesa.nombre) onCambio({ nombre: limpio });
  }

  // El tipo lleva forma, tamaño y aforo juntos: no se retocan por separado.
  const tipo = tipoDe(mesa);

  function cambiarTipo(id: string) {
    const nuevo = TIPOS.find((t) => t.id === id);
    if (!nuevo) return;
    onCambio({
      forma: nuevo.forma,
      ancho: nuevo.ancho,
      alto: nuevo.alto,
      capacidad: nuevo.capacidad,
    });
  }

  return (
    <div className={"tarjeta panel-mesa" + (abiertoEnMovil ? "" : " oculto-movil")}>
      <div className="cabecera-panel">
        <h3>{mesa.nombre}</h3>
        <button type="button" className="cerrar-panel" aria-label="Cerrar" onClick={onCerrar}>
          <svg viewBox="0 0 24 24">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      <p className={"estado-mesa" + (mesa.ocupada ? " con-clientes" : "")}>
        {mesa.ocupada ? "Con clientes" : "Libre"} · {mesa.capacidad}{" "}
        {mesa.capacidad === 1 ? "persona" : "personas"}
      </p>

      {/* La misma comanda que en Servicio: es la misma mesa, no una vista
          aparte. Solo en modo servicio (ojo) y con la mesa ocupada. */}
      {!editando && mesa.ocupada && <PanelComandaMesa mesaId={mesa.id} />}

      {editando && (
        <>
      <label htmlFor="mesa-nombre">Nombre</label>
      <input
        id="mesa-nombre"
        value={nombre}
        maxLength={60}
        onChange={(e) => setNombre(e.target.value)}
        onBlur={guardarNombre}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />

      <label htmlFor="mesa-tipo">Tipo de mesa</label>
      <select
        id="mesa-tipo"
        value={tipo?.id ?? ""}
        disabled={ocupado}
        onChange={(e) => cambiarTipo(e.target.value)}
      >
        {/* Mesas hechas antes de los tipos: se ven, pero al cambiar pasan a uno. */}
        {!tipo && (
          <option value="" disabled>
            Otra ({mesa.capacidad} {mesa.capacidad === 1 ? "persona" : "personas"})
          </option>
        )}
        {TIPOS.map((t) => (
          <option key={t.id} value={t.id}>
            {t.etiqueta}
          </option>
        ))}
      </select>

      {zonas.length > 1 && (
        <>
          <label htmlFor="mesa-zona">Zona</label>
          <select
            id="mesa-zona"
            value={mesa.zona_id ?? ""}
            onChange={(e) => onCambio({ zona_id: e.target.value })}
          >
            {zonas.map((z) => (
              <option key={z.id} value={z.id}>
                {z.nombre}
              </option>
            ))}
          </select>
        </>
      )}

      <div className="acciones-mesa">
        <button
          type="button"
          className="secundario"
          disabled={ocupado}
          onClick={() => onCambio({ rotacion: girar(mesa.rotacion, -45) })}
        >
          ↺ Girar
        </button>
        <button
          type="button"
          className="secundario"
          disabled={ocupado}
          onClick={() => onCambio({ rotacion: girar(mesa.rotacion, 45) })}
        >
          Girar ↻
        </button>
      </div>
        </>
      )}

      <details className="mesa-qr">
        <summary>QR de esta mesa</summary>
        <QrMesa mesa={mesa} qr={qr} compacta={true} ocupado={ocupado} onRegenerar={onRegenerar} />
      </details>

      {editando && (
        <button
          type="button"
          className="secundario peligro"
          disabled={ocupado}
          onClick={onEliminar}
        >
          Eliminar mesa
        </button>
      )}
    </div>
  );
}
