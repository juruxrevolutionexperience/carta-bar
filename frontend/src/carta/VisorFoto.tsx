import { useEffect, useRef, useState } from "react";

import { useCartaContext } from "./CartaContext";
import { degradado, iconoPlato } from "./iconos";
import { textoPrecio } from "./precios";
import { urlSegura } from "./seguridad";
import type { Plato } from "./types";

interface Props {
  platoId: string | null;
  platos: Plato[]; // en el orden de la carta: categoria por categoria
  onNavegar: (id: string) => void;
  onCerrar: () => void;
}

export function VisorFoto({ platoId, platos, onNavegar, onCerrar }: Props) {
  const { categorias, idioma, config, t } = useCartaContext();
  const moneda = config.moneda || "€";
  const [banner, setBanner] = useState<string | null>(null);
  const tocando = useRef<number | null>(null);

  const indice = platoId === null ? -1 : platos.findIndex((p) => p.id === platoId);
  const actual = indice >= 0 ? platos[indice] : null;
  const anterior = indice > 0 ? platos[indice - 1] : null;
  const siguiente = indice >= 0 && indice < platos.length - 1 ? platos[indice + 1] : null;

  function nombreCategoria(catId: string): string {
    const c = categorias.find((c) => c.id === catId);
    return c ? c.nombre_i18n[idioma] || c.nombre : catId;
  }

  function ir(destino: Plato | null) {
    if (!destino || !actual) return;
    if (destino.categoria !== actual.categoria) {
      const nombre = nombreCategoria(destino.categoria);
      setBanner(nombre);
      window.setTimeout(() => setBanner(null), 1600);
    }
    onNavegar(destino.id);
  }

  useEffect(() => {
    if (!actual) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") ir(siguiente);
      if (e.key === "ArrowLeft") ir(anterior);
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actual, anterior, siguiente]);

  if (!actual) return <div className="visor-foto" hidden />;

  const foto = urlSegura(actual.foto);
  const descripcion = actual.descripcion_i18n?.[idioma] || actual.descripcion;

  return (
    <div
      className="visor-foto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
      onTouchStart={(e) => {
        tocando.current = e.touches[0].clientX;
      }}
      onTouchEnd={(e) => {
        if (tocando.current === null) return;
        const delta = e.changedTouches[0].clientX - tocando.current;
        tocando.current = null;
        if (Math.abs(delta) < 45) return;
        ir(delta < 0 ? siguiente : anterior);
      }}
    >
      <button className="visor-cerrar" aria-label="Cerrar" onClick={onCerrar}>
        ×
      </button>

      {banner && <div className="visor-banner">{banner}</div>}

      <div
        className="visor-imagen"
        style={!foto ? { background: degradado(actual.categoria, actual.id) } : undefined}
      >
        {foto ? <img src={foto} alt="" /> : <span className="visor-icono">{iconoPlato(actual)}</span>}

        <div className="visor-info">
          <h3>{actual.nombre}</h3>
          <div className="visor-linea">
            <span className="visor-precio">
              {textoPrecio(actual, moneda, t("precio_consultar"))}
            </span>
          </div>
          {descripcion && <p className="visor-desc">{descripcion}</p>}
        </div>
      </div>

      {anterior && (
        <button
          className="visor-flecha izquierda"
          aria-label="Plato anterior"
          onClick={(e) => {
            e.stopPropagation();
            ir(anterior);
          }}
        >
          ‹
        </button>
      )}
      {siguiente && (
        <button
          className="visor-flecha derecha"
          aria-label="Plato siguiente"
          onClick={(e) => {
            e.stopPropagation();
            ir(siguiente);
          }}
        >
          ›
        </button>
      )}
    </div>
  );
}
