import { useCartaContext } from "./CartaContext";
import { degradado, ICONO_CAT } from "./iconos";
import { urlSegura } from "./seguridad";

interface Props {
  categoriaSeleccionada: string | null;
  onSeleccionar: (id: string) => void;
}

export function Carrusel({ categoriaSeleccionada, onSeleccionar }: Props) {
  const { carta, categoriasVisibles, idioma, t } = useCartaContext();

  return (
    <div className="carrusel" role="tablist">
      {categoriasVisibles.map((cat) => {
        const platosCat = carta.filter((p) => p.categoria === cat.id && p.disponible);
        const n = platosCat.length;
        const nomCat = cat.nombre_i18n[idioma] || cat.nombre;
        const seleccionada = cat.id === categoriaSeleccionada;
        // Con una foto de un plato de la categoria, la pestana deja de ser un
        // icono generico y pasa a representar lo que de verdad se sirve ahi.
        const foto = urlSegura(platosCat.find((p) => p.foto)?.foto || null);
        return (
          <button
            key={cat.id}
            className={"cat-card" + (cat.id === "especial-de-hoy" ? " especial" : "")}
            role="tab"
            aria-selected={seleccionada}
            onClick={() => onSeleccionar(cat.id)}
          >
            <div className="cat-visual" style={foto ? undefined : { background: degradado(cat.id) }}>
              {foto ? (
                <img src={foto} alt="" loading="lazy" decoding="async" />
              ) : (
                ICONO_CAT[cat.id] || "🍽️"
              )}
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
