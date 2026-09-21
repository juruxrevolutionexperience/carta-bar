import { useEffect, useState } from "react";

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
    <div className="panel-tarjeta">
      <h2>QR de {restauranteId}</h2>
      {error && <p className="cargando">No se pudo cargar el QR.</p>}
      {!error && !datos && <p className="cargando">Cargando…</p>}
      {datos && <HojaQR url={datos.url} nombre={datos.nombre} texto={datos.texto} />}
      <button type="button" className="secundario" onClick={onCerrar}>
        Cerrar
      </button>
    </div>
  );
}
