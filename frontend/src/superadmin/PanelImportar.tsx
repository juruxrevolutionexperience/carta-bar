import { useEffect, useState } from "react";

import {
  cargarCategoriasRestaurante,
  crearCategoriaRestaurante,
  crearPlatoRestaurante,
  leerCartaDeFoto,
  type Categoria,
  type PlatoLeido,
} from "./api";

interface Props {
  restauranteId: string;
  onCerrar: () => void;
}

interface FilaEditable {
  incluir: boolean;
  nombre: string;
  descripcion: string;
  ingredientes: string; // editado como texto separado por comas
  precio: string; // editado como texto, se valida al crear
}

function aFila(p: PlatoLeido): FilaEditable {
  return {
    incluir: true,
    nombre: p.nombre,
    descripcion: p.descripcion,
    ingredientes: p.ingredientes.join(", "),
    precio: p.precio == null ? "" : String(p.precio),
  };
}

// Herramienta de uso propio, no del gerente: lee una foto de una carta en
// papel con el modelo (cuesta unos centimos) y propone los platos en una
// tabla editable. No se crea nada hasta pulsar "Crear".
export function PanelImportar({ restauranteId, onCerrar }: Props) {
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [nuevaCategoria, setNuevaCategoria] = useState("");
  const [leyendo, setLeyendo] = useState(false);
  const [filas, setFilas] = useState<FilaEditable[] | null>(null);
  const [creando, setCreando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [creados, setCreados] = useState(0);

  useEffect(() => {
    cargarCategoriasRestaurante(restauranteId)
      .then((cats) => {
        setCategorias(cats);
        if (cats[0]) setCategoriaId(cats[0].id);
      })
      .catch(() => setAviso("No se pudieron cargar las categorías de este restaurante."));
  }, [restauranteId]);

  async function alElegirFoto(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setAviso(null);
    setLeyendo(true);
    try {
      const leidos = await leerCartaDeFoto(restauranteId, archivo);
      setFilas(leidos.map(aFila));
    } catch {
      setAviso("No se pudo leer la foto. Prueba con otra o inténtalo de nuevo.");
    } finally {
      setLeyendo(false);
    }
  }

  function cambiarFila(i: number, cambios: Partial<FilaEditable>) {
    setFilas((actual) => actual?.map((f, idx) => (idx === i ? { ...f, ...cambios } : f)) ?? actual);
  }

  async function crearTodos() {
    if (!filas) return;
    setAviso(null);
    setCreando(true);
    setCreados(0);
    try {
      let destino = categoriaId;
      const nombreNueva = nuevaCategoria.trim();
      if (nombreNueva) {
        const creada = await crearCategoriaRestaurante(restauranteId, nombreNueva);
        destino = creada.id;
        setCategorias((c) => [...c, creada]);
        setCategoriaId(creada.id);
        setNuevaCategoria("");
      }
      if (!destino) {
        setAviso("Elige o crea una categoría antes de crear los platos.");
        return;
      }
      const incluidas = filas.filter((f) => f.incluir);
      let hechos = 0;
      for (const f of incluidas) {
        const precio = f.precio.trim() === "" ? null : Number(f.precio.replace(",", "."));
        const resp = await crearPlatoRestaurante(restauranteId, {
          categoria: destino,
          nombre: f.nombre.trim(),
          descripcion: f.descripcion.trim(),
          precio: precio !== null && !Number.isNaN(precio) ? precio : null,
          ingredientes: f.ingredientes
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        });
        if (resp.ok) {
          hechos += 1;
          setCreados(hechos);
        }
      }
      if (hechos === incluidas.length) {
        setFilas(null);
        setAviso(`Creados ${hechos} platos. Se están traduciendo en segundo plano.`);
      } else {
        setAviso(`Creados ${hechos} de ${incluidas.length}. Revisa los que fallaron e inténtalo de nuevo.`);
      }
    } catch {
      setAviso("Algo falló creando los platos. Revisa cuáles se quedaron a medias.");
    } finally {
      setCreando(false);
    }
  }

  return (
    <div className="panel-tarjeta">
      <h2>Importar platos de una foto — {restauranteId}</h2>
      <p className="sub">
        Sube una foto de la carta en papel; el modelo propone los platos y tú los revisas antes de
        crear nada.
      </p>

      {!filas && (
        <label className="boton-archivo">
          {leyendo ? "Leyendo la foto…" : "Elegir foto"}
          <input type="file" accept="image/jpeg" hidden disabled={leyendo} onChange={alElegirFoto} />
        </label>
      )}

      {filas && filas.length > 0 && (
        <>
          <div className="tabla-scroll">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Nombre</th>
                  <th>Descripción</th>
                  <th>Ingredientes</th>
                  <th>Precio</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f, i) => (
                  <tr key={i}>
                    <td>
                      <input
                        type="checkbox"
                        checked={f.incluir}
                        onChange={(e) => cambiarFila(i, { incluir: e.target.checked })}
                        aria-label={`Incluir ${f.nombre || "este plato"}`}
                      />
                    </td>
                    <td>
                      <input
                        value={f.nombre}
                        onChange={(e) => cambiarFila(i, { nombre: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        value={f.descripcion}
                        onChange={(e) => cambiarFila(i, { descripcion: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        value={f.ingredientes}
                        onChange={(e) => cambiarFila(i, { ingredientes: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        value={f.precio}
                        inputMode="decimal"
                        style={{ width: "70px" }}
                        onChange={(e) => cambiarFila(i, { precio: e.target.value })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <label>Categoría de destino</label>
          <select value={categoriaId} onChange={(e) => setCategoriaId(e.target.value)}>
            {categorias.length === 0 && <option value="">— sin categorías todavía —</option>}
            {categorias.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          <label>O crea una categoría nueva</label>
          <input
            value={nuevaCategoria}
            placeholder="p. ej. Tostas"
            onChange={(e) => setNuevaCategoria(e.target.value)}
          />

          <button type="button" className="primario" disabled={creando} onClick={crearTodos}>
            {creando
              ? `Creando… (${creados}/${filas.filter((f) => f.incluir).length})`
              : `Crear ${filas.filter((f) => f.incluir).length} platos`}
          </button>
          <button type="button" className="secundario" disabled={creando} onClick={() => setFilas(null)}>
            Empezar de nuevo
          </button>
        </>
      )}

      {filas && filas.length === 0 && (
        <p className="cargando">No se reconoció ningún plato en la foto.</p>
      )}

      {aviso && <div className="aviso visible exito">{aviso}</div>}

      <button type="button" className="secundario" onClick={onCerrar}>
        Cerrar
      </button>
    </div>
  );
}
