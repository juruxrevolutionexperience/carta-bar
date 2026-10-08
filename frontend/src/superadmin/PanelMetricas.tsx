import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableFooter from "@mui/material/TableFooter";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

import { cargarMetricas, type MetricasBar } from "./api";

function Estadistica({ valor, etiqueta }: { valor: string; etiqueta: string }) {
  return (
    <Card sx={{ flex: "1 1 140px" }}>
      <CardContent>
        <Typography sx={{ fontSize: 22, fontWeight: 700 }}>{valor}</Typography>
        <Typography sx={{ fontSize: 12.5, color: "text.secondary" }}>{etiqueta}</Typography>
      </CardContent>
    </Card>
  );
}

const PERIODOS = [7, 30] as const;

const entero = (n: number) => n.toLocaleString("es-ES");
const dolares = (n: number, decimales: number) =>
  `${n.toLocaleString("es-ES", { minimumFractionDigits: decimales, maximumFractionDigits: decimales })} $`;

function idiomas(porIdioma: Record<string, number>): string {
  const partes = Object.entries(porIdioma)
    .sort((a, b) => b[1] - a[1])
    .map(([idioma, n]) => `${idioma.toUpperCase()} ${n}`);
  return partes.length ? partes.join(" · ") : "—";
}

export function PanelMetricas() {
  const [dias, setDias] = useState<number>(7);
  const [filas, setFilas] = useState<MetricasBar[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setFilas(null);
    setError(false);
    cargarMetricas(dias)
      .then(setFilas)
      .catch(() => setError(true));
  }, [dias]);

  const total = (campo: "visitas" | "preguntas" | "conversaciones" | "rechazadas") =>
    (filas ?? []).reduce((suma, f) => suma + f[campo], 0);
  const costeChat = (filas ?? []).reduce((suma, f) => suma + f.coste_chat_usd, 0);
  const costeTraducciones = (filas ?? []).reduce((suma, f) => suma + f.coste_traducciones_usd, 0);

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
          <Typography variant="h3">Métricas</Typography>
          <Stack direction="row" spacing={1}>
            {PERIODOS.map((p) => (
              <Button
                key={p}
                size="small"
                variant={dias === p ? "contained" : "outlined"}
                aria-pressed={dias === p}
                onClick={() => setDias(p)}
              >
                {p} días
              </Button>
            ))}
          </Stack>
        </Stack>

        {error && <p className="cargando">No se pudieron cargar las métricas.</p>}
        {!error && filas === null && <p className="cargando">Cargando…</p>}

        {!error && filas !== null && (
          <>
            <Stack direction="row" flexWrap="wrap" gap={1.5} sx={{ mb: 2 }}>
              <Estadistica valor={entero(total("visitas"))} etiqueta="visitas" />
              <Estadistica valor={entero(total("preguntas"))} etiqueta="preguntas" />
              <Estadistica valor={entero(total("conversaciones"))} etiqueta="conversaciones" />
              <Estadistica valor={dolares(costeChat, 2)} etiqueta="coste del chat" />
            </Stack>

            <TableContainer sx={{ mb: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Bar</TableCell>
                    <TableCell>Visitas</TableCell>
                    <TableCell>Preguntas</TableCell>
                    <TableCell>Conv.</TableCell>
                    <TableCell>Idiomas</TableCell>
                    <TableCell>Sin cupo</TableCell>
                    <TableCell>Chat</TableCell>
                    <TableCell>Traduc.</TableCell>
                    <TableCell>Por pregunta</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filas.map((f) => (
                    <TableRow key={f.restaurante_id}>
                      <TableCell>{f.nombre}</TableCell>
                      <TableCell>{entero(f.visitas)}</TableCell>
                      <TableCell>{entero(f.preguntas)}</TableCell>
                      <TableCell>{entero(f.conversaciones)}</TableCell>
                      <TableCell>{idiomas(f.preguntas_por_idioma)}</TableCell>
                      <TableCell sx={{ color: f.rechazadas > 0 ? "error.main" : undefined }}>
                        {entero(f.rechazadas)}
                      </TableCell>
                      <TableCell>{dolares(f.coste_chat_usd, 3)}</TableCell>
                      <TableCell>{dolares(f.coste_traducciones_usd, 3)}</TableCell>
                      <TableCell>
                        {f.coste_por_pregunta_usd === null
                          ? "—"
                          : dolares(f.coste_por_pregunta_usd, 4)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
                {filas.length > 1 && (
                  <TableFooter>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Total</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>{entero(total("visitas"))}</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>{entero(total("preguntas"))}</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>
                        {entero(total("conversaciones"))}
                      </TableCell>
                      <TableCell></TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>{entero(total("rechazadas"))}</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>{dolares(costeChat, 3)}</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>
                        {dolares(costeTraducciones, 3)}
                      </TableCell>
                      <TableCell></TableCell>
                    </TableRow>
                  </TableFooter>
                )}
              </Table>
            </TableContainer>

            <Box
              component="p"
              sx={{ fontSize: 12, color: "text.secondary", m: 0 }}
            >
              Visitas: cargas de la carta sin robots ni el gerente con sesión abierta (una
              persona que recarga cuenta dos veces). Conversación: pregunta que llega sin
              historial, aproximada. Sin cupo: preguntas cortadas por el tope diario de gasto.
              Días en hora de España.
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}
