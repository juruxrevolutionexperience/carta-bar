import { useEffect, useState } from "react";

import { IconPlus } from "@tabler/icons-react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

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
      <Card>
        <CardContent>
          <p>{error ? "No se pudieron cargar los extras." : "Cargando…"}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <section className="seccion">
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1 }}>
            Extras y opciones
          </Typography>
          <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>
            Crea aquí cada grupo una sola vez y márcalo luego en los platos que lo lleven (al
            editar el plato, en «Para pedir»). Obligatorio es lo que el camarero preguntaría
            siempre, como el punto de la carne; opcional, los extras.
          </Typography>
          {editando !== "nuevo" && (
            <Button
              variant="contained"
              startIcon={<IconPlus size={18} />}
              onClick={() => setEditando("nuevo")}
            >
              Nuevo grupo
            </Button>
          )}
        </CardContent>
      </Card>

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
          <Card sx={{ mb: 2 }} key={g.id}>
            <CardContent>
              <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
                <Typography variant="h4">{g.nombre}</Typography>
                <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                  {resumenGrupo(g)}
                </Typography>
              </Stack>
              <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0, mb: 1 }}>
                {g.opciones.map((o) => (
                  <Stack
                    component="li"
                    direction="row"
                    justifyContent="space-between"
                    key={o.nombre}
                    sx={{ py: 0.5, fontSize: 14 }}
                  >
                    <span>{o.nombre}</span>
                    <span>{textoPrecio(o.precio)}</span>
                  </Stack>
                ))}
              </Box>
              <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 1.5 }}>
                {platosCon(g.id) === 0
                  ? "No está en ningún plato todavía."
                  : `En ${platosCon(g.id)} ${platosCon(g.id) === 1 ? "plato" : "platos"}.`}
              </Typography>
              <Stack direction="row" spacing={1}>
                <Button variant="outlined" size="small" onClick={() => setEditando(g.id)}>
                  Editar
                </Button>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => setAsignando(asignando === g.id ? null : g.id)}
                >
                  {asignando === g.id ? "Cerrar" : "Asignar a platos"}
                </Button>
              </Stack>
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
            </CardContent>
          </Card>
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
    <Box sx={{ mt: 2 }}>
      {carta.length === 0 ? (
        <p className="ayuda-campo">Cargando la carta…</p>
      ) : (
        [...porCategoria.entries()].map(([catId, platos]) => (
          <Box key={catId} sx={{ mb: 1.5 }}>
            <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>
              {nombreCategoria.get(catId) ?? catId}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {platos.map((p) => (
                <FormControlLabel
                  key={p.id}
                  sx={{ width: { xs: "100%", sm: "48%" }, mr: 0 }}
                  control={
                    <Checkbox
                      size="small"
                      checked={p.id !== null && elegidos.has(p.id)}
                      onChange={() => p.id && alternar(p.id)}
                    />
                  }
                  label={<Typography sx={{ fontSize: 14 }}>{p.nombre}</Typography>}
                />
              ))}
            </Box>
          </Box>
        ))
      )}
      <Button variant="contained" disabled={ocupado} onClick={guardar}>
        Guardar ({elegidos.size} {elegidos.size === 1 ? "plato" : "platos"})
      </Button>
      {aviso && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {aviso}
        </Alert>
      )}
    </Box>
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
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Stack spacing={2}>
          <TextField
            label="Nombre del grupo"
            size="small"
            fullWidth
            value={nombre}
            slotProps={{ htmlInput: { maxLength: 60 } }}
            placeholder="Extras de hamburguesa"
            onChange={(e) => setNombre(e.target.value)}
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={obligatorio}
                onChange={(e) => setObligatorio(e.target.checked)}
              />
            }
            label={
              <Typography sx={{ fontSize: 14 }}>
                Obligatorio (el cliente tiene que elegir)
              </Typography>
            }
          />

          <TextField
            label="Cuántas se pueden elegir como mucho"
            size="small"
            type="number"
            slotProps={{ htmlInput: { min: 1, max: 30 } }}
            value={maximo}
            onChange={(e) => setMaximo(Math.max(1, Number(e.target.value) || 1))}
          />

          <Box>
            <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.5 }}>
              Opciones (precio vacío = gratis)
            </Typography>
            <FilasPrecio
              filas={filas}
              onCambio={setFilas}
              ejemploNombre="Queso"
              precioOpcional={true}
              maximo={30}
              textoAnadir="Añadir opción"
            />
          </Box>

          {aviso && <Alert severity="error">{aviso}</Alert>}

          <Stack direction="row" spacing={1}>
            <Button variant="contained" disabled={ocupado} onClick={guardar}>
              Guardar
            </Button>
            <Button variant="outlined" onClick={onCancelar}>
              Cancelar
            </Button>
            {grupo && (
              <Button variant="outlined" color="error" disabled={ocupado} onClick={borrar}>
                Eliminar grupo
              </Button>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
