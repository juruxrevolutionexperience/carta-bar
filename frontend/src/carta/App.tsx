import { useEffect, useMemo, useState } from "react";

import "./estilos.css";
import { Carrusel } from "./Carrusel";
import { CartaProvider, useCartaContext } from "./CartaContext";
import { Chat } from "./Chat";
import { ListaPlatos } from "./ListaPlatos";
import { MiLista } from "./MiLista";
import { Portada } from "./Portada";
import { colorSeguro } from "./seguridad";
import { SelectorIdioma } from "./SelectorIdioma";
import { useListaCliente } from "./useListaCliente";
import { useVisorFoto } from "./useVisorFoto";
import { VisorFoto } from "./VisorFoto";

function CartaApp() {
  const { carta, config, idioma, categoriasVisibles, cargando, t } = useCartaContext();
  const [categoriaId, setCategoriaId] = useState<string | null>(null);
  const visor = useVisorFoto();
  const lista = useListaCliente();

  // Orden del "escaparate" del visor: todos los platos disponibles, categoria
  // a categoria en el mismo orden que la carta, para que las flechas naveguen
  // igual que si se fuera bajando por la carta entera.
  const platosEnOrden = useMemo(() => {
    const resultado = [];
    for (const cat of categoriasVisibles) {
      for (const p of carta) {
        if (p.categoria === cat.id && p.disponible) resultado.push(p);
      }
    }
    return resultado;
  }, [carta, categoriasVisibles]);

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

        <ListaPlatos
          categoriaId={categoriaId}
          onAbrirFoto={visor.abrir}
          onAnadirALista={lista.anadir}
        />

        <p className="pie">
          {config.aviso_alergenos_i18n?.[idioma] || config.aviso_alergenos || ""}
        </p>
      </div>

      <Chat />
      <VisorFoto
        platoId={visor.platoId}
        platos={platosEnOrden}
        onNavegar={visor.abrir}
        onCerrar={() => visor.cerrar(false)}
      />
      <MiLista lista={lista} />
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
