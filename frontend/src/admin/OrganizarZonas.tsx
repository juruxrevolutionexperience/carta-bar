import { useState } from "react";

import { IconCheck, IconGripVertical, IconPencil, IconTrash, IconX } from "@tabler/icons-react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

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
    <Card sx={{ p: 2.5, mb: 2 }}>
      <Typography variant="h3" sx={{ mb: 0.5 }}>
        Zonas del local
      </Typography>
      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
        Arrastra el icono para cambiar el orden de las pestañas. Ej.: Terraza, Barra, Salón 1.
      </Typography>

      <Stack spacing={1} sx={{ mb: 2 }}>
        {lista.map((z) => (
          <Stack
            key={z.id}
            direction="row"
            alignItems="center"
            spacing={1}
            ref={refFila(z.id)}
            sx={{
              p: 1,
              borderRadius: 1.5,
              bgcolor: arrastrandoId === z.id ? "action.selected" : "background.default",
            }}
          >
            {editando === z.id ? (
              <>
                <TextField
                  size="small"
                  value={nombreEditado}
                  slotProps={{ htmlInput: { maxLength: 60 } }}
                  autoFocus
                  aria-label="Nuevo nombre de la zona"
                  onChange={(e) => setNombreEditado(e.target.value)}
                  sx={{ flex: 1 }}
                />
                <IconButton disabled={ocupado} onClick={() => guardarNombre(z.id)}>
                  <IconCheck size={18} />
                </IconButton>
                <IconButton onClick={() => setEditando(null)}>
                  <IconX size={18} />
                </IconButton>
              </>
            ) : (
              <>
                <Typography sx={{ flex: 1, fontSize: 14, fontWeight: 600 }}>
                  {z.nombre}{" "}
                  <Typography component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>
                    ({cuantasMesas(z.id)})
                  </Typography>
                </Typography>
                <IconButton
                  aria-label={`Arrastrar ${z.nombre} para cambiar su orden`}
                  disabled={ocupado}
                  {...asa(z.id)}
                >
                  <IconGripVertical size={18} />
                </IconButton>
                <IconButton
                  aria-label={`Renombrar ${z.nombre}`}
                  disabled={ocupado}
                  onClick={() => {
                    setEditando(z.id);
                    setNombreEditado(z.nombre);
                  }}
                >
                  <IconPencil size={18} />
                </IconButton>
                <IconButton
                  aria-label={`Eliminar ${z.nombre}`}
                  disabled={ocupado}
                  onClick={() => borrar(z)}
                >
                  <IconTrash size={18} />
                </IconButton>
              </>
            )}
          </Stack>
        ))}
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
          placeholder="Nueva zona…"
          aria-label="Nombre de la nueva zona"
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
    </Card>
  );
}
