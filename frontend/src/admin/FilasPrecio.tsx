// Lista editable de "nombre + precio": los formatos de un plato (Tapa 3 €,
// Ración 10 €) y las opciones de un grupo (Queso +1 €, Poco hecha gratis).
// Se guarda como texto mientras se escribe ("2," a medias no es un número) y
// se convierte al guardar con `filasAValores`.

import { IconX } from "@tabler/icons-react";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

export interface FilaPrecio {
  nombre: string;
  precio: string;
}

interface Props {
  filas: FilaPrecio[];
  onCambio: (filas: FilaPrecio[]) => void;
  ejemploNombre: string;
  // Formatos: precio obligatorio. Opciones: vacío = gratis.
  precioOpcional?: boolean;
  maximo: number;
  textoAnadir: string;
}

export function FilasPrecio({
  filas,
  onCambio,
  ejemploNombre,
  precioOpcional = false,
  maximo,
  textoAnadir,
}: Props) {
  function cambiar(i: number, cambio: Partial<FilaPrecio>) {
    onCambio(filas.map((f, j) => (j === i ? { ...f, ...cambio } : f)));
  }

  return (
    <Stack spacing={1}>
      {filas.map((f, i) => (
        <Stack direction="row" spacing={1} alignItems="center" key={i}>
          <TextField
            size="small"
            value={f.nombre}
            slotProps={{ htmlInput: { maxLength: 40 } }}
            placeholder={ejemploNombre}
            aria-label="Nombre"
            onChange={(e) => cambiar(i, { nombre: e.target.value })}
            sx={{ flex: 2 }}
          />
          {/* Texto con teclado decimal, no type="number": en un móvil en
              español se escribe "1,50" y un campo numérico lo descarta. */}
          <TextField
            size="small"
            type="text"
            slotProps={{ htmlInput: { inputMode: "decimal" } }}
            autoComplete="off"
            value={f.precio}
            placeholder={precioOpcional ? "Gratis" : "€"}
            aria-label="Precio"
            onChange={(e) => cambiar(i, { precio: e.target.value.replace(/[^0-9.,]/g, "") })}
            sx={{ flex: 1 }}
          />
          <IconButton
            size="small"
            aria-label="Quitar"
            onClick={() => onCambio(filas.filter((_, j) => j !== i))}
          >
            <IconX size={16} />
          </IconButton>
        </Stack>
      ))}
      {filas.length < maximo && (
        <Button
          variant="text"
          size="small"
          sx={{ alignSelf: "flex-start" }}
          onClick={() => onCambio([...filas, { nombre: "", precio: "" }])}
        >
          + {textoAnadir}
        </Button>
      )}
    </Stack>
  );
}

export function valoresAFilas(valores: { nombre: string; precio: number }[]): FilaPrecio[] {
  return valores.map((v) => ({
    nombre: v.nombre,
    precio: v.precio === 0 ? "" : String(v.precio).replace(".", ","),
  }));
}

// Las filas vacías del todo se ignoran. Devuelve un texto de error si alguna
// está a medias o tiene un precio que no vale.
export function filasAValores(
  filas: FilaPrecio[],
  precioOpcional: boolean
): { nombre: string; precio: number }[] | string {
  const valores: { nombre: string; precio: number }[] = [];
  for (const f of filas) {
    const nombre = f.nombre.trim();
    const texto = f.precio.trim().replace(",", ".");
    if (!nombre && !texto) continue;
    if (!nombre) return "Falta el nombre en una de las filas.";
    if (!texto) {
      if (!precioOpcional) return `Falta el precio de "${nombre}".`;
      valores.push({ nombre, precio: 0 });
      continue;
    }
    const precio = /^\d+(\.\d{1,2})?$/.test(texto) ? Number(texto) : NaN;
    if (!Number.isFinite(precio) || precio < 0 || (!precioOpcional && precio === 0)) {
      return `El precio de "${nombre}" no vale.`;
    }
    valores.push({ nombre, precio: Math.round(precio * 100) / 100 });
  }
  const nombres = valores.map((v) => v.nombre.toLocaleLowerCase("es"));
  if (new Set(nombres).size !== nombres.length) return "Hay dos filas con el mismo nombre.";
  return valores;
}
