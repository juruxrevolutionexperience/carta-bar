import { IconPlus } from "@tabler/icons-react";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";

import { FilaPlato } from "./FilaPlato";
import type { Plato } from "./types";

interface Props {
  especiales: Plato[] | null;
  error: boolean;
  categoriasPorId: Record<string, string>;
  onActualizar: (anterior: Plato, nuevo: Plato) => void;
  onQuitar: (objetivo: Plato) => void;
  onAnadir: () => void;
}

export function SeccionEspeciales({
  especiales,
  error,
  categoriasPorId,
  onActualizar,
  onQuitar,
  onAnadir,
}: Props) {
  return (
    <section className="seccion">
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1 }}>
            Especial de hoy
          </Typography>
          <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>
            Platos fuera de la carta fija. Aparecen en una sección propia en la carta pública
            mientras estén aquí; quítalos cuando ya no toque.
          </Typography>
          <Button variant="contained" startIcon={<IconPlus size={18} />} onClick={onAnadir}>
            Añadir especial
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          {error && <p className="cargando">No se pudo cargar la carta.</p>}
          {!error && especiales === null && <p className="cargando">Cargando…</p>}
          {!error && especiales !== null && especiales.length === 0 && (
            <p className="cargando">No hay especiales activos.</p>
          )}
          {especiales?.map((p, i) => (
            <FilaPlato
              key={p.id ?? `nuevo-${i}`}
              plato={p}
              nombreCategoria={categoriasPorId[p.categoria] || p.categoria}
              onCambiado={(nuevo) => onActualizar(p, nuevo)}
              onQuitarDeLista={() => onQuitar(p)}
            />
          ))}
        </CardContent>
      </Card>
    </section>
  );
}
