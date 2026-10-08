import { useState, type FormEvent } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { cambiarClave, cerrarSesion } from "./api";

export function SeccionCuenta() {
  const [claveActual, setClaveActual] = useState("");
  const [claveNueva, setClaveNueva] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  async function enviar(ev: FormEvent) {
    ev.preventDefault();
    setAviso(null);
    setGuardando(true);

    try {
      const resp = await cambiarClave(claveActual, claveNueva);
      if (resp.ok) {
        setAviso({ texto: "Contraseña actualizada.", tipo: "exito" });
        setClaveActual("");
        setClaveNueva("");
      } else if (resp.status === 401) {
        // 401 aqui significa "contraseña actual incorrecta", no sesion
        // caducada: cambiarClave() no redirige sola, a diferencia del resto.
        setAviso({ texto: "La contraseña actual no es correcta.", tipo: "error" });
      } else {
        setAviso({ texto: "No se pudo guardar. Inténtalo de nuevo.", tipo: "error" });
      }
    } catch {
      setAviso({ texto: "No se pudo conectar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="seccion">
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1.5 }}>
            Cambiar contraseña
          </Typography>
          <Box component="form" onSubmit={enviar}>
            <Stack spacing={2} alignItems="flex-start">
              <TextField
                label="Contraseña actual"
                type="password"
                size="small"
                fullWidth
                autoComplete="current-password"
                required
                value={claveActual}
                onChange={(e) => setClaveActual(e.target.value)}
              />
              <TextField
                label="Contraseña nueva"
                type="password"
                size="small"
                fullWidth
                autoComplete="new-password"
                slotProps={{ htmlInput: { minLength: 8 } }}
                required
                value={claveNueva}
                onChange={(e) => setClaveNueva(e.target.value)}
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

      <Card>
        <CardContent>
          <Button variant="outlined" color="error" fullWidth onClick={cerrarSesion}>
            Cerrar sesión
          </Button>
        </CardContent>
      </Card>
    </section>
  );
}
