import { useEffect, useState } from "react";

import "./estilos.css";
import { cargarCarta, cargarCategorias } from "./api";
import { NavInferior, type Seccion } from "./NavInferior";
import { SeccionCuenta } from "./SeccionCuenta";
import { SeccionEspeciales } from "./SeccionEspeciales";
import { SeccionPlatos } from "./SeccionPlatos";
import { CATEGORIA_ESPECIALES, platoVacio, type Plato } from "./types";

export function App() {
  const [seccion, setSeccion] = useState<Seccion>("platos");
  const [platos, setPlatos] = useState<Plato[] | null>(null);
  const [categoriasPorId, setCategoriasPorId] = useState<Record<string, string>>({});
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([cargarCarta(), cargarCategorias()])
      .then(([platosCargados, categorias]) => {
        setPlatos(platosCargados);
        setCategoriasPorId(Object.fromEntries(categorias.map((c) => [c.id, c.nombre])));
      })
      .catch(() => setError(true));
  }, []);

  function actualizarPlato(anterior: Plato, nuevo: Plato) {
    setPlatos((actual) => actual?.map((p) => (p === anterior ? nuevo : p)) ?? actual);
  }

  function quitarPlato(objetivo: Plato) {
    setPlatos((actual) => actual?.filter((p) => p !== objetivo) ?? actual);
  }

  function anadirEspecial() {
    setPlatos((actual) => [platoVacio(), ...(actual ?? [])]);
  }

  const normales = platos?.filter((p) => p.categoria !== CATEGORIA_ESPECIALES) ?? null;
  const especiales = platos?.filter((p) => p.categoria === CATEGORIA_ESPECIALES) ?? null;

  return (
    <div className="app">
      <header>
        <h1>Panel de gestión</h1>
      </header>

      {seccion === "platos" && (
        <SeccionPlatos
          platos={normales}
          error={error}
          categoriasPorId={categoriasPorId}
          onActualizar={actualizarPlato}
          onQuitar={quitarPlato}
        />
      )}
      {seccion === "especiales" && (
        <SeccionEspeciales
          especiales={especiales}
          error={error}
          categoriasPorId={categoriasPorId}
          onActualizar={actualizarPlato}
          onQuitar={quitarPlato}
          onAnadir={anadirEspecial}
        />
      )}
      {seccion === "cuenta" && <SeccionCuenta />}

      <NavInferior activa={seccion} onCambiar={setSeccion} />
    </div>
  );
}
