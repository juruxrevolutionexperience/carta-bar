import { useEffect, useState } from "react";

import { cargarConfig, cargarIdiomas } from "../carta/api";
import { CartaContext, type CartaContextValue } from "../carta/CartaContext";
import { PlatoCard } from "../carta/PlatoCard";
import type { Config, Idiomas, Plato as PlatoCarta } from "../carta/types";
import "./vistaPrevia.css";

interface Props {
  plato: PlatoCarta;
}

// Pinta la misma tarjeta que ve el cliente en la carta (PlatoCard), con los
// textos y la moneda reales del restaurante, no una imitacion.
export function VistaPreviaPlato({ plato }: Props) {
  const [config, setConfig] = useState<Config>({});
  const [idiomas, setIdiomas] = useState<Idiomas>({});

  useEffect(() => {
    void cargarConfig().then((c) => c && setConfig(c));
    void cargarIdiomas().then((i) => i && setIdiomas(i));
  }, []);

  const textos = idiomas.es || {};
  const valor = {
    config,
    idioma: "es",
    textos,
    t: (clave: string) => {
      const v = textos[clave];
      return typeof v === "string" ? v : clave;
    },
  } as CartaContextValue;

  return (
    <div className="vista-previa-carta">
      <div className="vista-previa-titulo">Así se verá en la carta</div>
      <CartaContext.Provider value={valor}>
        <PlatoCard plato={plato} onAbrirFoto={() => {}} />
      </CartaContext.Provider>
    </div>
  );
}
