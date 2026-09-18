import { useEffect, useState } from "react";

import "./estilos.css";
import { cerrarSesion, listarRestaurantes, type ResumenRestaurante } from "./api";
import { FormularioNuevoRestaurante } from "./FormularioNuevoRestaurante";
import { ListaRestaurantes } from "./ListaRestaurantes";

export function App() {
  const [restaurantes, setRestaurantes] = useState<ResumenRestaurante[] | null>(null);
  const [error, setError] = useState(false);

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

      <ListaRestaurantes restaurantes={restaurantes} error={error} />
      <FormularioNuevoRestaurante onCreado={alCrear} />
    </div>
  );
}
