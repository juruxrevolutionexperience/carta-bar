import { FilaPlato } from "./FilaPlato";
import type { Plato } from "./types";

interface Props {
  especiales: Plato[] | null;
  error: boolean;
  categoriasPorId: Record<string, string>;
  onActualizar: (anterior: Plato, nuevo: Plato) => void;
  onQuitar: (objetivo: Plato) => void;
  onAnadir: () => void;
}

export function SeccionEspeciales({
  especiales,
  error,
  categoriasPorId,
  onActualizar,
  onQuitar,
  onAnadir,
}: Props) {
  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Especial de hoy</h2>
        <p>
          Platos fuera de la carta fija. Aparecen en una sección propia en la
          carta pública mientras estén aquí; quítalos cuando ya no toque.
        </p>
        <button type="button" className="primario" onClick={onAnadir}>
          + Añadir especial
        </button>
      </div>
      <div>
        {error && <p className="cargando">No se pudo cargar la carta.</p>}
        {!error && especiales === null && <p className="cargando">Cargando…</p>}
        {!error && especiales !== null && especiales.length === 0 && (
          <p className="cargando">No hay especiales activos.</p>
        )}
        {especiales?.map((p, i) => (
          <FilaPlato
            key={p.id ?? `nuevo-${i}`}
            plato={p}
            nombreCategoria={categoriasPorId[p.categoria] || p.categoria}
            onCambiado={(nuevo) => onActualizar(p, nuevo)}
            onQuitarDeLista={() => onQuitar(p)}
          />
        ))}
      </div>
    </section>
  );
}
