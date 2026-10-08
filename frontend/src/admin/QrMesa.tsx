import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

import { HojaQR, type DatosQr } from "../shared/HojaQR";
import type { Mesa } from "./api";

// La direccion que lleva el QR de una mesa: la de la carta del restaurante
// mas el token secreto de esa mesa. La carta aun no lo lee (llega con el
// siguiente bloque: proponer platos); hasta entonces abre la carta normal.
function urlDeMesa(base: string, token: string): string {
  const url = new URL(base);
  url.searchParams.set("mesa", token);
  return url.toString();
}

interface Props {
  mesa: Mesa;
  qr: DatosQr;
  compacta: boolean;
  ocupado: boolean;
  onRegenerar: (mesa: Mesa) => void;
}

export function QrMesa({ mesa, qr, compacta, ocupado, onRegenerar }: Props) {
  return (
    <Stack spacing={1.5}>
      <HojaQR
        url={urlDeMesa(qr.url, mesa.token_qr)}
        nombre={mesa.nombre}
        texto={qr.texto}
        compacta={compacta}
      />
      <Button variant="outlined" disabled={ocupado} onClick={() => onRegenerar(mesa)}>
        Cambiar el QR de esta mesa
      </Button>
    </Stack>
  );
}
