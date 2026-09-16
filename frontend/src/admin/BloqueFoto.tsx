import { useRef, useState } from "react";

import { borrarFoto, subirFoto } from "./api";
import { comprimirImagen } from "./comprimirImagen";
import type { Plato } from "./types";

interface Props {
  plato: Plato;
  onCambioFoto: (foto: string | null) => void;
}

export function BloqueFoto({ plato, onCambioFoto }: Props) {
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function subir() {
    const archivo = inputRef.current?.files?.[0];
    if (!archivo || !plato.id) return;
    setError(null);
    try {
      const blob = await comprimirImagen(archivo);
      const resp = await subirFoto(plato.id, blob);
      if (!resp.ok) throw new Error("fallo al subir");
      const datos = await resp.json();
      onCambioFoto(datos.foto);
    } catch {
      setError("No se pudo subir la foto.");
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function quitar() {
    if (!plato.id) return;
    setError(null);
    try {
      const resp = await borrarFoto(plato.id);
      if (resp.status !== 204) throw new Error("fallo al quitar");
      onCambioFoto(null);
    } catch {
      setError("No se pudo quitar la foto.");
    }
  }

  return (
    <div className="bloque-foto">
      {plato.foto ? (
        <img className="miniatura-foto" src={plato.foto} alt="" />
      ) : (
        <div className="miniatura-foto vacia">Sin foto</div>
      )}
      <div className="acciones-foto">
        <label className="boton-archivo">
          Subir foto
          <input ref={inputRef} type="file" accept="image/*" onChange={subir} />
        </label>
        {plato.foto && (
          <button type="button" onClick={quitar}>
            Quitar foto
          </button>
        )}
        {error && <div className="aviso visible error">{error}</div>}
      </div>
    </div>
  );
}
