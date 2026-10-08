import { useEffect, useState, type FormEvent } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { cargarQr, guardarTextoQr } from "./api";
import { HojaQR, type DatosQr } from "../shared/HojaQR";

export function SeccionQr() {
  const [datos, setDatos] = useState<DatosQr | null>(null);
  const [error, setError] = useState(false);
  const [texto, setTexto] = useState("");
  const [compacta, setCompacta] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  useEffect(() => {
    cargarQr()
      .then((cargados) => {
        setDatos(cargados);
        setTexto(cargados.texto);
      })
      .catch(() => setError(true));
  }, []);

  // Guardar un texto vacio es "volver al de por defecto": el servidor decide
  // cual es, asi que se vuelve a pedir en vez de repetirlo aqui.
  async function guardar(nuevo: string) {
    setAviso(null);
    setGuardando(true);
    try {
      const resp = await guardarTextoQr(nuevo);
      if (resp.status !== 204) throw new Error("fallo al guardar");
      const actualizados = await cargarQr();
      setDatos(actualizados);
      setTexto(actualizados.texto);
      setAviso({ texto: "Texto guardado.", tipo: "exito" });
    } catch {
      setAviso({ texto: "No se pudo guardar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  function enviar(ev: FormEvent) {
    ev.preventDefault();
    void guardar(texto);
  }

  if (error) return <section className="seccion">No se pudo cargar el QR.</section>;
  if (!datos) return <section className="seccion">Cargando…</section>;

  return (
    <section className="seccion">
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1 }}>
            Código QR de tu carta
          </Typography>
          <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>
            Escanéalo con tu móvil para probar la carta, o imprime la hoja y ponla en las mesas.
          </Typography>
          <RadioGroup
            value={compacta ? "compacta" : "completa"}
            onChange={(e) => setCompacta(e.target.value === "compacta")}
            sx={{ mb: 2 }}
          >
            <FormControlLabel
              value="completa"
              control={<Radio size="small" />}
              label="Hoja completa (nombre + QR + enlace)"
            />
            <FormControlLabel
              value="compacta"
              control={<Radio size="small" />}
              label="Tarjeta pequeña (para soporte de mesa)"
            />
          </RadioGroup>
          <HojaQR
            url={datos.url}
            nombre={datos.nombre}
            texto={texto.trim() || datos.texto}
            compacta={compacta}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1.5 }}>
            Texto de la hoja
          </Typography>
          <Box component="form" onSubmit={enviar}>
            <Stack spacing={2} alignItems="flex-start">
              <TextField
                label="Lo que se lee bajo el QR"
                size="small"
                fullWidth
                slotProps={{ htmlInput: { maxLength: 120 } }}
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
              />
              <Stack direction="row" spacing={1}>
                <Button type="submit" variant="contained" disabled={guardando}>
                  Guardar
                </Button>
                <Button
                  variant="outlined"
                  disabled={guardando}
                  onClick={() => void guardar("")}
                >
                  Volver al texto original
                </Button>
              </Stack>
              {aviso && (
                <Alert severity={aviso.tipo === "exito" ? "success" : "error"} sx={{ width: "100%" }}>
                  {aviso.texto}
                </Alert>
              )}
            </Stack>
          </Box>
        </CardContent>
      </Card>
    </section>
  );
}
