import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import type { Destino, GrupoOpciones } from "./api";
import { FilasPrecio, type FilaPrecio } from "./FilasPrecio";
import { resumenGrupo } from "./textosProductos";

// Lo de "Para pedir" de un plato mientras se edita: los formatos van como
// texto (ver FilasPrecio) y se convierten al guardar el plato.
export interface PedidoEditable {
  destino: Destino | null;
  alcohol: boolean;
  formatos: FilaPrecio[];
  grupos: string[];
}

interface Props {
  valor: PedidoEditable;
  onCambio: (valor: PedidoEditable) => void;
  grupos: GrupoOpciones[];
  destinoCategoria: Destino;
}

const TEXTO_DESTINO: Record<Destino, string> = { cocina: "Cocina", barra: "Barra" };

export function BloquePedido({ valor, onCambio, grupos, destinoCategoria }: Props) {
  function alternarGrupo(id: string) {
    onCambio({
      ...valor,
      grupos: valor.grupos.includes(id)
        ? valor.grupos.filter((g) => g !== id)
        : [...valor.grupos, id],
    });
  }

  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 2 }}>
      <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 2 }}>Para pedir desde la mesa</Typography>

      <Stack spacing={2}>
        <FormControl size="small" fullWidth>
          <InputLabel id="pedido-destino">Dónde se prepara</InputLabel>
          <Select
            labelId="pedido-destino"
            label="Dónde se prepara"
            value={valor.destino ?? ""}
            onChange={(e) =>
              onCambio({
                ...valor,
                destino: e.target.value === "" ? null : (e.target.value as Destino),
              })
            }
          >
            <MenuItem value="">Como su categoría ({TEXTO_DESTINO[destinoCategoria]})</MenuItem>
            <MenuItem value="cocina">Cocina</MenuItem>
            <MenuItem value="barra">Barra</MenuItem>
          </Select>
        </FormControl>

        <FormControlLabel
          control={
            <Checkbox
              checked={valor.alcohol}
              onChange={(e) => onCambio({ ...valor, alcohol: e.target.checked })}
            />
          }
          label={<Typography sx={{ fontSize: 14 }}>Lleva alcohol</Typography>}
        />

        <Box>
          <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>
            Formatos (tapa, media, ración, caña, jarra…)
          </Typography>
          <Typography sx={{ fontSize: 12.5, color: "text.secondary", mb: 1 }}>
            Sin formatos se pide a su precio de siempre. Con formatos, la carta los enseña con su
            precio y el cliente elige uno. No se traducen: se piden por su nombre.
          </Typography>
          <FilasPrecio
            filas={valor.formatos}
            onCambio={(formatos) => onCambio({ ...valor, formatos })}
            ejemploNombre="Ración"
            maximo={10}
            textoAnadir="Añadir formato"
          />
        </Box>

        <Box>
          <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>Extras y opciones</Typography>
          {grupos.length === 0 ? (
            <Typography sx={{ fontSize: 12.5, color: "text.secondary" }}>
              Aún no hay grupos. Créalos en "Extras y opciones" del menú y luego márcalos aquí.
            </Typography>
          ) : (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {grupos.map((g) => (
                <FormControlLabel
                  key={g.id}
                  sx={{ width: { xs: "100%", sm: "48%" }, mr: 0 }}
                  control={
                    <Checkbox
                      size="small"
                      checked={valor.grupos.includes(g.id)}
                      onChange={() => alternarGrupo(g.id)}
                    />
                  }
                  label={
                    <Typography sx={{ fontSize: 14 }}>
                      {g.nombre}{" "}
                      <Typography component="span" sx={{ fontSize: 12.5, color: "text.secondary" }}>
                        ({resumenGrupo(g)})
                      </Typography>
                    </Typography>
                  }
                />
              ))}
            </Box>
          )}
        </Box>
      </Stack>
    </Box>
  );
}
