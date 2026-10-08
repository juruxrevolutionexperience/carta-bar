import { IconMaximize, IconZoomIn, IconZoomOut } from "@tabler/icons-react";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { ZOOM_FACTOR, ZOOM_MAX, ZOOM_MIN } from "./planoUtil";

interface Props {
  zoom: number;
  onZoom: (zoom: number) => void;
  onAjustar: () => void;
}

// Solo mueven la vista del plano; qué se puede tocar lo decide el modo (ojo o
// lápiz), no esta barra.
export function HerramientasPlano({ zoom, onZoom, onAjustar }: Props) {
  return (
    <Stack direction="row" alignItems="center" spacing={0.5} className="herramientas-plano">
      <IconButton
        size="small"
        aria-label="Alejar"
        disabled={zoom <= ZOOM_MIN}
        onClick={() => onZoom(zoom / ZOOM_FACTOR)}
      >
        <IconZoomOut size={18} />
      </IconButton>
      <Typography sx={{ fontSize: 12.5, color: "text.secondary", minWidth: 36, textAlign: "center" }}>
        {Math.round(zoom * 100)}%
      </Typography>
      <IconButton
        size="small"
        aria-label="Acercar"
        disabled={zoom >= ZOOM_MAX}
        onClick={() => onZoom(zoom * ZOOM_FACTOR)}
      >
        <IconZoomIn size={18} />
      </IconButton>
      <IconButton size="small" aria-label="Ver el plano entero" onClick={onAjustar}>
        <IconMaximize size={18} />
      </IconButton>
    </Stack>
  );
}
