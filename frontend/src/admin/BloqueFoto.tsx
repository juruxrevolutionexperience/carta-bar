import { useRef, useState } from "react";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

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
    <Stack direction="row" spacing={2} alignItems="center">
      <Avatar variant="rounded" src={plato.foto ?? undefined} sx={{ width: 72, height: 72 }}>
        {!plato.foto && "Sin"}
      </Avatar>
      <Stack spacing={1}>
        <Stack direction="row" spacing={1}>
          <Button component="label" variant="outlined">
            Subir foto
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              onChange={subir}
              style={{ position: "absolute", width: 1, height: 1, opacity: 0, overflow: "hidden" }}
            />
          </Button>
          {plato.foto && (
            <Button variant="outlined" color="error" onClick={quitar}>
              Quitar foto
            </Button>
          )}
        </Stack>
        {error && <Alert severity="error">{error}</Alert>}
      </Stack>
    </Stack>
  );
}
