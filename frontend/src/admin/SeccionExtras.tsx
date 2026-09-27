import { useEffect, useState } from "react";

import {
  actualizarGrupo,
  cargarProductos,
  crearGrupo,
  eliminarGrupo,
  type ConfigProductos,
  type GrupoOpciones,
} from "./api";
import { FilasPrecio, filasAValores, valoresAFilas, type FilaPrecio } from "./FilasPrecio";
import { resumenGrupo, textoPrecio } from "./textosProductos";

// Grupos de extras y opciones reutilizables: se crean aquí una vez ("Extras de
// hamburguesa", "Punto de la carne") y se marcan en cada plato, en "Para pedir".
// Cambiar un precio aquí vale para todos los platos que lo tengan.
export function SeccionExtras() {
  const [config, setConfig] = useState<ConfigProductos | null>(null);
  const [error, setError] = useState(false);
  // null = nada abierto; "nuevo" = creando; otro = id del grupo que se edita.
  const [editando, setEditando] = useState<string | null>(null);

  function recargar() {
    cargarProductos()
      .then((c) => {
        setConfig(c);
        setError(false);
      })
      .catch(() => setError(true));
  }

  useEffect(recargar, []);

  function platosCon(id: string): number {
    return Object.values(config?.platos ?? {}).filter((p) => p.grupos.includes(id)).length;
  }

  if (config === null) {
    return (
      <div className="tarjeta">
        <p>{error ? "No se pudieron cargar los extras." : "Cargando…"}</p>
      </div>
    );
  }

  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Extras y opciones</h2>
        <p>
          Crea aquí cada grupo una sola vez y márcalo luego en los platos que lo lleven (al
          editar el plato, en «Para pedir»). Obligatorio es lo que el camarero preguntaría
          siempre, como el punto de la carne; opcional, los extras.
        </p>
        {editando !== "nuevo" && (
          <button type="button" className="primario" onClick={() => setEditando("nuevo")}>
            + Nuevo grupo
          </button>
        )}
      </div>

      {editando === "nuevo" && (
        <EditorGrupo
          onGuardado={() => {
            setEditando(null);
            recargar();
          }}
          onCancelar={() => setEditando(null)}
        />
      )}

      {config.grupos.length === 0 && editando !== "nuevo" && (
        <p className="cargando">Todavía no hay ningún grupo.</p>
      )}

      {config.grupos.map((g) =>
        editando === g.id ? (
          <EditorGrupo
            key={g.id}
            grupo={g}
            onGuardado={() => {
              setEditando(null);
              recargar();
            }}
            onCancelar={() => setEditando(null)}
          />
        ) : (
          <div className="tarjeta tarjeta-grupo" key={g.id}>
            <div className="cabecera-grupo">
              <h2>{g.nombre}</h2>
              <span className="resumen-grupo">{resumenGrupo(g)}</span>
            </div>
            <ul className="opciones-grupo">
              {g.opciones.map((o) => (
                <li key={o.nombre}>
                  <span>{o.nombre}</span>
                  <span className="precio-opcion">{textoPrecio(o.precio)}</span>
                </li>
              ))}
            </ul>
            <p className="uso-grupo">
              {platosCon(g.id) === 0
                ? "No está en ningún plato todavía."
                : `En ${platosCon(g.id)} ${platosCon(g.id) === 1 ? "plato" : "platos"}.`}
            </p>
            <button type="button" className="secundario" onClick={() => setEditando(g.id)}>
              Editar
            </button>
          </div>
        )
      )}
    </section>
  );
}

interface PropsEditor {
  grupo?: GrupoOpciones;
  onGuardado: () => void;
  onCancelar: () => void;
}

function EditorGrupo({ grupo, onGuardado, onCancelar }: PropsEditor) {
  const [nombre, setNombre] = useState(grupo?.nombre ?? "");
  const [obligatorio, setObligatorio] = useState((grupo?.minimo ?? 0) > 0);
  const [maximo, setMaximo] = useState(grupo?.maximo ?? 1);
  const [filas, setFilas] = useState<FilaPrecio[]>(
    grupo ? valoresAFilas(grupo.opciones) : [{ nombre: "", precio: "" }]
  );
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  async function guardar() {
    setAviso(null);
    if (!nombre.trim()) {
      setAviso("Ponle un nombre al grupo.");
      return;
    }
    const opciones = filasAValores(filas, true);
    if (typeof opciones === "string") {
      setAviso(opciones);
      return;
    }
    if (opciones.length === 0) {
      setAviso("Añade al menos una opción.");
      return;
    }
    const maximoReal = Math.min(Math.max(1, maximo), opciones.length);
    // Obligatorio = hay que elegir al menos uno (y como mucho `maximo`).
    const datos = {
      nombre: nombre.trim(),
      minimo: obligatorio ? 1 : 0,
      maximo: maximoReal,
      opciones,
    };
    setOcupado(true);
    try {
      const resp = grupo ? await actualizarGrupo(grupo.id, datos) : await crearGrupo(datos);
      if (resp.ok) {
        onGuardado();
        return;
      }
      setAviso(
        resp.status === 404 ? "Este grupo ya no existe." : "Revisa los datos e inténtalo otra vez."
      );
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  }

  async function borrar() {
    if (!grupo) return;
    if (
      !window.confirm(`¿Eliminar "${grupo.nombre}"? Se quitará de todos los platos que lo tengan.`)
    ) {
      return;
    }
    setOcupado(true);
    try {
      const resp = await eliminarGrupo(grupo.id);
      if (resp.status === 204 || resp.status === 404) {
        onGuardado();
        return;
      }
      setAviso("No se pudo eliminar. Inténtalo de nuevo.");
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="tarjeta editor-grupo">
      <label htmlFor="grupo-nombre">Nombre del grupo</label>
      <input
        id="grupo-nombre"
        value={nombre}
        maxLength={60}
        placeholder="Extras de hamburguesa"
        onChange={(e) => setNombre(e.target.value)}
      />

      <label className="opcion">
        <input
          type="checkbox"
          checked={obligatorio}
          onChange={(e) => setObligatorio(e.target.checked)}
        />
        Obligatorio (el cliente tiene que elegir)
      </label>

      <label htmlFor="grupo-maximo">Cuántas se pueden elegir como mucho</label>
      <input
        id="grupo-maximo"
        type="number"
        min={1}
        max={30}
        value={maximo}
        onChange={(e) => setMaximo(Math.max(1, Number(e.target.value) || 1))}
      />

      <label>Opciones (precio vacío = gratis)</label>
      <FilasPrecio
        filas={filas}
        onCambio={setFilas}
        ejemploNombre="Queso"
        precioOpcional={true}
        maximo={30}
        textoAnadir="Añadir opción"
      />

      <button type="button" className="primario" disabled={ocupado} onClick={guardar}>
        Guardar
      </button>
      <button type="button" className="secundario" onClick={onCancelar}>
        Cancelar
      </button>
      {grupo && (
        <button type="button" className="secundario peligro" disabled={ocupado} onClick={borrar}>
          Eliminar grupo
        </button>
      )}
      {aviso && <div className="aviso visible error">{aviso}</div>}
    </div>
  );
}
