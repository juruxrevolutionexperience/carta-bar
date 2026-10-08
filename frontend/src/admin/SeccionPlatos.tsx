import { useMemo, useState } from "react";

import { IconChevronDown, IconPlus } from "@tabler/icons-react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { colorCategoria } from "../carta/iconos";
import { FilaPlato } from "./FilaPlato";
import { FormularioPlato } from "./FormularioPlato";
import { OrganizarCategorias } from "./OrganizarCategorias";
import { CATEGORIA_ESPECIALES, platoVacio, type Categoria, type Plato } from "./types";

interface Props {
  platos: Plato[] | null;
  error: boolean;
  categorias: Categoria[];
  onActualizar: (anterior: Plato, nuevo: Plato) => void;
  onQuitar: (objetivo: Plato) => void;
  onCreado: (plato: Plato) => void;
  onCambioCategorias: (categorias: Categoria[]) => void;
}

// Sin acentos ni mayusculas: "salmon" tiene que encontrar "Salmón".
function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

export function SeccionPlatos({
  platos,
  error,
  categorias,
  onActualizar, onQuitar,
  onCreado,
  onCambioCategorias,
}: Props) {
  const [busqueda, setBusqueda] = useState("");
  // Categorias que el gerente ha desplegado a mano. Vacio = todo cerrado por
  // defecto (mas comodo con 28 platos que empezar con todo abierto).
  const [abiertas, setAbiertas] = useState<Set<string>>(new Set());
  const [anadiendo, setAnadiendo] = useState(false);
  const [organizando, setOrganizando] = useState(false);
  const buscando = busqueda.trim() !== "";
  const categoriasElegibles = categorias.filter((c) => c.id !== CATEGORIA_ESPECIALES);

  function alternar(id: string, abierta: boolean) {
    setAbiertas((actual) => {
      const siguiente = new Set(actual);
      if (abierta) siguiente.add(id);
      else siguiente.delete(id);
      return siguiente;
    });
  }

  const filtrados = useMemo(() => {
    const termino = normalizar(busqueda.trim());
    if (!termino || !platos) return platos;
    return platos.filter((p) => normalizar(p.nombre).includes(termino));
  }, [platos, busqueda]);

  const grupos = useMemo(() => {
    if (!filtrados) return null;
    const porCategoria = new Map<string, Plato[]>();
    for (const p of filtrados) {
      const lista = porCategoria.get(p.categoria);
      if (lista) lista.push(p);
      else porCategoria.set(p.categoria, [p]);
    }
    // Las categorias conocidas, en su orden; cualquier plato con una
    // categoria que ya no exista en categorias.json no se pierde, aparece
    // al final agrupado bajo su propio id.
    const ordenadas = categorias
      .filter((c) => porCategoria.has(c.id))
      .map((c) => ({ id: c.id, nombre: c.nombre, platos: porCategoria.get(c.id)! }));
    const conocidas = new Set(categorias.map((c) => c.id));
    for (const [id, platosDeCategoria] of porCategoria) {
      if (!conocidas.has(id)) ordenadas.push({ id, nombre: id, platos: platosDeCategoria });
    }
    return ordenadas;
  }, [filtrados, categorias]);

  return (
    <section className="seccion">
      <Card>
        <CardContent>
          <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="h3">Platos</Typography>
            {!error && platos !== null && (
              <Button
                variant="outlined"
                size="small"
                onClick={() => {
                  setOrganizando((o) => !o);
                  setAnadiendo(false);
                }}
              >
                {organizando ? "Hecho" : "Organizar categorías"}
              </Button>
            )}
          </Stack>
          {organizando && (
            <OrganizarCategorias
              categorias={categorias}
              platos={platos}
              onCambio={onCambioCategorias}
            />
          )}
          {!error && platos !== null && categoriasElegibles.length === 0 && !organizando && (
            <p className="cargando">Crea primero una categoría para poder añadir platos.</p>
          )}
          {!error &&
            platos !== null &&
            categoriasElegibles.length > 0 &&
            !anadiendo &&
            !organizando && (
              <Button
                variant="contained"
                startIcon={<IconPlus size={18} />}
                onClick={() => setAnadiendo(true)}
                sx={{ mb: 2 }}
              >
                Añadir plato
              </Button>
            )}
          {anadiendo && (
            <FormularioPlato
              plato={platoVacio()}
              categoriasElegibles={categoriasElegibles}
              onCancelar={() => setAnadiendo(false)}
              onEliminado={() => setAnadiendo(false)}
              onGuardado={(creado) => {
                setAnadiendo(false);
                onCreado(creado);
                // Que el gerente vea donde ha quedado el plato nuevo.
                alternar(creado.categoria, true);
              }}
            />
          )}
          {!error && !organizando && platos !== null && platos.length > 0 && (
            <TextField
              type="search"
              placeholder="Buscar un plato…"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              aria-label="Buscar un plato"
              size="small"
              fullWidth
              sx={{ mb: 2 }}
            />
          )}

          {error && <p className="cargando">No se pudo cargar la carta.</p>}
          {!error && platos === null && <p className="cargando">Cargando…</p>}
          {!error && platos !== null && platos.length === 0 && (
            <p className="cargando">No hay platos.</p>
          )}
          {!error && grupos !== null && grupos.length === 0 && busqueda.trim() && (
            <p className="cargando">Ningún plato coincide con "{busqueda.trim()}".</p>
          )}

          {!organizando &&
            grupos?.map((grupo) => (
              <Accordion
                key={grupo.id}
                // Buscando, se fuerza abierto para que un resultado nunca quede
                // escondido dentro de una categoria cerrada; al borrar la
                // busqueda vuelve a lo que el gerente tenia puesto a mano.
                expanded={buscando || abiertas.has(grupo.id)}
                onChange={(_, abierta) => alternar(grupo.id, abierta)}
                disableGutters
                elevation={0}
                sx={{
                  "&:before": { display: "none" },
                  background: "transparent",
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1.5,
                  mb: 1,
                  "&.Mui-expanded": { mb: 1 },
                }}
              >
                <AccordionSummary
                  expandIcon={<IconChevronDown size={16} />}
                  sx={{
                    borderLeft: 4,
                    borderLeftColor: colorCategoria(grupo.id),
                    borderRadius: 1.5,
                  }}
                >
                  <Typography sx={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.03em" }}>
                    {grupo.nombre.toUpperCase()}
                  </Typography>
                  <Chip label={grupo.platos.length} size="small" sx={{ ml: 1 }} />
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{ pt: 0.5 }}>
                    {grupo.platos.map((p) => (
                      <FilaPlato
                        key={p.id}
                        plato={p}
                        nombreCategoria={grupo.nombre}
                        onCambiado={(nuevo) => onActualizar(p, nuevo)}
                        onQuitarDeLista={() => onQuitar(p)}
                      />
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
        </CardContent>
      </Card>
    </section>
  );
}
