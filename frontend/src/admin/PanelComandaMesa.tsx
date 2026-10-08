import { useCallback, useEffect, useState } from "react";

import { IconCheck } from "@tabler/icons-react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  ajustarPrecioLinea,
  anadirAComanda,
  cargarComandaMesa,
  confirmarComandaMesa,
  quitarDeComanda,
  type ComandaMesa,
  type NuevaLineaComanda,
  type Propuesta,
} from "./api";
import { SelectorTPV } from "./SelectorTPV";

const REFRESCO_MS = 5000;

function lineaTexto(p: Propuesta): string {
  const partes = [p.formato, ...p.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${p.nombre_plato} (${partes.join(", ")})` : p.nombre_plato;
}

function importe(n: number): string {
  return n.toFixed(2).replace(".", ",") + " €";
}

interface Props {
  mesaId: string;
}

// Lo que pide el camarero/gerente: entrar en la mesa y ver todo el pedido,
// quien pidio que, el total, cuanto le toca a cada uno, y poder anadir,
// quitar o ajustar un precio sin salir de aqui (docs/PEDIDO-EN-MESA.md,
// "Gestion de la comanda desde la mesa").
export function PanelComandaMesa({ mesaId }: Props) {
  const [comanda, setComanda] = useState<ComandaMesa | null>(null);
  const [error, setError] = useState(false);
  const [anadiendo, setAnadiendo] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [editando, setEditando] = useState<string | null>(null);
  const [precioEditado, setPrecioEditado] = useState("");

  const recargar = useCallback(() => {
    cargarComandaMesa(mesaId)
      .then((c) => {
        setComanda(c);
        setError(c === null);
      })
      .catch(() => setError(true));
  }, [mesaId]);

  useEffect(recargar, [recargar]);
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) recargar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [recargar]);

  async function anadir(datos: NuevaLineaComanda): Promise<boolean> {
    const r = await anadirAComanda(mesaId, datos);
    if (r.ok) recargar();
    return r.ok;
  }

  async function quitar(propuestaId: string) {
    setOcupado(true);
    try {
      await quitarDeComanda(mesaId, propuestaId);
      recargar();
    } finally {
      setOcupado(false);
    }
  }

  async function guardarPrecio(propuestaId: string) {
    const nuevo = Number(precioEditado.replace(",", "."));
    if (!Number.isFinite(nuevo) || nuevo < 0) return;
    setOcupado(true);
    try {
      await ajustarPrecioLinea(mesaId, propuestaId, nuevo);
      setEditando(null);
      recargar();
    } finally {
      setOcupado(false);
    }
  }

  async function confirmar() {
    if (!window.confirm("¿Mandar esto a cocina/barra?")) return;
    setOcupado(true);
    try {
      await confirmarComandaMesa(mesaId);
      recargar();
    } finally {
      setOcupado(false);
    }
  }

  if (error && comanda === null) {
    return <p className="explicacion">No se pudo cargar la comanda.</p>;
  }
  if (comanda === null) {
    return <p className="explicacion">Cargando…</p>;
  }

  const activas = comanda.propuestas.filter((p) => p.estado !== "retirada");
  const pendientes = activas.filter((p) => p.estado === "pendiente");

  return (
    <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: "divider" }}>
      <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 1 }}>Comanda</Typography>

      {activas.length === 0 && (
        <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
          Nada pedido todavía.
        </Typography>
      )}

      {activas.length > 0 && (
        <Stack spacing={1} sx={{ mb: 1.5 }}>
          {activas.map((p) => (
            <Box key={p.id} sx={{ pb: 1, borderBottom: 1, borderColor: "divider" }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography sx={{ fontSize: 14 }}>
                  {p.cantidad}× {lineaTexto(p)}
                  {p.estado === "confirmada" && (
                    <Chip label="pedido" size="small" color="primary" variant="outlined" sx={{ ml: 0.5 }} />
                  )}
                </Typography>
                {editando === p.id ? (
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <TextField
                      type="number"
                      size="small"
                      autoFocus
                      slotProps={{ htmlInput: { step: 0.01, min: 0 } }}
                      value={precioEditado}
                      onChange={(e) => setPrecioEditado(e.target.value)}
                      sx={{ width: 90 }}
                    />
                    <IconButton size="small" onClick={() => void guardarPrecio(p.id)}>
                      <IconCheck size={18} />
                    </IconButton>
                  </Stack>
                ) : (
                  <Button
                    size="small"
                    onClick={() => {
                      setEditando(p.id);
                      setPrecioEditado(String(p.precio_unitario));
                    }}
                  >
                    {importe(p.total)}
                  </Button>
                )}
              </Stack>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography sx={{ fontSize: 12.5, color: "text.secondary" }}>
                  {p.comensal_nombre}
                </Typography>
                {p.estado === "pendiente" && (
                  <Button size="small" color="error" disabled={ocupado} onClick={() => void quitar(p.id)}>
                    Quitar
                  </Button>
                )}
              </Stack>
            </Box>
          ))}
        </Stack>
      )}

      {comanda.por_persona.length > 1 && (
        <Stack spacing={0.25} sx={{ mb: 1.5 }}>
          {comanda.por_persona.map((r) => (
            <Stack key={r.nombre} direction="row" justifyContent="space-between">
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{r.nombre}</Typography>
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                {importe(r.total)}
              </Typography>
            </Stack>
          ))}
        </Stack>
      )}

      <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1.5 }}>
        <Typography sx={{ fontSize: 15 }}>Total</Typography>
        <Typography sx={{ fontSize: 16, fontWeight: 700 }}>{importe(comanda.total)}</Typography>
      </Stack>

      <Stack spacing={1}>
        <Button variant="outlined" onClick={() => setAnadiendo(true)}>
          Añadir a la mesa
        </Button>

        {pendientes.length > 0 && (
          <Button variant="contained" disabled={ocupado} onClick={() => void confirmar()}>
            Confirmar comanda ({pendientes.length})
          </Button>
        )}
      </Stack>

      {anadiendo && <SelectorTPV onElegir={anadir} onCerrar={() => setAnadiendo(false)} />}
    </Box>
  );
}
