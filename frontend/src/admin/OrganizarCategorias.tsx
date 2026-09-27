import { useEffect, useState } from "react";

import { colorCategoria } from "../carta/iconos";
import {
  cargarProductos,
  crearCategoria,
  eliminarCategoria,
  guardarDestinoCategoria,
  ordenarCategorias,
  renombrarCategoria,
  type Destino,
} from "./api";
import { CATEGORIA_ESPECIALES, type Categoria, type Plato } from "./types";
import { useArrastreOrden } from "./useArrastreOrden";

interface Props {
  categorias: Categoria[];
  platos: Plato[] | null;
  onCambio: (categorias: Categoria[]) => void;
}

export function OrganizarCategorias({ categorias, platos, onCambio }: Props) {
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [editando, setEditando] = useState<string | null>(null);
  const [nombreEditado, setNombreEditado] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  // A qué pantalla van los platos de cada categoría al pedir desde la mesa.
  // null = aún cargando (o sin conexión): el botón no se enseña.
  const [destinos, setDestinos] = useState<Record<string, Destino> | null>(null);

  useEffect(() => {
    cargarProductos()
      .then((c) => setDestinos(c.destinos_categoria))
      .catch(() => setDestinos(null));
  }, []);

  function cambiarDestino(c: Categoria) {
    if (destinos === null) return;
    const nuevo: Destino = (destinos[c.id] ?? "cocina") === "cocina" ? "barra" : "cocina";
    void ejecutar(async () => {
      const resp = await guardarDestinoCategoria(c.id, nuevo);
      if (resp.status === 204) {
        setDestinos((actual) => ({ ...(actual ?? {}), [c.id]: nuevo }));
      } else {
        setAviso("No se pudo cambiar dónde se prepara. Inténtalo de nuevo.");
      }
    });
  }

  // La del "especial del dia" es interna: se gestiona en su propia seccion.
  const base = categorias.filter((c) => c.id !== CATEGORIA_ESPECIALES);
  const especial = categorias.filter((c) => c.id === CATEGORIA_ESPECIALES);

  function cuantosPlatos(id: string): number {
    return platos?.filter((p) => p.categoria === id).length ?? 0;
  }

  // Envuelve cada accion: un solo sitio para el "ocupado" y los errores de red.
  async function ejecutar(accion: () => Promise<void>) {
    setAviso(null);
    setOcupado(true);
    try {
      await accion();
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  }

  function anadir() {
    const nombre = nuevoNombre.trim();
    if (!nombre) return;
    void ejecutar(async () => {
      const resp = await crearCategoria(nombre);
      if (resp.status === 201) {
        const creada: Categoria = await resp.json();
        onCambio([...categorias, creada]);
        setNuevoNombre("");
      } else {
        setAviso("Ese nombre no vale: debe tener letras o números (máximo 60).");
      }
    });
  }

  function guardarNombre(id: string) {
    const nombre = nombreEditado.trim();
    if (!nombre) return;
    void ejecutar(async () => {
      const resp = await renombrarCategoria(id, nombre);
      if (resp.ok) {
        const nueva: Categoria = await resp.json();
        onCambio(categorias.map((c) => (c.id === id ? nueva : c)));
        setEditando(null);
      } else if (resp.status === 404) {
        setAviso("Esa categoría ya no existe.");
      } else {
        setAviso("Ese nombre no vale: debe tener letras o números (máximo 60).");
      }
    });
  }

  function guardarOrden(reordenada: Categoria[]) {
    void ejecutar(async () => {
      const resp = await ordenarCategorias(reordenada.map((c) => c.id));
      if (resp.status === 204) {
        // Mismos numeros de orden que el servidor: 1..n en la nueva secuencia.
        onCambio([...especial, ...reordenada.map((c, i) => ({ ...c, orden: i + 1 }))]);
      } else {
        setAviso("No se pudo cambiar el orden. Recarga la página e inténtalo de nuevo.");
      }
    });
  }

  const { lista, arrastrandoId, refFila, asa } = useArrastreOrden(base, guardarOrden, ocupado);

  function borrar(c: Categoria) {
    if (!window.confirm(`¿Eliminar la categoría "${c.nombre}"? No se puede deshacer.`)) return;
    void ejecutar(async () => {
      const resp = await eliminarCategoria(c.id);
      if (resp.status === 204 || resp.status === 404) {
        onCambio(categorias.filter((x) => x.id !== c.id));
      } else if (resp.status === 409) {
        setAviso("La categoría tiene platos: muévelos o elimínalos antes de borrarla.");
      } else {
        setAviso("No se pudo eliminar. Inténtalo de nuevo.");
      }
    });
  }

  return (
    <div className="organizar">
        <p className="ayuda">Arrastra con el dedo el icono ⠿ para cambiar el orden de las categorías.</p>
        {destinos !== null && (
          <p className="ayuda">
            «Cocina» o «Barra» dice dónde se preparan sus platos al pedir desde la mesa. Toca para
            cambiarlo; un plato suelto puede llevar otro en su «Para pedir».
          </p>
        )}
        {lista.length === 0 && <p className="cargando">Todavía no hay categorías.</p>}

        {lista.map((c) => {
          const total = cuantosPlatos(c.id);
          return (
            <div
              key={c.id}
              ref={refFila(c.id)}
              className={"fila-categoria" + (arrastrandoId === c.id ? " arrastrando" : "")}
              style={{ borderLeftColor: colorCategoria(c.id) }}
            >
              {editando === c.id ? (
                <>
                  <input
                    value={nombreEditado}
                    maxLength={60}
                    autoFocus
                    aria-label="Nuevo nombre de la categoría"
                    onChange={(e) => setNombreEditado(e.target.value)}
                  />
                  <button type="button" disabled={ocupado} onClick={() => guardarNombre(c.id)}>
                    OK
                  </button>
                  <button type="button" onClick={() => setEditando(null)}>
                    ✕
                  </button>
                </>
              ) : (
                <>
                  <span className="nombre-categoria">
                    {c.nombre} <span className="cuenta-categoria">({total})</span>
                  </span>
                  {destinos !== null && (
                    <button
                      type="button"
                      className={"destino-categoria destino-" + (destinos[c.id] ?? "cocina")}
                      aria-label={`${c.nombre} se prepara en ${destinos[c.id] ?? "cocina"}. Cambiar`}
                      disabled={ocupado}
                      onClick={() => cambiarDestino(c)}
                    >
                      {(destinos[c.id] ?? "cocina") === "cocina" ? "Cocina" : "Barra"}
                    </button>
                  )}
                  <button
                    type="button"
                    className="asa"
                    aria-label={`Arrastrar ${c.nombre} para cambiar su orden`}
                    disabled={ocupado}
                    {...asa(c.id)}
                  >
                    ⠿
                  </button>
                  <button
                    type="button"
                    aria-label={`Renombrar ${c.nombre}`}
                    disabled={ocupado}
                    onClick={() => {
                      setEditando(c.id);
                      setNombreEditado(c.nombre);
                    }}
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    aria-label={`Eliminar ${c.nombre}`}
                    title={total > 0 ? "Solo se pueden eliminar categorías vacías" : undefined}
                    disabled={ocupado || total > 0}
                    onClick={() => borrar(c)}
                  >
                    🗑
                  </button>
                </>
              )}
            </div>
          );
        })}

        <form
          className="form-categoria-nueva"
          onSubmit={(e) => {
            e.preventDefault();
            anadir();
          }}
        >
          <input
            value={nuevoNombre}
            maxLength={60}
            placeholder="Nueva categoría…"
            aria-label="Nombre de la nueva categoría"
            onChange={(e) => setNuevoNombre(e.target.value)}
          />
          <button type="submit" className="primario" disabled={ocupado || !nuevoNombre.trim()}>
            Añadir
          </button>
        </form>

        {aviso && <div className="aviso visible error">{aviso}</div>}
      </div>
  );
}
