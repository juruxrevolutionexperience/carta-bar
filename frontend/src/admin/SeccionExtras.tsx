import { useEffect, useState } from "react";

import {
  actualizarGrupo,
  asignarGrupoAPlatos,
  cargarCarta,
  cargarCategorias,
  cargarProductos,
  crearGrupo,
  eliminarGrupo,
  type ConfigProductos,
  type GrupoOpciones,
} from "./api";
import { FilasPrecio, filasAValores, valoresAFilas, type FilaPrecio } from "./FilasPrecio";
import { resumenGrupo, textoPrecio } from "./textosProductos";
import type { Categoria, Plato } from "./types";

// Grupos de extras y opciones reutilizables: se crean aquí una vez ("Extras de
// hamburguesa", "Punto de la carne") y se marcan en cada plato, en "Para pedir".
// Cambiar un precio aquí vale para todos los platos que lo tengan.
export function SeccionExtras() {
  const [config, setConfig] = useState<ConfigProductos | null>(null);
  const [carta, setCarta] = useState<Plato[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [error, setError] = useState(false);
  // null = nada abierto; "nuevo" = creando; otro = id del grupo que se edita.
  const [editando, setEditando] = useState<string | null>(null);
  // Grupo cuya lista de platos esta desplegada (para "asignar a varios de golpe").
  const [asignando, setAsignando] = useState<string | null>(null);

  function recargar() {
    cargarProductos()
      .then((c) => {
        setConfig(c);
        setError(false);
      })
      .catch(() => setError(true));
  }

  useEffect(recargar, []);
  useEffect(() => {
    cargarCarta().then(setCarta);
    cargarCategorias().then(setCategorias);
  }, []);

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
            <div className="acciones-grupo">
              <button type="button" className="secundario" onClick={() => setEditando(g.id)}>
                Editar
              </button>
              <button
                type="button"
                className="secundario"
                onClick={() => setAsignando(asignando === g.id ? null : g.id)}
              >
                {asignando === g.id ? "Cerrar" : "Asignar a platos"}
              </button>
            </div>
            {asignando === g.id && (
              <AsignarPlatos
                grupo={g}
                carta={carta}
                categorias={categorias}
                asignados={
                  new Set(
                    Object.entries(config.platos)
                      .filter(([, p]) => p.grupos.includes(g.id))
                      .map(([id]) => id)
                  )
                }
                onGuardado={(nuevaConfig) => {
                  setConfig(nuevaConfig);
                  setAsignando(null);
                }}
              />
            )}
          </div>
        )
      )}
    </section>
  );
}

interface PropsAsignar {
  grupo: GrupoOpciones;
  carta: Plato[];
  categorias: Categoria[];
  asignados: Set<string>;
  onGuardado: (config: ConfigProductos) => void;
}

// El "marcar de golpe" en el que se pensó todo esto: en vez de abrir cada
// plato de carne para tildar "Punto de la carne", se hace una vez desde aqui.
function AsignarPlatos({ grupo, carta, categorias, asignados, onGuardado }: PropsAsignar) {
  const [elegidos, setElegidos] = useState<Set<string>>(new Set(asignados));
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const nombreCategoria = new Map(categorias.map((c) => [c.id, c.nombre]));
  const porCategoria = new Map<string, Plato[]>();
  for (const p of carta) {
    if (!p.id) continue;
    const lista = porCategoria.get(p.categoria) ?? [];
    lista.push(p);
    porCategoria.set(p.categoria, lista);
  }

  function alternar(id: string) {
    setElegidos((actual) => {
      const nuevo = new Set(actual);
      if (nuevo.has(id)) nuevo.delete(id);
      else nuevo.add(id);
      return nuevo;
    });
  }

  async function guardar() {
    setOcupado(true);
    setAviso(null);
    const resp = await asignarGrupoAPlatos(grupo.id, [...elegidos]);
    setOcupado(false);
    if (resp.ok && resp.config) {
      onGuardado(resp.config);
    } else {
      setAviso("No se pudo guardar. Inténtalo de nuevo.");
    }
  }

  return (
    <div className="asignar-platos">
      {carta.length === 0 ? (
        <p className="ayuda-campo">Cargando la carta…</p>
      ) : (
        [...porCategoria.entries()].map(([catId, platos]) => (
          <div key={catId} className="asignar-categoria">
            <h3>{nombreCategoria.get(catId) ?? catId}</h3>
            {platos.map((p) => (
              <label className="opcion" key={p.id}>
                <input
                  type="checkbox"
                  checked={p.id !== null && elegidos.has(p.id)}
                  onChange={() => p.id && alternar(p.id)}
                />
                {p.nombre}
              </label>
            ))}
          </div>
        ))
      )}
      <button type="button" className="primario" disabled={ocupado} onClick={guardar}>
        Guardar ({elegidos.size} {elegidos.size === 1 ? "plato" : "platos"})
      </button>
      {aviso && <div className="aviso visible error">{aviso}</div>}
    </div>
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
