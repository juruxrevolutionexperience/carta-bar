import { useEffect, useState } from "react";

import { IconX } from "@tabler/icons-react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { cargarCarta, cargarCategorias } from "./api";
import { cargarGruposDePlato, type GrupoOpciones, type NuevaLineaComanda } from "./api";
import { CATEGORIA_ESPECIALES, type Categoria, type Plato } from "./types";

interface Props {
  onElegir: (datos: NuevaLineaComanda) => Promise<boolean>;
  onCerrar: () => void;
}

// Parrilla estilo TPV para que el camarero anada algo en nombre de la mesa:
// pestanas de categoria arriba, botones grandes por plato debajo. Un plato
// sin formato ni extras obligatorios se anade con un solo toque; si necesita
// elegir algo, se abre un paso mas antes (ChoosePlato).
export function SelectorTPV({ onElegir, onCerrar }: Props) {
  const [carta, setCarta] = useState<Plato[] | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [categoriaId, setCategoriaId] = useState<string | null>(null);
  const [eligiendo, setEligiendo] = useState<Plato | null>(null);

  useEffect(() => {
    Promise.all([cargarCarta(), cargarCategorias()]).then(([platos, cats]) => {
      const ordenadas = [...cats]
        .filter((c) => c.id !== CATEGORIA_ESPECIALES)
        .sort((a, b) => a.orden - b.orden);
      setCarta(platos);
      setCategorias(ordenadas);
      setCategoriaId(ordenadas[0]?.id ?? null);
    });
  }, []);

  const disponibles = (carta ?? []).filter((p) => p.disponible && p.id);
  const visibles = disponibles.filter((p) => p.categoria === categoriaId);

  async function tocar(plato: Plato) {
    if ((plato.formatos?.length ?? 0) > 0) {
      setEligiendo(plato);
      return;
    }
    const grupos = await cargarGruposDePlato(plato.id as string);
    if (grupos.some((g) => g.minimo > 0)) {
      setEligiendo(plato);
      return;
    }
    await onElegir({ plato_id: plato.id as string, cantidad: 1 });
  }

  return (
    <Dialog open onClose={onCerrar} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        Añadir a la mesa
        <IconButton size="small" aria-label="Cerrar" onClick={onCerrar}>
          <IconX size={18} />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Tabs
          value={categoriaId ?? false}
          onChange={(_, nuevo) => setCategoriaId(nuevo)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ mb: 2, minHeight: 36, "& .MuiTab-root": { minHeight: 36 } }}
        >
          {categorias.map((c) => (
            <Tab key={c.id} value={c.id} label={c.nombre} />
          ))}
        </Tabs>

        {carta === null ? (
          <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Cargando la carta…</Typography>
        ) : (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
              gap: 1.5,
            }}
          >
            {visibles.map((p) => (
              <ButtonBase
                key={p.id}
                onClick={() => void tocar(p)}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 0.5,
                  minHeight: 88,
                  p: 1.5,
                  borderRadius: 2,
                  border: 1,
                  borderColor: "divider",
                  bgcolor: "background.default",
                  textAlign: "center",
                }}
              >
                <Typography sx={{ fontSize: 13.5, fontWeight: 600 }}>{p.nombre}</Typography>
                <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                  {(p.formatos?.length ?? 0) > 0
                    ? "Varios precios"
                    : p.precio != null
                      ? `${p.precio.toFixed(2).replace(".", ",")} €`
                      : "—"}
                </Typography>
              </ButtonBase>
            ))}
            {visibles.length === 0 && (
              <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
                Sin platos en esta categoría.
              </Typography>
            )}
          </Box>
        )}
      </DialogContent>

      {eligiendo && (
        <ElegirDetallePlato
          plato={eligiendo}
          onCancelar={() => setEligiendo(null)}
          onConfirmar={async (datos) => {
            const ok = await onElegir(datos);
            if (ok) setEligiendo(null);
          }}
        />
      )}
    </Dialog>
  );
}

interface PropsDetalle {
  plato: Plato;
  onCancelar: () => void;
  onConfirmar: (datos: NuevaLineaComanda) => Promise<void>;
}

// El mismo paso que ya hace el cliente al pedir desde la carta
// (FormularioPropuesta.tsx), aqui para cuando el camarero anade un plato con
// extras obligatorios (ej. "Punto de la carne").
function ElegirDetallePlato({ plato, onCancelar, onConfirmar }: PropsDetalle) {
  const [grupos, setGrupos] = useState<GrupoOpciones[]>([]);
  const [elegidas, setElegidas] = useState<string[]>([]);
  const [formato, setFormato] = useState<string | null>(plato.formatos?.[0]?.nombre ?? null);
  const [cantidad, setCantidad] = useState(1);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    cargarGruposDePlato(plato.id as string).then(setGrupos);
  }, [plato.id]);

  function alternar(grupo: GrupoOpciones, nombre: string) {
    setElegidas((actual) => {
      const enEsteGrupo = (n: string) => grupo.opciones.some((o) => o.nombre === n);
      if (grupo.maximo === 1) {
        const sinGrupo = actual.filter((n) => !enEsteGrupo(n));
        return actual.includes(nombre) ? sinGrupo : [...sinGrupo, nombre];
      }
      if (actual.includes(nombre)) return actual.filter((n) => n !== nombre);
      if (actual.filter(enEsteGrupo).length >= grupo.maximo) return actual;
      return [...actual, nombre];
    });
  }

  async function confirmar() {
    for (const g of grupos) {
      const elegidasDelGrupo = elegidas.filter((n) => g.opciones.some((o) => o.nombre === n));
      if (elegidasDelGrupo.length < g.minimo) {
        setError(`Elige "${g.nombre}" antes de añadir.`);
        return;
      }
    }
    setEnviando(true);
    setError(null);
    await onConfirmar({ plato_id: plato.id as string, formato, opciones: elegidas, cantidad });
    setEnviando(false);
  }

  return (
    <Dialog open onClose={onCancelar} maxWidth="xs" fullWidth>
      <DialogTitle>{plato.nombre}</DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          {(plato.formatos?.length ?? 0) > 0 && (
            <Box>
              <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>Formato</Typography>
              <RadioGroup value={formato} onChange={(e) => setFormato(e.target.value)}>
                {plato.formatos!.map((f) => (
                  <FormControlLabel
                    key={f.nombre}
                    value={f.nombre}
                    control={<Radio size="small" />}
                    label={`${f.nombre} (${f.precio.toFixed(2).replace(".", ",")} €)`}
                  />
                ))}
              </RadioGroup>
            </Box>
          )}
          {grupos.map((g) => (
            <Box key={g.id}>
              <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>
                {g.nombre}
                {g.minimo > 0 && " (obligatorio)"}
              </Typography>
              <Stack>
                {g.opciones.map((o) =>
                  g.maximo === 1 ? (
                    <FormControlLabel
                      key={o.nombre}
                      control={
                        <Radio
                          size="small"
                          checked={elegidas.includes(o.nombre)}
                          onChange={() => alternar(g, o.nombre)}
                        />
                      }
                      label={
                        o.nombre + (o.precio > 0 ? ` (+${o.precio.toFixed(2).replace(".", ",")} €)` : "")
                      }
                    />
                  ) : (
                    <FormControlLabel
                      key={o.nombre}
                      control={
                        <Checkbox
                          size="small"
                          checked={elegidas.includes(o.nombre)}
                          onChange={() => alternar(g, o.nombre)}
                        />
                      }
                      label={
                        o.nombre + (o.precio > 0 ? ` (+${o.precio.toFixed(2).replace(".", ",")} €)` : "")
                      }
                    />
                  )
                )}
              </Stack>
            </Box>
          ))}
          <TextField
            label="Cantidad"
            type="number"
            size="small"
            slotProps={{ htmlInput: { min: 1, max: 20 } }}
            value={cantidad}
            onChange={(e) => setCantidad(Math.max(1, Number(e.target.value) || 1))}
          />
          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancelar}>Cancelar</Button>
        <Button variant="contained" disabled={enviando} onClick={() => void confirmar()}>
          Añadir
        </Button>
      </DialogActions>
    </Dialog>
  );
}
