import { useCallback, useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { anularLinea, cambiarEstadoTicket, cargarTickets, type Destino, type Ticket } from "./api";

const REFRESCO_MS = 5000;

const TODOS = "todos";
type Filtro = Destino | typeof TODOS;

const TEXTO_DESTINO: Record<Destino, string> = { cocina: "Cocina", barra: "Barra" };

function lineaTexto(l: Ticket["lineas"][number]): string {
  const partes = [l.formato, ...l.opciones.map((o) => o.nombre)].filter(Boolean);
  return partes.length > 0 ? `${l.nombre_plato} (${partes.join(", ")})` : l.nombre_plato;
}

// La pantalla que mas importa en el dia a dia (docs/PEDIDO-EN-MESA.md,
// seccion 11.2): tarjetas grandes, una por ticket, para leerlas de pie y con
// prisa. De momento vive en el /admin del gerente; el acceso propio del
// camarero llega despues (bloque 3, "rol camarero"), sin tener que rehacer
// esto.
export function SeccionCocina() {
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState(false);
  const [filtro, setFiltro] = useState<Filtro>(TODOS);
  const [ocupado, setOcupado] = useState<string | null>(null);

  const recargar = useCallback(() => {
    cargarTickets()
      .then((t) => {
        setTickets(t);
        setError(false);
      })
      .catch(() => setError(true));
  }, []);

  useEffect(recargar, [recargar]);
  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) recargar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [recargar]);

  // Un solo toque: de pendiente a servida. Antes habia un paso "Empezar" que
  // obligaba a alguien a pulsar cada comanda al llegar, y en hora punta eso
  // es tiempo perdido (decidido con el dueno el 2026-10-04). El cliente ve
  // "en preparacion" desde que se envia hasta que se marca como lista.
  async function marcarLista(ticket: Ticket) {
    setOcupado(ticket.id);
    try {
      const r = await cambiarEstadoTicket(ticket.id, "servida");
      if (r.ok) recargar();
    } finally {
      setOcupado(null);
    }
  }

  async function anular(ticket: Ticket, lineaId: string) {
    const motivo = window.prompt("¿Por qué se anula? (lo verá el gerente)");
    if (!motivo || !motivo.trim()) return;
    setOcupado(ticket.id);
    try {
      const r = await anularLinea(ticket.id, lineaId, motivo.trim());
      if (r.ok) recargar();
    } finally {
      setOcupado(null);
    }
  }

  if (tickets === null) {
    return (
      <Card>
        <CardContent>
          <p>{error ? "No se pudieron cargar las comandas." : "Cargando…"}</p>
        </CardContent>
      </Card>
    );
  }

  // Del mas antiguo al mas nuevo (ya viene asi del servidor): lo que lleva
  // mas tiempo esperando, arriba. Incluye los que quedaran "en preparacion"
  // de antes de quitar el paso "Empezar".
  const visibles = tickets.filter((t) => filtro === TODOS || t.destino === filtro);

  return (
    <div className="cocina">
      <Stack direction="row" alignItems="center" flexWrap="wrap" gap={1} mb={1}>
        <Tabs
          value={filtro}
          onChange={(_, valor) => setFiltro(valor)}
          sx={{ minHeight: 36, "& .MuiTab-root": { minHeight: 36 } }}
        >
          {([TODOS, "cocina", "barra"] as const).map((d) => (
            <Tab key={d} value={d} label={d === TODOS ? "Todo" : TEXTO_DESTINO[d]} />
          ))}
        </Tabs>
        {error && <Chip label="Sin conexión" color="error" variant="outlined" size="small" />}
        <Link href="/admin/impresion" target="_blank" rel="noreferrer" sx={{ ml: "auto", fontSize: 13 }}>
          Pantalla de impresión ↗
        </Link>
      </Stack>

      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
        Para imprimir solas en cocina y barra, hace falta un aparato aparte dedicado a esto —
        nunca el TPV principal del bar. Ver "Pantalla de impresión" arriba.
      </Typography>

      {visibles.length === 0 && <p className="cargando">Sin comandas pendientes.</p>}

      <div className="lista-cocina">
        {visibles.map((t) => (
          <TarjetaTicket
            key={t.id}
            ticket={t}
            ocupado={ocupado === t.id}
            onLista={marcarLista}
            onAnular={anular}
          />
        ))}
      </div>
    </div>
  );
}

interface PropsTarjeta {
  ticket: Ticket;
  ocupado: boolean;
  onLista: (ticket: Ticket) => void;
  onAnular: (ticket: Ticket, lineaId: string) => void;
}

function TarjetaTicket({ ticket, ocupado, onLista, onAnular }: PropsTarjeta) {
  return (
    <Card
      component="article"
      className={"destino-" + ticket.destino}
      sx={{
        borderLeft: 4,
        borderLeftColor: ticket.destino === "cocina" ? "primary.main" : "secondary.main",
      }}
    >
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" mb={1}>
          <Typography sx={{ fontSize: 16, fontWeight: 700 }}>{ticket.mesa_nombre}</Typography>
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            Comanda {ticket.numero_comanda}
          </Typography>
        </Stack>
        <Stack component="ul" sx={{ listStyle: "none", m: 0, p: 0, mb: 1.5 }} spacing={1}>
          {ticket.lineas.map((l) => (
            <Box
              component="li"
              key={l.id}
              sx={{ opacity: l.anulada ? 0.6 : 1, borderBottom: 1, borderColor: "divider", pb: 1 }}
            >
              <Typography sx={{ fontSize: 14 }}>
                <Box component="span" sx={{ fontWeight: 700 }}>
                  {l.cantidad}×{" "}
                </Box>
                {lineaTexto(l)}
                {l.alcohol && (
                  <Chip label="alcohol" size="small" color="warning" sx={{ ml: 1 }} />
                )}
              </Typography>
              {l.anulada ? (
                <Typography sx={{ fontSize: 12.5, color: "error.main", fontWeight: 600 }}>
                  Anulada: {l.motivo_anulacion}
                </Typography>
              ) : (
                <>
                  {l.nota && (
                    <Typography sx={{ fontSize: 12.5, fontStyle: "italic", color: "text.secondary" }}>
                      {l.nota}
                    </Typography>
                  )}
                  <Button
                    size="small"
                    color="error"
                    disabled={ocupado}
                    onClick={() => onAnular(ticket, l.id)}
                    sx={{ minWidth: 0, p: 0, fontSize: 12 }}
                  >
                    Anular
                  </Button>
                </>
              )}
              <Typography sx={{ fontSize: 11.5, color: "text.secondary" }}>
                {l.pedido_por_nombre}
              </Typography>
            </Box>
          ))}
        </Stack>
        <Button
          variant="contained"
          fullWidth
          disabled={ocupado}
          onClick={() => onLista(ticket)}
        >
          Listo
        </Button>
      </CardContent>
    </Card>
  );
}
