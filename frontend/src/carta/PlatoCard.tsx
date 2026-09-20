import "./tarjetaPlato.css";
import { useCartaContext } from "./CartaContext";
import { degradado, iconoPlato, ICONO_ETQ } from "./iconos";
import { urlSegura } from "./seguridad";
import type { Plato } from "./types";

interface Props {
  plato: Plato;
  onAbrirFoto: (src: string) => void;
}

export function PlatoCard({ plato: p, onAbrirFoto }: Props) {
  const { idioma, config, textos, t } = useCartaContext();
  const moneda = config.moneda || "€";

  function txtAlergeno(a: string): string {
    return textos.alergenos?.[a] || a;
  }
  function txtEtiqueta(e: string): string {
    return textos.etiquetas?.[e] || e;
  }
  function txtDieta(d: string): string {
    return textos.dietas?.[d] || d;
  }

  const pendiente = !p.ingredientes || p.ingredientes.length === 0;
  const dietas = [
    p.vegano && txtDieta("vegano"),
    !p.vegano && p.vegetariano && txtDieta("vegetariano"),
    p.sin_gluten && txtDieta("sin_gluten"),
    p.sin_lactosa && txtDieta("sin_lactosa"),
  ].filter((d): d is string => Boolean(d));

  const foto = urlSegura(p.foto);
  const descripcion = p.descripcion_i18n?.[idioma] || p.descripcion;

  return (
    <article className="plato">
      <div
        className={"plato-foto" + (foto ? " con-foto" : "")}
        style={{ background: degradado(p.categoria, p.id) }}
        onClick={foto ? () => onAbrirFoto(foto) : undefined}
      >
        {foto ? <img src={foto} alt="" loading="lazy" decoding="async" /> : iconoPlato(p)}
      </div>
      <div className="plato-info">
        {p.etiqueta && (
          <span className={"etiqueta etq-" + p.etiqueta}>
            <span className="ico">{ICONO_ETQ[p.etiqueta] || ""}</span>
            {txtEtiqueta(p.etiqueta)}
          </span>
        )}
        <div className="plato-top">
          <h3 className="nombre">{p.nombre}</h3>
          <span className="precio">
            {p.precio == null
              ? t("precio_consultar")
              : Number(p.precio).toFixed(2).replace(".", ",") + " " + moneda}
          </span>
        </div>
        <p className={"desc" + (pendiente ? " pendiente" : "")}>{descripcion}</p>
        <div className="chips">
          {dietas.map((d) => (
            <span className="chip dieta" key={d}>
              {d}
            </span>
          ))}
          {(p.alergenos || []).map((a) => (
            <span className="chip alergeno" key={a}>
              {txtAlergeno(a)}
            </span>
          ))}
          {pendiente && <span className="chip aviso">{t("consultar_alergenos")}</span>}
        </div>
      </div>
    </article>
  );
}
