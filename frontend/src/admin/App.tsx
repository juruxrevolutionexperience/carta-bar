import { useEffect, useState } from "react";

import "./estilos.css";
import { cargarCarta, cargarCategorias } from "./api";
import { NavInferior, type Seccion } from "./NavInferior";
import { SeccionCategorias } from "./SeccionCategorias";
import { SeccionCuenta } from "./SeccionCuenta";
import { SeccionEspeciales } from "./SeccionEspeciales";
import { SeccionPlatos } from "./SeccionPlatos";
import { CATEGORIA_ESPECIALES, platoVacio, type Categoria, type Plato } from "./types";

export function App() {
  const [seccion, setSeccion] = useState<Seccion>("platos");
  const [platos, setPlatos] = useState<Plato[] | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([cargarCarta(), cargarCategorias()])
      .then(([platosCargados, categoriasCargadas]) => {
        setPlatos(platosCargados);
        setCategorias([...categoriasCargadas].sort((a, b) => a.orden - b.orden));
      })
      .catch(() => setError(true));
  }, []);

  const categoriasPorId = Object.fromEntries(categorias.map((c) => [c.id, c.nombre]));

  function actualizarPlato(anterior: Plato, nuevo: Plato) {
    setPlatos((actual) => actual?.map((p) => (p === anterior ? nuevo : p)) ?? actual);
  }

  function quitarPlato(objetivo: Plato) {
    setPlatos((actual) => actual?.filter((p) => p !== objetivo) ?? actual);
  }

  function anadirPlato(plato: Plato) {
    setPlatos((actual) => [...(actual ?? []), plato]);
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
          categorias={categorias}
          onActualizar={actualizarPlato}
          onQuitar={quitarPlato}
          onCreado={anadirPlato}
        />
      )}
      {seccion === "categorias" && (
        <SeccionCategorias
          categorias={categorias}
          platos={platos}
          onCambio={(nuevas) => setCategorias([...nuevas].sort((a, b) => a.orden - b.orden))}
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
