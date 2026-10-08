import { useState } from "react";

import { IconChevronDown, IconX } from "@tabler/icons-react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import type { DatosQr } from "../shared/HojaQR";
import type { CambiosMesa, Mesa, Zona } from "./api";
import { TIPOS, girar, tipoDe } from "./planoUtil";
import { QrMesa } from "./QrMesa";

interface Props {
  mesa: Mesa;
  zonas: Zona[];
  qr: DatosQr;
  // Modo lápiz: se puede cambiar todo. En modo ojo solo se ve el estado y el QR.
  editando: boolean;
  // En el móvil el panel es una hoja que tapa el plano: solo se ve si se abrió.
  abiertoEnMovil: boolean;
  ocupado: boolean;
  onCambio: (cambios: CambiosMesa) => void;
  onEliminar: () => void;
  onCerrar: () => void;
  onRegenerar: (mesa: Mesa) => void;
}

// Datos de la mesa seleccionada en el plano. Se monta con key={mesa.id}: al
// tocar otra mesa el formulario arranca limpio.
export function PanelMesa({
  mesa,
  zonas,
  qr,
  editando,
  abiertoEnMovil,
  ocupado,
  onCambio,
  onEliminar,
  onCerrar,
  onRegenerar,
}: Props) {
  const [nombre, setNombre] = useState(mesa.nombre);

  function guardarNombre() {
    const limpio = nombre.trim();
    if (!limpio) {
      setNombre(mesa.nombre);
      return;
    }
    if (limpio !== mesa.nombre) onCambio({ nombre: limpio });
  }

  // El tipo lleva forma, tamaño y aforo juntos: no se retocan por separado.
  const tipo = tipoDe(mesa);

  function cambiarTipo(id: string) {
    const nuevo = TIPOS.find((t) => t.id === id);
    if (!nuevo) return;
    onCambio({
      forma: nuevo.forma,
      ancho: nuevo.ancho,
      alto: nuevo.alto,
      capacidad: nuevo.capacidad,
    });
  }

  return (
    <Card className={"panel-mesa" + (abiertoEnMovil ? "" : " oculto-movil")} sx={{ p: 2.5 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="h3">{mesa.nombre}</Typography>
        <IconButton size="small" aria-label="Cerrar" onClick={onCerrar}>
          <IconX size={18} />
        </IconButton>
      </Stack>

      <Chip
        label={`${mesa.ocupada ? "Con clientes" : "Libre"} · ${mesa.capacidad} ${mesa.capacidad === 1 ? "persona" : "personas"}`}
        color={mesa.ocupada ? "primary" : "default"}
        size="small"
        sx={{ mb: 2 }}
      />

      {editando && (
        <Stack spacing={2} sx={{ mb: 2 }}>
          <TextField
            label="Nombre"
            size="small"
            fullWidth
            value={nombre}
            slotProps={{ htmlInput: { maxLength: 60 } }}
            onChange={(e) => setNombre(e.target.value)}
            onBlur={guardarNombre}
            onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          />

          <FormControl size="small" fullWidth>
            <InputLabel id="mesa-tipo">Tipo de mesa</InputLabel>
            <Select
              labelId="mesa-tipo"
              label="Tipo de mesa"
              value={tipo?.id ?? ""}
              disabled={ocupado}
              onChange={(e) => cambiarTipo(e.target.value)}
            >
              {/* Mesas hechas antes de los tipos: se ven, pero al cambiar pasan a uno. */}
              {!tipo && (
                <MenuItem value="" disabled>
                  Otra ({mesa.capacidad} {mesa.capacidad === 1 ? "persona" : "personas"})
                </MenuItem>
              )}
              {TIPOS.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.etiqueta}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {zonas.length > 1 && (
            <FormControl size="small" fullWidth>
              <InputLabel id="mesa-zona">Zona</InputLabel>
              <Select
                labelId="mesa-zona"
                label="Zona"
                value={mesa.zona_id ?? ""}
                onChange={(e) => onCambio({ zona_id: e.target.value })}
              >
                {zonas.map((z) => (
                  <MenuItem key={z.id} value={z.id}>
                    {z.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              fullWidth
              disabled={ocupado}
              onClick={() => onCambio({ rotacion: girar(mesa.rotacion, -45) })}
            >
              ↺ Girar
            </Button>
            <Button
              variant="outlined"
              fullWidth
              disabled={ocupado}
              onClick={() => onCambio({ rotacion: girar(mesa.rotacion, 45) })}
            >
              Girar ↻
            </Button>
          </Stack>
        </Stack>
      )}

      <Accordion disableGutters elevation={0} sx={{ border: 1, borderColor: "divider", mb: 2, "&:before": { display: "none" } }}>
        <AccordionSummary expandIcon={<IconChevronDown size={16} />}>
          <Typography sx={{ fontSize: 14 }}>QR de esta mesa</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <QrMesa mesa={mesa} qr={qr} compacta={true} ocupado={ocupado} onRegenerar={onRegenerar} />
        </AccordionDetails>
      </Accordion>

      {editando && (
        <Button variant="outlined" color="error" fullWidth disabled={ocupado} onClick={onEliminar}>
          Eliminar mesa
        </Button>
      )}
    </Card>
  );
}
