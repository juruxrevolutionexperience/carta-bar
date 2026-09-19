import { useMemo, useState } from "react";

import { colorCategoria } from "../carta/iconos";
import { FilaPlato } from "./FilaPlato";
import type { Categoria, Plato } from "./types";

interface Props {
  platos: Plato[] | null;
  error: boolean;
  categorias: Categoria[];
  onActualizar: (anterior: Plato, nuevo: Plato) => void;
  onQuitar: (objetivo: Plato) => void;
}

// Sin acentos ni mayusculas: "salmon" tiene que encontrar "Salmón".
function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export function SeccionPlatos({ platos, error, categorias, onActualizar, onQuitar }: Props) {
  const [busqueda, setBusqueda] = useState("");

  const filtrados = useMemo(() => {
    const termino = normalizar(busqueda.trim());
    if (!termino || !platos) return platos;
    return platos.filter((p) => normalizar(p.nombre).includes(termino));
  }, [platos, busqueda]);

  const grupos = useMemo(() => {
    if (!filtrados) return null;
    const porCategoria = new Map<string, Plato[]>();
    for (const p of filtrados) {
      const lista = porCategoria.get(p.categoria);
      if (lista) lista.push(p);
      else porCategoria.set(p.categoria, [p]);
    }
    // Las categorias conocidas, en su orden; cualquier plato con una
    // categoria que ya no exista en categorias.json no se pierde, aparece
    // al final agrupado bajo su propio id.
    const ordenadas = categorias
      .filter((c) => porCategoria.has(c.id))
      .map((c) => ({ id: c.id, nombre: c.nombre, platos: porCategoria.get(c.id)! }));
    const conocidas = new Set(categorias.map((c) => c.id));
    for (const [id, platosDeCategoria] of porCategoria) {
      if (!conocidas.has(id)) ordenadas.push({ id, nombre: id, platos: platosDeCategoria });
    }
    return ordenadas;
  }, [filtrados, categorias]);

  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Platos</h2>
        {!error && platos !== null && platos.length > 0 && (
          <input
            type="search"
            placeholder="Buscar un plato…"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            aria-label="Buscar un plato"
          />
        )}

        {error && <p className="cargando">No se pudo cargar la carta.</p>}
        {!error && platos === null && <p className="cargando">Cargando…</p>}
        {!error && platos !== null && platos.length === 0 && (
          <p className="cargando">No hay platos.</p>
        )}
        {!error && grupos !== null && grupos.length === 0 && busqueda.trim() && (
          <p className="cargando">Ningún plato coincide con "{busqueda.trim()}".</p>
        )}

        {grupos?.map((grupo) => (
          <details key={grupo.id} className="grupo-categoria" open>
            <summary
              className="titulo-categoria"
              style={{ borderLeftColor: colorCategoria(grupo.id) }}
            >
              {grupo.nombre} <span className="cuenta-categoria">({grupo.platos.length})</span>
            </summary>
            <div className="platos-categoria">
              {grupo.platos.map((p) => (
                <FilaPlato
                  key={p.id}
                  plato={p}
                  nombreCategoria={grupo.nombre}
                  onCambiado={(nuevo) => onActualizar(p, nuevo)}
                  onQuitarDeLista={() => onQuitar(p)}
                />
              ))}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
