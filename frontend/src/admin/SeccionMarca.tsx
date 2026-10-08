import { useEffect, useRef, useState, type FormEvent } from "react";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { cambiarNombre, cargarMarca, quitarImagenMarca, subirImagenMarca } from "./api";
import { comprimirImagen } from "./comprimirImagen";
import type { ConfigMarca, TipoImagenMarca } from "./types";

interface BloqueProps {
  tipo: TipoImagenMarca;
  titulo: string;
  ayuda: string;
  url: string;
  claseMiniatura: string;
  anchoMax: number;
  onCambio: (url: string) => void;
}

function BloqueImagen({ tipo, titulo, ayuda, url, claseMiniatura, anchoMax, onCambio }: BloqueProps) {
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function subir() {
    const archivo = inputRef.current?.files?.[0];
    if (!archivo) return;
    setError(null);
    setOcupado(true);
    try {
      const blob = await comprimirImagen(archivo, anchoMax);
      const resp = await subirImagenMarca(tipo, blob);
      if (!resp.ok) throw new Error("fallo al subir");
      const datos = await resp.json();
      onCambio(datos.url);
    } catch {
      setError("No se pudo subir la imagen.");
    } finally {
      setOcupado(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function quitar() {
    setError(null);
    setOcupado(true);
    try {
      const resp = await quitarImagenMarca(tipo);
      if (resp.status !== 204) throw new Error("fallo al quitar");
      onCambio("");
    } catch {
      setError("No se pudo quitar la imagen.");
    } finally {
      setOcupado(false);
    }
  }

  const esRedonda = claseMiniatura === "redonda";

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h3" sx={{ mb: 1 }}>
          {titulo}
        </Typography>
        <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>{ayuda}</Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          {esRedonda ? (
            <Avatar src={url || undefined} sx={{ width: 72, height: 72 }}>
              {!url && "Sin"}
            </Avatar>
          ) : (
            <Box
              sx={{
                width: 160,
                height: 72,
                borderRadius: 1.5,
                overflow: "hidden",
                bgcolor: "action.hover",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {url ? (
                <Box
                  component="img"
                  src={url}
                  alt=""
                  sx={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : (
                <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                  Sin imagen
                </Typography>
              )}
            </Box>
          )}
          <Stack spacing={1}>
            <Stack direction="row" spacing={1}>
              <Button component="label" variant="outlined" disabled={ocupado}>
                {ocupado ? "Subiendo…" : url ? "Cambiar" : "Subir"}
                <input
                  ref={inputRef}
                  type="file"
                  accept="image/*"
                  disabled={ocupado}
                  onChange={subir}
                  style={{
                    position: "absolute",
                    width: 1,
                    height: 1,
                    opacity: 0,
                    overflow: "hidden",
                  }}
                />
              </Button>
              {url && (
                <Button variant="outlined" color="error" onClick={quitar} disabled={ocupado}>
                  Quitar
                </Button>
              )}
            </Stack>
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

export function SeccionMarca() {
  const [marca, setMarca] = useState<ConfigMarca | null>(null);
  const [error, setError] = useState(false);
  const [nombre, setNombre] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  useEffect(() => {
    cargarMarca()
      .then((datos) => {
        setMarca(datos);
        setNombre(datos.nombre ?? "");
      })
      .catch(() => setError(true));
  }, []);

  async function guardarNombre(ev: FormEvent) {
    ev.preventDefault();
    setAviso(null);
    setGuardando(true);
    try {
      const resp = await cambiarNombre(nombre);
      if (resp.status === 204) {
        setAviso({ texto: "Nombre guardado.", tipo: "exito" });
      } else if (resp.status === 422) {
        setAviso({ texto: "El nombre debe tener entre 1 y 80 caracteres.", tipo: "error" });
      } else {
        setAviso({ texto: "No se pudo guardar. Inténtalo de nuevo.", tipo: "error" });
      }
    } catch {
      setAviso({ texto: "No se pudo conectar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  if (error) return <section className="seccion">No se pudo cargar la marca.</section>;
  if (!marca) return <section className="seccion">Cargando…</section>;

  return (
    <section className="seccion">
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1.5 }}>
            Nombre del negocio
          </Typography>
          <Box component="form" onSubmit={guardarNombre}>
            <Stack spacing={2} alignItems="flex-start">
              <TextField
                label="Nombre"
                size="small"
                fullWidth
                required
                slotProps={{ htmlInput: { maxLength: 80 } }}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
              />
              <Button type="submit" variant="contained" disabled={guardando}>
                Guardar
              </Button>
              {aviso && (
                <Alert severity={aviso.tipo === "exito" ? "success" : "error"} sx={{ width: "100%" }}>
                  {aviso.texto}
                </Alert>
              )}
            </Stack>
          </Box>
        </CardContent>
      </Card>

      <BloqueImagen
        tipo="logo"
        titulo="Logo"
        ayuda="Se ve en un círculo sobre la portada de la carta."
        url={marca.logo ?? ""}
        claseMiniatura="redonda"
        anchoMax={512}
        onCambio={(url) => setMarca((actual) => ({ ...actual, logo: url }))}
      />
      <BloqueImagen
        tipo="portada"
        titulo="Foto de portada"
        ayuda="La imagen grande de la parte de arriba de la carta."
        url={marca.foto_portada ?? ""}
        claseMiniatura="ancha"
        anchoMax={1600}
        onCambio={(url) => setMarca((actual) => ({ ...actual, foto_portada: url }))}
      />
    </section>
  );
}
