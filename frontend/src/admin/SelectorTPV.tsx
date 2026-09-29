import { useEffect, useState } from "react";

import { cargarCarta, cargarCategorias } from "./api";
import { cargarGruposDePlato, type GrupoOpciones, type NuevaLineaComanda } from "./api";
import { CATEGORIA_ESPECIALES, type Categoria, type Plato } from "./types";

interface Props {
  onElegir: (datos: NuevaLineaComanda) => Promise<boolean>;
  onCerrar: () => void;
}

// Parrilla estilo TPV para que el camarero anada algo en nombre de la mesa:
// pestanas de categoria arriba, botones grandes por plato debajo. Un plato
// sin formato ni extras obligatorios se anade con un solo toque; si necesita
// elegir algo, se abre un paso mas antes (ChoosePlato).
export function SelectorTPV({ onElegir, onCerrar }: Props) {
  const [carta, setCarta] = useState<Plato[] | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [categoriaId, setCategoriaId] = useState<string | null>(null);
  const [eligiendo, setEligiendo] = useState<Plato | null>(null);

  useEffect(() => {
    Promise.all([cargarCarta(), cargarCategorias()]).then(([platos, cats]) => {
      const ordenadas = [...cats]
        .filter((c) => c.id !== CATEGORIA_ESPECIALES)
        .sort((a, b) => a.orden - b.orden);
      setCarta(platos);
      setCategorias(ordenadas);
      setCategoriaId(ordenadas[0]?.id ?? null);
    });
  }, []);

  const disponibles = (carta ?? []).filter((p) => p.disponible && p.id);
  const visibles = disponibles.filter((p) => p.categoria === categoriaId);

  async function tocar(plato: Plato) {
    if ((plato.formatos?.length ?? 0) > 0) {
      setEligiendo(plato);
      return;
    }
    const grupos = await cargarGruposDePlato(plato.id as string);
    if (grupos.some((g) => g.minimo > 0)) {
      setEligiendo(plato);
      return;
    }
    await onElegir({ plato_id: plato.id as string, cantidad: 1 });
  }

  return (
    <div className="velo-tpv" onClick={onCerrar}>
      <div className="selector-tpv" onClick={(e) => e.stopPropagation()}>
        <div className="cabecera-panel">
          <h3>Añadir a la mesa</h3>
          <button type="button" className="cerrar-panel" aria-label="Cerrar" onClick={onCerrar}>
            <svg viewBox="0 0 24 24">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>

        <div className="pestanas-categoria-tpv">
          {categorias.map((c) => (
            <button
              key={c.id}
              type="button"
              className={"pestana-tpv" + (categoriaId === c.id ? " activa" : "")}
              onClick={() => setCategoriaId(c.id)}
            >
              {c.nombre}
            </button>
          ))}
        </div>

        {carta === null ? (
          <p className="explicacion">Cargando la carta…</p>
        ) : (
          <div className="rejilla-tpv">
            {visibles.map((p) => (
              <button key={p.id} type="button" className="tile-tpv" onClick={() => void tocar(p)}>
                <span className="tile-nombre">{p.nombre}</span>
                <span className="tile-precio">
                  {(p.formatos?.length ?? 0) > 0
                    ? "Varios precios"
                    : p.precio != null
                      ? `${p.precio.toFixed(2).replace(".", ",")} €`
                      : "—"}
                </span>
              </button>
            ))}
            {visibles.length === 0 && <p className="explicacion">Sin platos en esta categoría.</p>}
          </div>
        )}
      </div>

      {eligiendo && (
        <ElegirDetallePlato
          plato={eligiendo}
          onCancelar={() => setEligiendo(null)}
          onConfirmar={async (datos) => {
            const ok = await onElegir(datos);
            if (ok) setEligiendo(null);
          }}
        />
      )}
    </div>
  );
}

interface PropsDetalle {
  plato: Plato;
  onCancelar: () => void;
  onConfirmar: (datos: NuevaLineaComanda) => Promise<void>;
}

// El mismo paso que ya hace el cliente al pedir desde la carta
// (FormularioPropuesta.tsx), aqui para cuando el camarero anade un plato con
// extras obligatorios (ej. "Punto de la carne").
function ElegirDetallePlato({ plato, onCancelar, onConfirmar }: PropsDetalle) {
  const [grupos, setGrupos] = useState<GrupoOpciones[]>([]);
  const [elegidas, setElegidas] = useState<string[]>([]);
  const [formato, setFormato] = useState<string | null>(plato.formatos?.[0]?.nombre ?? null);
  const [cantidad, setCantidad] = useState(1);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    cargarGruposDePlato(plato.id as string).then(setGrupos);
  }, [plato.id]);

  function alternar(grupo: GrupoOpciones, nombre: string) {
    setElegidas((actual) => {
      const enEsteGrupo = (n: string) => grupo.opciones.some((o) => o.nombre === n);
      if (grupo.maximo === 1) {
        const sinGrupo = actual.filter((n) => !enEsteGrupo(n));
        return actual.includes(nombre) ? sinGrupo : [...sinGrupo, nombre];
      }
      if (actual.includes(nombre)) return actual.filter((n) => n !== nombre);
      if (actual.filter(enEsteGrupo).length >= grupo.maximo) return actual;
      return [...actual, nombre];
    });
  }

  async function confirmar() {
    for (const g of grupos) {
      const elegidasDelGrupo = elegidas.filter((n) => g.opciones.some((o) => o.nombre === n));
      if (elegidasDelGrupo.length < g.minimo) {
        setError(`Elige "${g.nombre}" antes de añadir.`);
        return;
      }
    }
    setEnviando(true);
    setError(null);
    await onConfirmar({ plato_id: plato.id as string, formato, opciones: elegidas, cantidad });
    setEnviando(false);
  }

  return (
    <div className="velo-tpv" onClick={onCancelar}>
      <div className="tarjeta editor-grupo" onClick={(e) => e.stopPropagation()}>
        <h3>{plato.nombre}</h3>
        {(plato.formatos?.length ?? 0) > 0 && (
          <div className="grupo-eleccion-tpv">
            <label>Formato</label>
            {plato.formatos!.map((f) => (
              <label className="opcion" key={f.nombre}>
                <input
                  type="radio"
                  checked={formato === f.nombre}
                  onChange={() => setFormato(f.nombre)}
                />
                {f.nombre} ({f.precio.toFixed(2).replace(".", ",")} €)
              </label>
            ))}
          </div>
        )}
        {grupos.map((g) => (
          <div key={g.id} className="grupo-eleccion-tpv">
            <label>
              {g.nombre}
              {g.minimo > 0 && " (obligatorio)"}
            </label>
            {g.opciones.map((o) => (
              <label className="opcion" key={o.nombre}>
                <input
                  type={g.maximo === 1 ? "radio" : "checkbox"}
                  checked={elegidas.includes(o.nombre)}
                  onChange={() => alternar(g, o.nombre)}
                />
                {o.nombre}
                {o.precio > 0 && ` (+${o.precio.toFixed(2).replace(".", ",")} €)`}
              </label>
            ))}
          </div>
        ))}
        <label htmlFor="cantidad-tpv">Cantidad</label>
        <input
          id="cantidad-tpv"
          type="number"
          min={1}
          max={20}
          value={cantidad}
          onChange={(e) => setCantidad(Math.max(1, Number(e.target.value) || 1))}
        />
        <button type="button" className="primario" disabled={enviando} onClick={() => void confirmar()}>
          Añadir
        </button>
        <button type="button" className="secundario" onClick={onCancelar}>
          Cancelar
        </button>
        {error && <div className="aviso visible error">{error}</div>}
      </div>
    </div>
  );
}
