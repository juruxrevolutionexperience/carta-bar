import { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";

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
    <Stack
      direction="row"
      alignItems="center"
      spacing={1.5}
      sx={{
        py: 1.5,
        borderBottom: 1,
        borderColor: "divider",
        opacity: agotado ? 0.6 : 1,
      }}
    >
      {plato.foto ? (
        <Avatar variant="rounded" src={plato.foto} alt="" sx={{ width: 56, height: 56 }} />
      ) : (
        <Avatar variant="rounded" sx={{ width: 56, height: 56, fontSize: 11 }}>
          Sin foto
        </Avatar>
      )}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
          <Typography sx={{ fontSize: 14.5, fontWeight: 600 }}>{plato.nombre}</Typography>
          {agotado && <Chip label="Agotado hoy" size="small" color="error" variant="outlined" />}
          {plato.alergenos_confirmados === false && (
            <Chip label="Alérgenos sin confirmar" size="small" color="warning" variant="outlined" />
          )}
        </Stack>
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
          {nombreCategoria || plato.categoria} · {formatoPrecio(plato.precio)}
        </Typography>
        {extra && (
          <Typography sx={{ fontSize: 12.5, color: "text.secondary" }}>{extra}</Typography>
        )}
        {falta.length > 0 && (
          <Typography sx={{ fontSize: 12.5, color: "warning.dark", fontWeight: 600 }}>
            Falta: {falta.join(", ")}
          </Typography>
        )}
      </Box>
      <Switch checked={!agotado} onChange={(e) => alternarDisponible(e.target.checked)} />
      <Button variant="outlined" size="small" onClick={() => setEditando(true)}>
        Editar
      </Button>
    </Stack>
  );
}
