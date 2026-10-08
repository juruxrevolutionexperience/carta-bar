import { useState, type FormEvent } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { crearRestaurante, type ResumenRestaurante } from "./api";

interface Props {
  onCreado: (restaurante: ResumenRestaurante) => void;
}

export function FormularioNuevoRestaurante({ onCreado }: Props) {
  const [restauranteId, setRestauranteId] = useState("");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  async function enviar(ev: FormEvent) {
    ev.preventDefault();
    setAviso(null);
    setGuardando(true);

    try {
      const resp = await crearRestaurante({ restaurante_id: restauranteId, nombre, clave });
      if (resp.status === 201) {
        const creado: ResumenRestaurante = await resp.json();
        onCreado(creado);
        setAviso({ texto: `Restaurante "${creado.nombre}" creado.`, tipo: "exito" });
        setRestauranteId("");
        setNombre("");
        setClave("");
        return;
      }
      if (resp.status === 409) {
        setAviso({ texto: "Ese subdominio ya está en uso.", tipo: "error" });
        return;
      }
      setAviso({
        texto: "Revisa los datos: el subdominio solo admite minúsculas, números y guiones.",
        tipo: "error",
      });
    } catch {
      setAviso({ texto: "No se pudo conectar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h3" sx={{ mb: 0.5 }}>
          Añadir restaurante
        </Typography>
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
          Crea el acceso (subdominio y contraseña). Su carta hay que cargarla aparte.
        </Typography>
        <Box component="form" onSubmit={enviar}>
          <Stack spacing={2} alignItems="flex-start">
            <TextField
              label="Subdominio"
              size="small"
              fullWidth
              placeholder="bar2"
              slotProps={{
                htmlInput: { pattern: "[a-z0-9-]+", title: "Solo minúsculas, números y guiones" },
              }}
              required
              value={restauranteId}
              onChange={(e) => setRestauranteId(e.target.value)}
            />
            <TextField
              label="Nombre"
              size="small"
              fullWidth
              placeholder="Bar Pepe"
              required
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
            />
            <TextField
              label="Contraseña inicial"
              type="password"
              size="small"
              fullWidth
              autoComplete="new-password"
              slotProps={{ htmlInput: { minLength: 8 } }}
              required
              value={clave}
              onChange={(e) => setClave(e.target.value)}
            />
            <Button type="submit" variant="contained" disabled={guardando}>
              Crear restaurante
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
  );
}
