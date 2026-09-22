import { useEffect, useState } from "react";

import "./estilos.css";
import { cerrarSesion, listarRestaurantes, type ResumenRestaurante } from "./api";
import { FormularioNuevoRestaurante } from "./FormularioNuevoRestaurante";
import { ListaRestaurantes } from "./ListaRestaurantes";
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

  return (
    <div className="app">
      <header>
        <h1>Panel superadmin</h1>
        <button type="button" className="secundario" onClick={cerrarSesion}>
          Cerrar sesión
        </button>
      </header>
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
  );
}
