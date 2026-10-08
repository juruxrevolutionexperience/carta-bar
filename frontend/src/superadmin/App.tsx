import { useEffect, useMemo, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import { ThemeProvider } from "@mui/material/styles";
import Typography from "@mui/material/Typography";

import "./estilos.css";
import { cerrarSesion, listarRestaurantes, type ResumenRestaurante } from "./api";
import { FormularioNuevoRestaurante } from "./FormularioNuevoRestaurante";
import { ListaRestaurantes } from "./ListaRestaurantes";
import { crearTemaMui } from "./muiTheme";
import { PanelImportar } from "./PanelImportar";
import { PanelMetricas } from "./PanelMetricas";
import { PanelQr } from "./PanelQr";

export function App() {
  const [restaurantes, setRestaurantes] = useState<ResumenRestaurante[] | null>(null);
  const [error, setError] = useState(false);
  const [qrDe, setQrDe] = useState<string | null>(null);
  const [importarDe, setImportarDe] = useState<string | null>(null);

  useEffect(() => {
    listarRestaurantes()
      .then(setRestaurantes)
      .catch(() => setError(true));
  }, []);

  function alCrear(nuevo: ResumenRestaurante) {
    setRestaurantes((actual) => (actual ? [...actual, nuevo] : [nuevo]));
  }

  const tema = useMemo(() => crearTemaMui("light"), []);

  return (
    <ThemeProvider theme={tema}>
      <div className="app">
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
          <Typography variant="h2">Panel superadmin</Typography>
          <Button variant="outlined" onClick={cerrarSesion}>
            Cerrar sesión
          </Button>
        </Stack>
        <div className="franja"></div>

        <ListaRestaurantes
          restaurantes={restaurantes}
          error={error}
          seleccionado={qrDe}
          onVerQr={setQrDe}
          onImportar={setImportarDe}
        />
        {qrDe && <PanelQr key={qrDe} restauranteId={qrDe} onCerrar={() => setQrDe(null)} />}
        {importarDe && (
          <PanelImportar
            key={importarDe}
            restauranteId={importarDe}
            onCerrar={() => setImportarDe(null)}
          />
        )}
        <PanelMetricas />
        <FormularioNuevoRestaurante onCreado={alCrear} />
      </div>
    </ThemeProvider>
  );
}
