import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";

import { useAvisosPersonal } from "./useAvisosPersonal";

const TEXTO: Record<string, string> = {
  nueva: "nueva, por aceptar",
  cuenta: "pide la cuenta",
};

// Banner flotante, visible encima de cualquier pantalla del panel: una mesa
// nueva o que pide la cuenta no deberia pasar desapercibida solo porque el
// camarero estuviera mirando Cocina en vez de Servicio.
export function AvisosPersonal() {
  const avisos = useAvisosPersonal();
  if (avisos.length === 0) return null;

  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        position: "fixed",
        top: 64,
        right: 12,
        zIndex: (t) => t.zIndex.snackbar,
        display: "flex",
        flexDirection: "column",
        gap: 1,
        maxWidth: { xs: "calc(100vw - 24px)", sm: 320 },
      }}
    >
      {avisos.map((a) => (
        <Alert key={a.clave} severity={a.tipo === "nueva" ? "warning" : "info"} variant="filled">
          <strong>{a.nombre}</strong> · {TEXTO[a.tipo]}
        </Alert>
      ))}
    </Box>
  );
}
