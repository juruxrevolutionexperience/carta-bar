import { useEffect, useState } from "react";

import { cargarGruposDePlato } from "./api";
import { useCartaContext } from "./CartaContext";
import { useMesaContext } from "./MesaContext";
import { importe } from "./precios";
import type { Grupo, Plato } from "./types";

interface Props {
  plato: Plato;
  onCerrar: () => void;
}

// Se abre al pulsar "Pedir" en un plato, solo cuando hay mesa (ver PlatoCard).
// Los extras se piden aqui: no se cargan con toda la carta (productos.py).
export function FormularioPropuesta({ plato, onCerrar }: Props) {
  const { config } = useCartaContext();
  const { proponer } = useMesaContext();
  const moneda = config.moneda || "€";

  const [grupos, setGrupos] = useState<Grupo[] | null>(null);
  const [formato, setFormato] = useState<string | null>(plato.formatos?.[0]?.nombre ?? null);
  const [elegidas, setElegidas] = useState<string[]>([]);
  const [cantidad, setCantidad] = useState(1);
  const [nota, setNota] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    cargarGruposDePlato(plato.id).then((g) => activo && setGrupos(g));
    return () => {
      activo = false;
    };
  }, [plato.id]);

  function enGrupo(grupo: Grupo, nombre: string): boolean {
    return grupo.opciones.some((o) => o.nombre === nombre);
  }

  function elegidasDe(grupo: Grupo): string[] {
    return elegidas.filter((n) => enGrupo(grupo, n));
  }

  function alternar(grupo: Grupo, nombre: string) {
    setElegidas((actual) => {
      if (grupo.maximo === 1) {
        // Radio: quita las demas de este grupo, deja solo esta (o ninguna).
        const sinGrupo = actual.filter((n) => !enGrupo(grupo, n));
        return actual.includes(nombre) ? sinGrupo : [...sinGrupo, nombre];
      }
      if (actual.includes(nombre)) return actual.filter((n) => n !== nombre);
      if (elegidasDe(grupo).length >= grupo.maximo) return actual;
      return [...actual, nombre];
    });
  }

  async function enviar() {
    setEnviando(true);
    setError(null);
    const r = await proponer({
      plato_id: plato.id,
      formato,
      opciones: elegidas,
      cantidad,
      nota: nota.trim() || null,
    });
    setEnviando(false);
    if (r.ok) {
      onCerrar();
    } else {
      setError("No se pudo añadir: revisa que hayas elegido lo necesario.");
    }
  }

  return (
    <div className="velo" onClick={onCerrar}>
      <div className="caja-propuesta" onClick={(e) => e.stopPropagation()}>
        <div className="panel-top">
          <h2>{plato.nombre}</h2>
          <button type="button" className="cerrar" aria-label="Cerrar" onClick={onCerrar}>
            ×
          </button>
        </div>

        {(plato.formatos?.length ?? 0) > 0 && (
          <div className="grupo-propuesta">
            <h3>Formato</h3>
            {plato.formatos!.map((f) => (
              <label className="opcion-propuesta" key={f.nombre}>
                <input
                  type="radio"
                  name="formato"
                  checked={formato === f.nombre}
                  onChange={() => setFormato(f.nombre)}
                />
                {f.nombre}
                <span className="opcion-precio">{importe(f.precio, moneda)}</span>
              </label>
            ))}
          </div>
        )}

        {grupos?.map((grupo) => (
          <div className="grupo-propuesta" key={grupo.id}>
            <h3>
              {grupo.nombre}
              {grupo.minimo > 0 && <span className="obligatorio"> · obligatorio</span>}
            </h3>
            {grupo.opciones.map((o) => (
              <label className="opcion-propuesta" key={o.nombre}>
                <input
                  type={grupo.maximo === 1 ? "radio" : "checkbox"}
                  name={grupo.id}
                  checked={elegidas.includes(o.nombre)}
                  onChange={() => alternar(grupo, o.nombre)}
                />
                {o.nombre}
                {o.precio > 0 && <span className="opcion-precio">+{importe(o.precio, moneda)}</span>}
              </label>
            ))}
          </div>
        ))}

        <div className="grupo-propuesta cantidad-propuesta">
          <h3>Cantidad</h3>
          <div className="fila-lista-cantidad">
            <button type="button" onClick={() => setCantidad((c) => Math.max(1, c - 1))}>
              −
            </button>
            <span>{cantidad}</span>
            <button type="button" onClick={() => setCantidad((c) => Math.min(20, c + 1))}>
              +
            </button>
          </div>
        </div>

        <input
          className="nota-propuesta"
          type="text"
          placeholder="Nota (opcional): sin cebolla…"
          maxLength={200}
          value={nota}
          onChange={(e) => setNota(e.target.value)}
        />

        {error && <p className="aviso-propuesta">{error}</p>}

        <button type="button" className="boton-proponer" disabled={enviando} onClick={enviar}>
          Añadir al pedido de la mesa
        </button>
      </div>
    </div>
  );
}
