import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

import type { ResumenRestaurante } from "./api";

interface Props {
  restaurantes: ResumenRestaurante[] | null;
  error: boolean;
  seleccionado: string | null;
  onVerQr: (id: string) => void;
  onImportar: (id: string) => void;
}

export function ListaRestaurantes({
  restaurantes,
  error,
  seleccionado,
  onVerQr,
  onImportar,
}: Props) {
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h3" sx={{ mb: 1.5 }}>
          Restaurantes
        </Typography>
        {error && <p className="cargando">No se pudo cargar la lista.</p>}
        {!error && restaurantes === null && <p className="cargando">Cargando…</p>}
        {!error && restaurantes !== null && restaurantes.length === 0 && (
          <p className="cargando">No hay restaurantes todavía.</p>
        )}
        {!error && restaurantes !== null && restaurantes.length > 0 && (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Subdominio</TableCell>
                  <TableCell>Nombre</TableCell>
                  <TableCell>Platos</TableCell>
                  <TableCell>QR</TableCell>
                  <TableCell>Importar</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {restaurantes.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>{r.id}</TableCell>
                    <TableCell>{r.nombre}</TableCell>
                    <TableCell>{r.num_platos}</TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        variant={seleccionado === r.id ? "contained" : "outlined"}
                        aria-pressed={seleccionado === r.id}
                        onClick={() => onVerQr(r.id)}
                      >
                        Ver QR
                      </Button>
                    </TableCell>
                    <TableCell>
                      <Button size="small" variant="outlined" onClick={() => onImportar(r.id)}>
                        Importar
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}
