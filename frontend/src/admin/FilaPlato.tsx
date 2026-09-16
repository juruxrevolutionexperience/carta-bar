import { useState } from "react";

import { actualizarDisponibilidad } from "./api";
import { FormularioPlato } from "./FormularioPlato";
import { TEXTO_DIETA, TEXTO_ETIQUETA, type ClaveDieta } from "./textos";
import type { Plato } from "./types";

interface Props {
  plato: Plato;
  nombreCategoria: string;
  onCambiado: (plato: Plato) => void;
  // Cubre dos casos con el mismo efecto sobre la lista del padre: se cancela
  // un especial que aun no tenia id, o se elimina uno que ya lo tenia.
  onQuitarDeLista: () => void;
}

function formatoPrecio(precio: number | null): string {
  return precio === null ? "a consultar" : `${precio.toFixed(2)} €`;
}

function resumenExtra(plato: Plato): string {
  const partes: string[] = [];
  if (plato.etiqueta) partes.push(TEXTO_ETIQUETA[plato.etiqueta] || plato.etiqueta);
  (Object.keys(TEXTO_DIETA) as ClaveDieta[]).forEach((clave) => {
    if (plato[clave]) partes.push(TEXTO_DIETA[clave]);
  });
  return partes.join(" · ");
}

export function FilaPlato({ plato, nombreCategoria, onCambiado, onQuitarDeLista }: Props) {
  // Un especial recien anadido (sin id todavia) se abre directo en edicion.
  const [editando, setEditando] = useState(plato.id === null);

  if (editando) {
    return (
      <FormularioPlato
        plato={plato}
        onGuardado={(nuevo) => {
          onCambiado(nuevo);
          setEditando(false);
        }}
        onCancelar={() => {
          if (!plato.id) {
            onQuitarDeLista();
            return;
          }
          setEditando(false);
        }}
        onEliminado={onQuitarDeLista}
      />
    );
  }

  const extra = resumenExtra(plato);
  const agotado = plato.disponible === false;

  async function alternarDisponible(checked: boolean) {
    if (!plato.id) return;
    try {
      const resp = await actualizarDisponibilidad(plato.id, checked);
      if (resp.status !== 204) return;
      onCambiado({ ...plato, disponible: checked });
    } catch {
      // Sin cambios: el checkbox controlado vuelve solo al valor de plato.disponible.
    }
  }

  return (
    <div className={"fila-plato" + (agotado ? " agotado" : "")}>
      <div className="info">
        <div className="nombre">
          {plato.nombre}
          {agotado && <span className="etiqueta-agotado">Agotado hoy</span>}
        </div>
        <div className="detalle">
          {nombreCategoria || plato.categoria} · {formatoPrecio(plato.precio)}
        </div>
        {extra && <div className="detalle-extra">{extra}</div>}
      </div>
      <label className="interruptor">
        <input
          type="checkbox"
          checked={!agotado}
          onChange={(e) => alternarDisponible(e.target.checked)}
        />
        <span className="riel"></span>
      </label>
      <button type="button" onClick={() => setEditando(true)}>
        Editar
      </button>
    </div>
  );
}
