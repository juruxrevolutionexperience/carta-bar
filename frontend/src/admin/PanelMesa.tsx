import { useState } from "react";

import type { DatosQr } from "../shared/HojaQR";
import type { CambiosMesa, Mesa, Zona } from "./api";
import { DISENO, FORMAS, girar, type FormaMesa } from "./planoUtil";
import { QrMesa } from "./QrMesa";

interface Props {
  mesa: Mesa;
  zonas: Zona[];
  qr: DatosQr;
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
  ocupado,
  onCambio,
  onEliminar,
  onCerrar,
  onRegenerar,
}: Props) {
  const [nombre, setNombre] = useState(mesa.nombre);
  const [capacidad, setCapacidad] = useState(String(mesa.capacidad));

  function guardarNombre() {
    const limpio = nombre.trim();
    if (!limpio) {
      setNombre(mesa.nombre);
      return;
    }
    if (limpio !== mesa.nombre) onCambio({ nombre: limpio });
  }

  function guardarCapacidad() {
    const n = Math.round(Number(capacidad));
    if (!Number.isFinite(n) || n < 1 || n > 30) {
      setCapacidad(String(mesa.capacidad));
      return;
    }
    if (n !== mesa.capacidad) onCambio({ capacidad: n });
  }

  function cambiarForma(forma: FormaMesa) {
    // Al cambiar de forma la mesa toma el tamano tipico de la nueva.
    onCambio({ forma, ancho: DISENO[forma].ancho, alto: DISENO[forma].alto });
  }

  return (
    <div className="tarjeta panel-mesa">
      <div className="cabecera-panel">
        <h3>{mesa.nombre}</h3>
        <button type="button" className="cerrar-panel" aria-label="Cerrar" onClick={onCerrar}>
          <svg viewBox="0 0 24 24">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      <label htmlFor="mesa-nombre">Nombre</label>
      <input
        id="mesa-nombre"
        value={nombre}
        maxLength={60}
        onChange={(e) => setNombre(e.target.value)}
        onBlur={guardarNombre}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />

      <label htmlFor="mesa-capacidad">Personas</label>
      <input
        id="mesa-capacidad"
        type="number"
        min={1}
        max={30}
        value={capacidad}
        onChange={(e) => setCapacidad(e.target.value)}
        onBlur={guardarCapacidad}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />

      <label htmlFor="mesa-forma">Forma</label>
      <select
        id="mesa-forma"
        value={mesa.forma}
        onChange={(e) => cambiarForma(e.target.value as FormaMesa)}
      >
        {FORMAS.map((f) => (
          <option key={f} value={f}>
            {DISENO[f].etiqueta}
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

      <details className="mesa-qr">
        <summary>QR de esta mesa</summary>
        <QrMesa mesa={mesa} qr={qr} compacta={true} ocupado={ocupado} onRegenerar={onRegenerar} />
      </details>

      <button type="button" className="secundario peligro" disabled={ocupado} onClick={onEliminar}>
        Eliminar mesa
      </button>
    </div>
  );
}
