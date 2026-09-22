import { useCartaContext } from "./CartaContext";
import { PlatoCard } from "./PlatoCard";

interface Props {
  categoriaId: string | null;
  onAbrirFoto: (id: string) => void;
}

export function ListaPlatos({ categoriaId, onAbrirFoto }: Props) {
  const { carta, categorias, idioma, t } = useCartaContext();

  const cat = categorias.find((c) => c.id === categoriaId);
  const titulo = cat ? cat.nombre_i18n[idioma] || cat.nombre : "";
  const platos = carta.filter((p) => p.categoria === categoriaId && p.disponible);

  return (
    <main>
      <h2 className="seccion-tit" id="titulo-cat">
        {titulo}
      </h2>
      <div id="lista">
        {platos.length === 0 ? (
          <p className="vacio">{t("sin_platos")}</p>
        ) : (
          platos.map((p) => <PlatoCard key={p.id} plato={p} onAbrirFoto={onAbrirFoto} />)
        )}
      </div>
    </main>
  );
}
