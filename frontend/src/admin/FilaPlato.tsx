import { useState } from "react";

import { actualizarDisponibilidad } from "./api";
import { FormularioPlato } from "./FormularioPlato";
import { TEXTO_DIETA, TEXTO_ETIQUETA, type ClaveDieta } from "./textos";
import type { Plato } from "./types";

// Lo que el gerente tiene que rellenar para que el plato se vea completo en
// la carta. Sirve de chuleta visual: sin entrar a editar, un vistazo a la
// miniatura y a este aviso le dice que le falta algo.
function faltaPorRellenar(plato: Plato): string[] {
  const falta: string[] = [];
  if (!plato.foto) falta.push("foto");
  if (plato.precio === null) falta.push("precio");
  if (!plato.descripcion.trim()) falta.push("descripción");
  return falta;
}

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
  const falta = faltaPorRellenar(plato);

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
      {plato.foto ? (
        <img className="miniatura-foto miniatura-fila" src={plato.foto} alt="" />
      ) : (
        <div className="miniatura-foto miniatura-fila vacia">Sin foto</div>
      )}
      <div className="info">
        <div className="nombre">
          {plato.nombre}
          {agotado && <span className="etiqueta-agotado">Agotado hoy</span>}
          {plato.alergenos_confirmados === false && (
            <span className="etiqueta-sin-confirmar">Alérgenos sin confirmar</span>
          )}
        </div>
        <div className="detalle">
          {nombreCategoria || plato.categoria} · {formatoPrecio(plato.precio)}
        </div>
        {extra && <div className="detalle-extra">{extra}</div>}
        {falta.length > 0 && (
          <div className="detalle-falta">Falta: {falta.join(", ")}</div>
        )}
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
