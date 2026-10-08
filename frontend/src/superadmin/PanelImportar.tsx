import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  cargarCategoriasRestaurante,
  crearCategoriaRestaurante,
  crearPlatoRestaurante,
  leerCartaDeFoto,
  type Categoria,
  type PlatoLeido,
} from "./api";

interface Props {
  restauranteId: string;
  onCerrar: () => void;
}

interface FilaEditable {
  incluir: boolean;
  nombre: string;
  descripcion: string;
  ingredientes: string; // editado como texto separado por comas
  precio: string; // editado como texto, se valida al crear
}

function aFila(p: PlatoLeido): FilaEditable {
  return {
    incluir: true,
    nombre: p.nombre,
    descripcion: p.descripcion,
    ingredientes: p.ingredientes.join(", "),
    precio: p.precio == null ? "" : String(p.precio),
  };
}

// Herramienta de uso propio, no del gerente: lee una foto de una carta en
// papel con el modelo (cuesta unos centimos) y propone los platos en una
// tabla editable. No se crea nada hasta pulsar "Crear".
export function PanelImportar({ restauranteId, onCerrar }: Props) {
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [nuevaCategoria, setNuevaCategoria] = useState("");
  const [leyendo, setLeyendo] = useState(false);
  const [filas, setFilas] = useState<FilaEditable[] | null>(null);
  const [creando, setCreando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [creados, setCreados] = useState(0);

  useEffect(() => {
    cargarCategoriasRestaurante(restauranteId)
      .then((cats) => {
        setCategorias(cats);
        if (cats[0]) setCategoriaId(cats[0].id);
      })
      .catch(() => setAviso("No se pudieron cargar las categorías de este restaurante."));
  }, [restauranteId]);

  async function alElegirFoto(e: React.ChangeEvent<HTMLInputElement>) {
    const archivo = e.target.files?.[0];
    e.target.value = "";
    if (!archivo) return;
    setAviso(null);
    setLeyendo(true);
    try {
      const leidos = await leerCartaDeFoto(restauranteId, archivo);
      setFilas(leidos.map(aFila));
    } catch {
      setAviso("No se pudo leer la foto. Prueba con otra o inténtalo de nuevo.");
    } finally {
      setLeyendo(false);
    }
  }

  function cambiarFila(i: number, cambios: Partial<FilaEditable>) {
    setFilas((actual) => actual?.map((f, idx) => (idx === i ? { ...f, ...cambios } : f)) ?? actual);
  }

  async function crearTodos() {
    if (!filas) return;
    setAviso(null);
    setCreando(true);
    setCreados(0);
    try {
      let destino = categoriaId;
      const nombreNueva = nuevaCategoria.trim();
      if (nombreNueva) {
        const creada = await crearCategoriaRestaurante(restauranteId, nombreNueva);
        destino = creada.id;
        setCategorias((c) => [...c, creada]);
        setCategoriaId(creada.id);
        setNuevaCategoria("");
      }
      if (!destino) {
        setAviso("Elige o crea una categoría antes de crear los platos.");
        return;
      }
      const incluidas = filas.filter((f) => f.incluir);
      let hechos = 0;
      for (const f of incluidas) {
        const precio = f.precio.trim() === "" ? null : Number(f.precio.replace(",", "."));
        const resp = await crearPlatoRestaurante(restauranteId, {
          categoria: destino,
          nombre: f.nombre.trim(),
          descripcion: f.descripcion.trim(),
          precio: precio !== null && !Number.isNaN(precio) ? precio : null,
          ingredientes: f.ingredientes
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        });
        if (resp.ok) {
          hechos += 1;
          setCreados(hechos);
        }
      }
      if (hechos === incluidas.length) {
        setFilas(null);
        setAviso(`Creados ${hechos} platos. Se están traduciendo en segundo plano.`);
      } else {
        setAviso(`Creados ${hechos} de ${incluidas.length}. Revisa los que fallaron e inténtalo de nuevo.`);
      }
    } catch {
      setAviso("Algo falló creando los platos. Revisa cuáles se quedaron a medias.");
    } finally {
      setCreando(false);
    }
  }

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h3" sx={{ mb: 0.5 }}>
          Importar platos de una foto — {restauranteId}
        </Typography>
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
          Sube una foto de la carta en papel; el modelo propone los platos y tú los revisas antes
          de crear nada.
        </Typography>

        {!filas && (
          <Button component="label" variant="outlined" disabled={leyendo} sx={{ mb: 2 }}>
            {leyendo ? "Leyendo la foto…" : "Elegir foto"}
            <input
              type="file"
              accept="image/jpeg"
              hidden
              disabled={leyendo}
              onChange={alElegirFoto}
            />
          </Button>
        )}

        {filas && filas.length > 0 && (
          <>
            <TableContainer sx={{ mb: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox"></TableCell>
                    <TableCell>Nombre</TableCell>
                    <TableCell>Descripción</TableCell>
                    <TableCell>Ingredientes</TableCell>
                    <TableCell>Precio</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filas.map((f, i) => (
                    <TableRow key={i}>
                      <TableCell padding="checkbox">
                        <Checkbox
                          size="small"
                          checked={f.incluir}
                          onChange={(e) => cambiarFila(i, { incluir: e.target.checked })}
                          aria-label={`Incluir ${f.nombre || "este plato"}`}
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          variant="standard"
                          value={f.nombre}
                          onChange={(e) => cambiarFila(i, { nombre: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          variant="standard"
                          value={f.descripcion}
                          onChange={(e) => cambiarFila(i, { descripcion: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          variant="standard"
                          value={f.ingredientes}
                          onChange={(e) => cambiarFila(i, { ingredientes: e.target.value })}
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          variant="standard"
                          value={f.precio}
                          slotProps={{ htmlInput: { inputMode: "decimal" } }}
                          sx={{ width: 70 }}
                          onChange={(e) => cambiarFila(i, { precio: e.target.value })}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Stack spacing={2} alignItems="flex-start" sx={{ mb: 2 }}>
              <FormControl size="small" fullWidth>
                <InputLabel id="categoria-destino">Categoría de destino</InputLabel>
                <Select
                  labelId="categoria-destino"
                  label="Categoría de destino"
                  value={categoriaId}
                  onChange={(e) => setCategoriaId(e.target.value)}
                >
                  {categorias.length === 0 && (
                    <MenuItem value="">— sin categorías todavía —</MenuItem>
                  )}
                  {categorias.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.nombre}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label="O crea una categoría nueva"
                size="small"
                fullWidth
                value={nuevaCategoria}
                placeholder="p. ej. Tostas"
                onChange={(e) => setNuevaCategoria(e.target.value)}
              />

              <Stack direction="row" spacing={1}>
                <Button variant="contained" disabled={creando} onClick={crearTodos}>
                  {creando
                    ? `Creando… (${creados}/${filas.filter((f) => f.incluir).length})`
                    : `Crear ${filas.filter((f) => f.incluir).length} platos`}
                </Button>
                <Button variant="outlined" disabled={creando} onClick={() => setFilas(null)}>
                  Empezar de nuevo
                </Button>
              </Stack>
            </Stack>
          </>
        )}

        {filas && filas.length === 0 && (
          <p className="cargando">No se reconoció ningún plato en la foto.</p>
        )}

        {aviso && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {aviso}
          </Alert>
        )}

        <Box>
          <Button variant="outlined" onClick={onCerrar}>
            Cerrar
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
