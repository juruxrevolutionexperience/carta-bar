import { useEffect, useState } from "react";

import { IconCheck, IconGripVertical, IconPencil, IconTrash, IconX } from "@tabler/icons-react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

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
    <Box sx={{ mt: 2 }}>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.5 }}>
        Arrastra el icono para cambiar el orden de las categorías.
      </Typography>
      {destinos !== null && (
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
          «Cocina» o «Barra» dice dónde se preparan sus platos al pedir desde la mesa. Toca para
          cambiarlo; un plato suelto puede llevar otro en su «Para pedir».
        </Typography>
      )}
      {lista.length === 0 && <p className="cargando">Todavía no hay categorías.</p>}

      <Stack spacing={1} sx={{ mb: 2 }}>
        {lista.map((c) => {
          const total = cuantosPlatos(c.id);
          return (
            <Stack
              key={c.id}
              direction="row"
              alignItems="center"
              spacing={1}
              ref={refFila(c.id)}
              sx={{
                p: 1,
                borderRadius: 1.5,
                borderLeft: 4,
                borderLeftColor: colorCategoria(c.id),
                bgcolor: arrastrandoId === c.id ? "action.selected" : "background.default",
              }}
            >
              {editando === c.id ? (
                <>
                  <TextField
                    size="small"
                    value={nombreEditado}
                    slotProps={{ htmlInput: { maxLength: 60 } }}
                    autoFocus
                    aria-label="Nuevo nombre de la categoría"
                    onChange={(e) => setNombreEditado(e.target.value)}
                    sx={{ flex: 1 }}
                  />
                  <IconButton disabled={ocupado} onClick={() => guardarNombre(c.id)}>
                    <IconCheck size={18} />
                  </IconButton>
                  <IconButton onClick={() => setEditando(null)}>
                    <IconX size={18} />
                  </IconButton>
                </>
              ) : (
                <>
                  <Typography sx={{ flex: 1, fontSize: 14, fontWeight: 600 }}>
                    {c.nombre}{" "}
                    <Typography component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>
                      ({total})
                    </Typography>
                  </Typography>
                  {destinos !== null && (
                    <Chip
                      label={(destinos[c.id] ?? "cocina") === "cocina" ? "Cocina" : "Barra"}
                      color={(destinos[c.id] ?? "cocina") === "cocina" ? "primary" : "secondary"}
                      size="small"
                      disabled={ocupado}
                      onClick={() => cambiarDestino(c)}
                      aria-label={`${c.nombre} se prepara en ${destinos[c.id] ?? "cocina"}. Cambiar`}
                    />
                  )}
                  <IconButton
                    aria-label={`Arrastrar ${c.nombre} para cambiar su orden`}
                    disabled={ocupado}
                    {...asa(c.id)}
                  >
                    <IconGripVertical size={18} />
                  </IconButton>
                  <IconButton
                    aria-label={`Renombrar ${c.nombre}`}
                    disabled={ocupado}
                    onClick={() => {
                      setEditando(c.id);
                      setNombreEditado(c.nombre);
                    }}
                  >
                    <IconPencil size={18} />
                  </IconButton>
                  <IconButton
                    aria-label={`Eliminar ${c.nombre}`}
                    title={total > 0 ? "Solo se pueden eliminar categorías vacías" : undefined}
                    disabled={ocupado || total > 0}
                    onClick={() => borrar(c)}
                  >
                    <IconTrash size={18} />
                  </IconButton>
                </>
              )}
            </Stack>
          );
        })}
      </Stack>

      <Box
        component="form"
        onSubmit={(e) => {
          e.preventDefault();
          anadir();
        }}
        sx={{ display: "flex", gap: 1 }}
      >
        <TextField
          size="small"
          value={nuevoNombre}
          slotProps={{ htmlInput: { maxLength: 60 } }}
          placeholder="Nueva categoría…"
          aria-label="Nombre de la nueva categoría"
          onChange={(e) => setNuevoNombre(e.target.value)}
          sx={{ flex: 1 }}
        />
        <Button type="submit" variant="contained" disabled={ocupado || !nuevoNombre.trim()}>
          Añadir
        </Button>
      </Box>

      {aviso && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {aviso}
        </Alert>
      )}
    </Box>
  );
}
