import { useCartaContext } from "./CartaContext";
import { degradado, ICONO_CAT } from "./iconos";

interface Props {
  categoriaSeleccionada: string | null;
  onSeleccionar: (id: string) => void;
}

export function Carrusel({ categoriaSeleccionada, onSeleccionar }: Props) {
  const { carta, categoriasVisibles, idioma, t } = useCartaContext();

  return (
    <div className="carrusel" role="tablist">
      {categoriasVisibles.map((cat) => {
        const n = carta.filter((p) => p.categoria === cat.id && p.disponible).length;
        const nomCat = cat.nombre_i18n[idioma] || cat.nombre;
        const seleccionada = cat.id === categoriaSeleccionada;
        return (
          <button
            key={cat.id}
            className={"cat-card" + (cat.id === "especial-de-hoy" ? " especial" : "")}
            role="tab"
            aria-selected={seleccionada}
            onClick={() => onSeleccionar(cat.id)}
          >
            <div className="cat-visual" style={{ background: degradado(cat.id) }}>
              {ICONO_CAT[cat.id] || "🍽️"}
            </div>
            <div className="cat-nombre">{nomCat}</div>
            <div className="cat-cuenta">
              {n} {n === 1 ? t("platos_uno") : t("platos_varios")}
            </div>
          </button>
        );
      })}
    </div>
  );
}
