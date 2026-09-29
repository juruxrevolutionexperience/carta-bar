import { useState } from "react";

import "./tarjetaPlato.css";
import { useCartaContext } from "./CartaContext";
import { FormularioPropuesta } from "./FormularioPropuesta";
import { degradado, iconoPlato, ICONO_ETQ } from "./iconos";
import { importe, textoPrecio } from "./precios";
import { useMesaContext } from "./MesaContext";
import { urlSegura } from "./seguridad";
import type { Plato } from "./types";

interface Props {
  plato: Plato;
  onAbrirFoto: (id: string) => void;
  onAnadirALista: (id: string) => void;
}

export function PlatoCard({ plato: p, onAbrirFoto, onAnadirALista }: Props) {
  const { idioma, config, textos, t } = useCartaContext();
  const { mesa } = useMesaContext();
  const [pidiendo, setPidiendo] = useState(false);
  const moneda = config.moneda || "€";
  const enMesa = mesa !== null && mesa.estado !== "cerrada";

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
  // Alergenos y dieta sin revisar por el restaurante: pueden ser una
  // estimacion, asi que no se ensenan como si fueran un dato. Solo el aviso.
  const sinConfirmar = p.alergenos_confirmados === false;
  const dietas = [
    p.vegano && txtDieta("vegano"),
    !p.vegano && p.vegetariano && txtDieta("vegetariano"),
    p.sin_gluten && txtDieta("sin_gluten"),
    p.sin_lactosa && txtDieta("sin_lactosa"),
  ].filter((d): d is string => Boolean(d));

  const foto = urlSegura(p.foto);
  const conFormatos = (p.formatos?.length ?? 0) > 0;
  const descripcion = p.descripcion_i18n?.[idioma] || p.descripcion;

  return (
    <article className="plato">
      <div
        className={"plato-foto" + (foto ? " con-foto" : "")}
        style={{ background: degradado(p.categoria, p.id) }}
        onClick={foto ? () => onAbrirFoto(p.id) : undefined}
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
          {!conFormatos && (
            <span className="precio">{textoPrecio(p, moneda, t("precio_consultar"))}</span>
          )}
          <button
            type="button"
            className="anadir-lista"
            aria-label={`${t("mi_lista")}: ${p.nombre}`}
            onClick={() => onAnadirALista(p.id)}
          >
            +
          </button>
        </div>
        {enMesa && p.disponible && (
          <button type="button" className="boton-pedir" onClick={() => setPidiendo(true)}>
            Pedir
          </button>
        )}
        {conFormatos && (
          <ul className="formatos">
            {p.formatos?.map((f) => (
              <li key={f.nombre}>
                <span className="formato-nombre">{f.nombre}</span>
                <span className="formato-precio">{importe(f.precio, moneda)}</span>
              </li>
            ))}
          </ul>
        )}
        <p className={"desc" + (pendiente ? " pendiente" : "")}>{descripcion}</p>
        <div className="chips">
          {!sinConfirmar && dietas.map((d) => (
            <span className="chip dieta" key={d}>
              {d}
            </span>
          ))}
          {!sinConfirmar && (p.alergenos || []).map((a) => (
            <span className="chip alergeno" key={a}>
              {txtAlergeno(a)}
            </span>
          ))}
          {(pendiente || sinConfirmar) && (
            <span className="chip aviso">{t("consultar_alergenos")}</span>
          )}
        </div>
      </div>
      {pidiendo && <FormularioPropuesta plato={p} onCerrar={() => setPidiendo(false)} />}
    </article>
  );
}
