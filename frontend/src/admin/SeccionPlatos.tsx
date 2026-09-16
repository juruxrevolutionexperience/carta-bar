import { FilaPlato } from "./FilaPlato";
import type { Plato } from "./types";

interface Props {
  platos: Plato[] | null;
  error: boolean;
  categoriasPorId: Record<string, string>;
  onActualizar: (anterior: Plato, nuevo: Plato) => void;
  onQuitar: (objetivo: Plato) => void;
}

export function SeccionPlatos({ platos, error, categoriasPorId, onActualizar, onQuitar }: Props) {
  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Platos</h2>
        <div>
          {error && <p className="cargando">No se pudo cargar la carta.</p>}
          {!error && platos === null && <p className="cargando">Cargando…</p>}
          {!error && platos !== null && platos.length === 0 && (
            <p className="cargando">No hay platos.</p>
          )}
          {platos?.map((p) => (
            <FilaPlato
              key={p.id}
              plato={p}
              nombreCategoria={categoriasPorId[p.categoria] || p.categoria}
              onCambiado={(nuevo) => onActualizar(p, nuevo)}
              onQuitarDeLista={() => onQuitar(p)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
