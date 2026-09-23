import { useState } from "react";

import { crearZona, eliminarZona, ordenarZonas, renombrarZona, type Mesa, type Zona } from "./api";
import { useArrastreOrden } from "./useArrastreOrden";

interface Props {
  zonas: Zona[];
  mesas: Mesa[];
  onCambio: (zonas: Zona[]) => void;
  // Tras borrar una zona (que se lleva sus mesas) hay que volver a pedir todo.
  onRecargar: () => void;
}

export function OrganizarZonas({ zonas, mesas, onCambio, onRecargar }: Props) {
  const [nuevoNombre, setNuevoNombre] = useState("");
  const [editando, setEditando] = useState<string | null>(null);
  const [nombreEditado, setNombreEditado] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  function cuantasMesas(id: string): number {
    return mesas.filter((m) => m.zona_id === id).length;
  }

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

  function guardarOrden(reordenadas: Zona[]) {
    void ejecutar(async () => {
      const resp = await ordenarZonas(reordenadas.map((z) => z.id));
      if (resp.status === 204) {
        onCambio(reordenadas.map((z, i) => ({ ...z, orden: i + 1 })));
      } else {
        setAviso("No se pudo cambiar el orden. Recarga la página e inténtalo de nuevo.");
      }
    });
  }

  const { lista, arrastrandoId, refFila, asa } = useArrastreOrden(zonas, guardarOrden, ocupado);

  function anadir() {
    const nombre = nuevoNombre.trim();
    if (!nombre) return;
    void ejecutar(async () => {
      const resp = await crearZona(nombre);
      if (resp.status !== 201) {
        setAviso("Ese nombre no vale (máximo 60 letras).");
        return;
      }
      const creada: Zona = await resp.json();
      onCambio([...zonas, creada]);
      setNuevoNombre("");
    });
  }

  function guardarNombre(id: string) {
    const nombre = nombreEditado.trim();
    if (!nombre) return;
    void ejecutar(async () => {
      const resp = await renombrarZona(id, nombre);
      if (!resp.ok) {
        setAviso(resp.status === 404 ? "Esa zona ya no existe." : "Ese nombre no vale.");
        return;
      }
      const nueva: Zona = await resp.json();
      onCambio(zonas.map((z) => (z.id === id ? nueva : z)));
      setEditando(null);
    });
  }

  function borrar(zona: Zona) {
    const n = cuantasMesas(zona.id);
    const aviso =
      n > 0
        ? `¿Eliminar la zona "${zona.nombre}" y sus ${n} mesas? No se puede deshacer.`
        : `¿Eliminar la zona "${zona.nombre}"? No se puede deshacer.`;
    if (!window.confirm(aviso)) return;
    void ejecutar(async () => {
      const resp = await eliminarZona(zona.id);
      if (resp.status === 204 || resp.status === 404) {
        onRecargar();
      } else if (resp.status === 409) {
        setAviso("Hay clientes sentados en una mesa de esta zona: espera a que se cierre.");
      } else {
        setAviso("No se pudo eliminar. Inténtalo de nuevo.");
      }
    });
  }

  return (
    <div className="tarjeta organizar">
      <h3>Zonas del local</h3>
      <p className="ayuda">
        Arrastra el icono ⠿ para cambiar el orden de las pestañas. Ej.: Terraza, Barra, Salón 1.
      </p>

      {lista.map((z) => (
        <div
          key={z.id}
          ref={refFila(z.id)}
          className={"fila-categoria" + (arrastrandoId === z.id ? " arrastrando" : "")}
        >
          {editando === z.id ? (
            <>
              <input
                value={nombreEditado}
                maxLength={60}
                autoFocus
                aria-label="Nuevo nombre de la zona"
                onChange={(e) => setNombreEditado(e.target.value)}
              />
              <button type="button" disabled={ocupado} onClick={() => guardarNombre(z.id)}>
                OK
              </button>
              <button type="button" onClick={() => setEditando(null)}>
                ✕
              </button>
            </>
          ) : (
            <>
              <span className="nombre-categoria">
                {z.nombre} <span className="cuenta-categoria">({cuantasMesas(z.id)})</span>
              </span>
              <button
                type="button"
                className="asa"
                aria-label={`Arrastrar ${z.nombre} para cambiar su orden`}
                disabled={ocupado}
                {...asa(z.id)}
              >
                ⠿
              </button>
              <button
                type="button"
                aria-label={`Renombrar ${z.nombre}`}
                disabled={ocupado}
                onClick={() => {
                  setEditando(z.id);
                  setNombreEditado(z.nombre);
                }}
              >
                ✎
              </button>
              <button
                type="button"
                aria-label={`Eliminar ${z.nombre}`}
                disabled={ocupado}
                onClick={() => borrar(z)}
              >
                🗑
              </button>
            </>
          )}
        </div>
      ))}

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
          placeholder="Nueva zona…"
          aria-label="Nombre de la nueva zona"
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
