import { useRef, useState } from "react";

import Avatar from "@mui/material/Avatar";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

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
    <Stack direction="row" spacing={2} alignItems="center">
      <Avatar variant="rounded" src={previa ?? undefined} sx={{ width: 72, height: 72 }}>
        {!previa && "Sin"}
      </Avatar>
      <Stack spacing={1}>
        <Stack direction="row" spacing={1}>
          <Button component="label" variant="outlined">
            Subir foto
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              onChange={manejarCambio}
              style={{ position: "absolute", width: 1, height: 1, opacity: 0, overflow: "hidden" }}
            />
          </Button>
          {archivo && (
            <Button variant="outlined" color="error" onClick={quitar}>
              Quitar foto
            </Button>
          )}
        </Stack>
        <Typography sx={{ fontSize: 11, color: "text.secondary" }}>Se sube al guardar</Typography>
      </Stack>
    </Stack>
  );
}
