import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { cargarCarta, cargarCategorias, cargarConfig, cargarIdiomas } from "./api";
import type { Categoria, Config, Idiomas, Plato, TextosIdioma } from "./types";

const CATEGORIA_ESPECIALES = "especial-de-hoy";
const CLAVE_IDIOMA_LOCALSTORAGE = "carta_idioma";

export interface CartaContextValue {
  carta: Plato[];
  categorias: Categoria[];
  categoriasVisibles: Categoria[];
  config: Config;
  idiomas: Idiomas;
  idioma: string;
  textos: TextosIdioma;
  t: (clave: string) => string;
  cambiarIdioma: (codigo: string) => void;
  mostrarSelectorIdioma: boolean;
  abrirSelectorIdioma: () => void;
  cerrarSelectorIdioma: () => void;
  cargando: boolean;
}

export const CartaContext = createContext<CartaContextValue | null>(null);

export function useCartaContext(): CartaContextValue {
  const ctx = useContext(CartaContext);
  if (!ctx) throw new Error("useCartaContext fuera de <CartaProvider>");
  return ctx;
}

export function CartaProvider({ children }: { children: ReactNode }) {
  const [carta, setCarta] = useState<Plato[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [config, setConfig] = useState<Config>({});
  const [idiomas, setIdiomas] = useState<Idiomas>({});
  const [idioma, setIdioma] = useState<string>(
    () => localStorage.getItem(CLAVE_IDIOMA_LOCALSTORAGE) || ""
  );
  const [mostrarSelectorIdioma, setMostrarSelectorIdioma] = useState(false);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let activo = true;
    (async () => {
      const [c, cats, cfg, idi] = await Promise.all([
        cargarCarta(),
        cargarCategorias(),
        cargarConfig(),
        cargarIdiomas(),
      ]);
      if (!activo) return;

      const cartaInicial = c || [];
      const idiomasCargados = idi || {};

      let idiomaResuelto = idioma;
      if (!idiomaResuelto || !idiomasCargados[idiomaResuelto]) {
        const nav = (navigator.language || "es").slice(0, 2);
        idiomaResuelto = idiomasCargados[nav] ? nav : "es";
        setMostrarSelectorIdioma(true);
      }

      const categoriasResueltas =
        cats ||
        [...new Set(cartaInicial.map((p) => p.categoria))].map((id, i) => ({
          id,
          nombre: id.replace(/_/g, " "),
          nombre_i18n: {},
          orden: i,
        }));
      categoriasResueltas.sort((a, b) => a.orden - b.orden);

      setCarta(cartaInicial);
      setConfig(cfg || {});
      setIdiomas(idiomasCargados);
      setCategorias(categoriasResueltas);
      setIdioma(idiomaResuelto);

      // Igual que aplicarIdioma() hoy: la primera carga trae /carta sin
      // idioma (por defecto "es" en el backend); en cuanto se resuelve el
      // idioma real, se vuelve a pedir ya traducida.
      const cartaTraducida = await cargarCarta(idiomaResuelto);
      if (activo && cartaTraducida) setCarta(cartaTraducida);

      setCargando(false);
    })();
    return () => {
      activo = false;
    };
    // Solo en el montaje: cambiar de idioma lo gestiona cambiarIdioma().
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function cambiarIdioma(codigo: string) {
    setIdioma(codigo);
    localStorage.setItem(CLAVE_IDIOMA_LOCALSTORAGE, codigo);
    setMostrarSelectorIdioma(false);
    cargarCarta(codigo).then((d) => {
      if (d) setCarta(d);
    });
  }

  const textos = idiomas[idioma] || {};

  function t(clave: string): string {
    const valor = textos[clave];
    return typeof valor === "string" ? valor : clave;
  }

  // La categoria centinela de los especiales del dia solo se muestra si
  // tiene algun plato activo: sin eso, se ve una pestaña vacia permanente.
  const categoriasVisibles = useMemo(
    () =>
      categorias.filter(
        (cat) =>
          cat.id !== CATEGORIA_ESPECIALES ||
          carta.some((p) => p.categoria === cat.id && p.disponible)
      ),
    [categorias, carta]
  );

  const value: CartaContextValue = {
    carta,
    categorias,
    categoriasVisibles,
    config,
    idiomas,
    idioma,
    textos,
    t,
    cambiarIdioma,
    mostrarSelectorIdioma,
    abrirSelectorIdioma: () => setMostrarSelectorIdioma(true),
    cerrarSelectorIdioma: () => setMostrarSelectorIdioma(false),
    cargando,
  };

  return <CartaContext.Provider value={value}>{children}</CartaContext.Provider>;
}
