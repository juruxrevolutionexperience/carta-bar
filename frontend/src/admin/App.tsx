import { useEffect, useState } from "react";

import "./estilos.css";
import { cargarCarta, cargarCategorias } from "./api";
import { BarraSuperior } from "./BarraSuperior";
import { MenuLateral } from "./MenuLateral";
import { SeccionCocina } from "./SeccionCocina";
import { SeccionCuenta } from "./SeccionCuenta";
import { SeccionMesas } from "./SeccionMesas";
import { SeccionMarca } from "./SeccionMarca";
import { SeccionEspeciales } from "./SeccionEspeciales";
import { SeccionExtras } from "./SeccionExtras";
import { SeccionPlatos } from "./SeccionPlatos";
import { SeccionQr } from "./SeccionQr";
import { SeccionServicio } from "./SeccionServicio";
import { SECCIONES, tituloDe, type Seccion } from "./secciones";
import { CATEGORIA_ESPECIALES, platoVacio, type Categoria, type Plato } from "./types";

export function App() {
  const [seccion, setSeccion] = useState<Seccion>(SECCIONES[0].id);
  const [menuAbierto, setMenuAbierto] = useState(false);
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

  // El plano de mesas manda: en esa pantalla el menú se esconde también en
  // escritorio (se abre con la hamburguesa) y el plano usa toda la pantalla.
  useEffect(() => {
    document.body.classList.toggle("plano-completo", seccion === "mesas");
    return () => document.body.classList.remove("plano-completo");
  }, [seccion]);

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
    <>
      <BarraSuperior titulo={tituloDe(seccion)} onAbrirMenu={() => setMenuAbierto(true)} />
      <MenuLateral
        activa={seccion}
        abierto={menuAbierto}
        onCambiar={setSeccion}
        onCerrar={() => setMenuAbierto(false)}
      />

      <div
        className={
          "app" +
          (seccion === "mesas" || seccion === "servicio" || seccion === "cocina"
            ? " app-ancha"
            : "")
        }
      >
        {seccion === "platos" && (
          <SeccionPlatos
            platos={normales}
            error={error}
            categorias={categorias}
            onActualizar={actualizarPlato}
            onQuitar={quitarPlato}
            onCreado={anadirPlato}
            onCambioCategorias={(nuevas) =>
              setCategorias([...nuevas].sort((a, b) => a.orden - b.orden))
            }
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
        {seccion === "extras" && <SeccionExtras />}
        {seccion === "servicio" && <SeccionServicio />}
        {seccion === "cocina" && <SeccionCocina />}
        {seccion === "mesas" && <SeccionMesas />}
        {seccion === "marca" && <SeccionMarca />}
        {seccion === "qr" && <SeccionQr />}
        {seccion === "cuenta" && <SeccionCuenta />}
      </div>
    </>
  );
}
