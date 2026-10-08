import { useEffect, useState } from "react";

import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";

import { HojaQR, type DatosQr } from "../shared/HojaQR";
import { cargarQrRestaurante } from "./api";

interface Props {
  restauranteId: string;
  onCerrar: () => void;
}

// El QR de un restaurante, con su hoja imprimible, para entregarselo al dar de
// alta el bar. El texto de la hoja lo cambia el propio gerente desde su panel.
export function PanelQr({ restauranteId, onCerrar }: Props) {
  const [datos, setDatos] = useState<DatosQr | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    cargarQrRestaurante(restauranteId)
      .then(setDatos)
      .catch(() => setError(true));
  }, [restauranteId]);

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h3" sx={{ mb: 1.5 }}>
          QR de {restauranteId}
        </Typography>
        {error && <p className="cargando">No se pudo cargar el QR.</p>}
        {!error && !datos && <p className="cargando">Cargando…</p>}
        {datos && <HojaQR url={datos.url} nombre={datos.nombre} texto={datos.texto} />}
        <Button variant="outlined" onClick={onCerrar} sx={{ mt: 2 }}>
          Cerrar
        </Button>
      </CardContent>
    </Card>
  );
}
