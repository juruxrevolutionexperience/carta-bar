import { useEffect, useState } from "react";

import "./estilos.css";
import { Carrusel } from "./Carrusel";
import { CartaProvider, useCartaContext } from "./CartaContext";
import { Chat } from "./Chat";
import { ListaPlatos } from "./ListaPlatos";
import { Portada } from "./Portada";
import { colorSeguro } from "./seguridad";
import { SelectorIdioma } from "./SelectorIdioma";
import { useVisorFoto } from "./useVisorFoto";
import { VisorFoto } from "./VisorFoto";

function CartaApp() {
  const { config, idioma, categoriasVisibles, cargando, t } = useCartaContext();
  const [categoriaId, setCategoriaId] = useState<string | null>(null);
  const visor = useVisorFoto();

  // Efectos de pagina completa: titulo de la pestaña, idioma del documento
  // (para lectores de pantalla) y el color de marca del restaurante, que
  // afecta a elementos fuera de la portada (el lanzador del chat, focus...).
  useEffect(() => {
    if (config.nombre) document.title = config.nombre;
  }, [config.nombre]);

  useEffect(() => {
    if (idioma) document.documentElement.lang = idioma;
  }, [idioma]);

  useEffect(() => {
    const marca = colorSeguro(config.color_marca);
    if (marca) document.documentElement.style.setProperty("--marca", marca);
  }, [config.color_marca]);

  // Al terminar de cargar (o al cambiar de idioma), si la categoria activa
  // ya no existe o todavia no hay ninguna elegida, se selecciona la primera
  // visible — igual que hace aplicarIdioma() con el "aria-selected" de hoy.
  useEffect(() => {
    if (cargando) return;
    setCategoriaId((actual) => {
      if (actual && categoriasVisibles.some((c) => c.id === actual)) return actual;
      return categoriasVisibles[0]?.id ?? null;
    });
  }, [cargando, categoriasVisibles]);

  if (cargando) return null;

  return (
    <>
      <div className="app">
        <Portada />

        <h2 className="seccion-tit">{t("menu")}</h2>
        <Carrusel categoriaSeleccionada={categoriaId} onSeleccionar={setCategoriaId} />

        <div className="divisor"></div>

        <ListaPlatos categoriaId={categoriaId} onAbrirFoto={visor.abrir} />

        <p className="pie">
          {config.aviso_alergenos_i18n?.[idioma] || config.aviso_alergenos || ""}
        </p>
      </div>

      <Chat />
      <VisorFoto src={visor.src} onCerrar={() => visor.cerrar(false)} />
      <SelectorIdioma />
    </>
  );
}

export function App() {
  return (
    <CartaProvider>
      <CartaApp />
    </CartaProvider>
  );
}
