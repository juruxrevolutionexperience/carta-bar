import { useRef, useState } from "react";

// Para un plato que todavia no existe en el servidor no hay donde subir la
// foto (el endpoint necesita su id). Aqui solo se guarda el archivo elegido
// y se ensena una vista previa local; FormularioPlato la sube de verdad
// justo despues de crear el plato, en el mismo "Guardar".
interface Props {
  archivo: File | null;
  onSeleccionar: (archivo: File | null) => void;
}

export function SelectorFotoNueva({ archivo, onSeleccionar }: Props) {
  const [previa, setPrevia] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function manejarCambio() {
    const elegido = inputRef.current?.files?.[0] ?? null;
    onSeleccionar(elegido);
    if (!elegido) {
      setPrevia(null);
      return;
    }
    const lector = new FileReader();
    lector.onload = () => setPrevia(lector.result as string);
    lector.readAsDataURL(elegido);
  }

  function quitar() {
    onSeleccionar(null);
    setPrevia(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="bloque-foto">
      {previa ? (
        <img className="miniatura-foto" src={previa} alt="" />
      ) : (
        <div className="miniatura-foto vacia">Sin foto</div>
      )}
      <div className="acciones-foto">
        <label className="boton-archivo">
          Subir foto
          <input ref={inputRef} type="file" accept="image/*" onChange={manejarCambio} />
        </label>
        {archivo && (
          <button type="button" onClick={quitar}>
            Quitar foto
          </button>
        )}
        <span style={{ fontSize: "11px", color: "var(--tinta-media)" }}>
          Se sube al guardar
        </span>
      </div>
    </div>
  );
}
