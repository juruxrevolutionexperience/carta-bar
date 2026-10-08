import { useEffect, useState } from "react";

import { IconX } from "@tabler/icons-react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  abrirMesa,
  cargarSesionMesa,
  cobrarMesa,
  confirmarMesa,
  expulsarComensal,
  liberarMesa,
  type Mesa,
  type SesionConComensales,
} from "./api";
import { PanelComandaMesa } from "./PanelComandaMesa";
import { TEXTO_ESTADO, estadoDe, personas, tiempoDesde } from "./servicioUtil";

interface Props {
  mesa: Mesa;
  ahora: number;
  // Tras cada acción: la pantalla vuelve a pedir las mesas para pintar el estado.
  onCambio: () => void;
  onCerrar: () => void;
  // Solo lo usa Mesas (el plano), donde el panel es una hoja que tapa la
  // pantalla en móvil y solo se ve si se abrió a propósito. Sin este prop
  // (SeccionServicio, que no tiene plano) el panel se ve siempre.
  abiertoEnMovil?: boolean;
}

const MAX_COMENSALES = 50;

// Lo que el camarero hace con una mesa durante el servicio: abrirla, aceptar la
// que abrió un cliente, gestionar su comanda, liberarla y quitar a alguien que
// no debería estar. Es el mismo panel en Servicio y en Mesas (modo ojo): la
// mesa es la misma, no hay dos gestiones distintas. Se monta con
// key={mesa.id}: al tocar otra mesa arranca limpio.
export function PanelServicio({
  mesa,
  ahora,
  onCambio,
  onCerrar,
  abiertoEnMovil = true,
}: Props) {
  const estado = estadoDe(mesa);
  const [datos, setDatos] = useState<SesionConComensales | null>(null);
  const [comensales, setComensales] = useState(Math.min(mesa.capacidad, MAX_COMENSALES));
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  // Se vuelve a pedir cuando el listado dice que algo cambió (alguien entró,
  // la aceptaron, caducó...), no en cada refresco.
  useEffect(() => {
    if (estado === "libre") {
      setDatos(null);
      return;
    }
    let vigente = true;
    cargarSesionMesa(mesa.id)
      .then((d) => vigente && setDatos(d))
      .catch(() => vigente && setAviso("No se pudo cargar quién está en la mesa."));
    return () => {
      vigente = false;
    };
  }, [mesa.id, estado, mesa.comensales]);

  async function hacer(accion: () => Promise<Response>) {
    setOcupado(true);
    setAviso(null);
    try {
      const resp = await accion();
      if (!resp.ok) {
        setAviso((await resp.text()) || "No se pudo hacer. Inténtalo otra vez.");
      }
    } catch {
      setAviso("Sin conexión. Inténtalo otra vez.");
    } finally {
      setOcupado(false);
      onCambio();
    }
  }

  function liberar() {
    const texto =
      estado === "por_confirmar"
        ? `¿Liberar "${mesa.nombre}"? Si nadie está sentado ahí, es lo correcto.`
        : `¿Liberar "${mesa.nombre}"? Los clientes perderán la mesa en su móvil.`;
    if (!window.confirm(texto)) return;
    void hacer(() => liberarMesa(mesa.id));
  }

  function cobrar() {
    if (!window.confirm(`¿Ya has cobrado "${mesa.nombre}"? La mesa quedará libre.`)) return;
    void hacer(() => cobrarMesa(mesa.id));
  }

  function quitar(id: string, nombre: string) {
    if (!window.confirm(`¿Quitar a ${nombre} de la mesa? Ya no podrá pedir desde su móvil.`)) {
      return;
    }
    void hacer(() => expulsarComensal(id));
  }

  const dentro = datos?.comensales.filter((c) => c.expulsado_en === null) ?? [];
  const declarados = datos?.sesion.comensales_declarados ?? null;
  const tiempo = tiempoDesde(mesa.abierta_en, ahora);

  const colorEstado: "warning" | "info" | "primary" | "default" =
    estado === "por_confirmar"
      ? "warning"
      : estado === "cuenta_pedida"
        ? "info"
        : estado === "abierta"
          ? "primary"
          : "default";

  return (
    <Card
      className={"panel-mesa panel-servicio" + (abiertoEnMovil ? "" : " oculto-movil")}
      sx={{ p: 2.5 }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="h3">{mesa.nombre}</Typography>
        <IconButton size="small" aria-label="Cerrar" onClick={onCerrar}>
          <IconX size={18} />
        </IconButton>
      </Stack>

      <Chip
        label={tiempo ? `${TEXTO_ESTADO[estado]} · ${tiempo}` : TEXTO_ESTADO[estado]}
        color={colorEstado}
        size="small"
        sx={{ mb: 2 }}
      />

      {estado === "libre" && (
        <>
          <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>
            Ábrela si se sienta alguien sin usar el QR. Si no, el primero que lo escanee la abrirá
            y te saldrá aquí para aceptarla.
          </Typography>
          <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.5 }}>
            Comensales
          </Typography>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
            <IconButton
              size="small"
              aria-label="Uno menos"
              disabled={comensales <= 1}
              onClick={() => setComensales((n) => Math.max(1, n - 1))}
              sx={{ border: 1, borderColor: "divider" }}
            >
              −
            </IconButton>
            <Typography sx={{ fontSize: 18, fontWeight: 700, minWidth: 24, textAlign: "center" }}>
              {comensales}
            </Typography>
            <IconButton
              size="small"
              aria-label="Uno más"
              disabled={comensales >= MAX_COMENSALES}
              onClick={() => setComensales((n) => Math.min(MAX_COMENSALES, n + 1))}
              sx={{ border: 1, borderColor: "divider" }}
            >
              +
            </IconButton>
          </Stack>
          <Button
            variant="contained"
            fullWidth
            disabled={ocupado}
            onClick={() => void hacer(() => abrirMesa(mesa.id, comensales))}
            sx={{ mb: 1.5 }}
          >
            Abrir mesa
          </Button>
        </>
      )}

      {estado === "por_confirmar" && (
        <>
          <Typography sx={{ fontSize: 14, color: "text.secondary", mb: 2 }}>
            Un cliente la ha abierto con el QR. Sal a la mesa y, si de verdad están ahí, acéptala:
            hasta entonces no llega nada a cocina.
          </Typography>
          <Button
            variant="contained"
            fullWidth
            disabled={ocupado}
            onClick={() => void hacer(() => confirmarMesa(mesa.id))}
            sx={{ mb: 1.5 }}
          >
            Aceptar mesa
          </Button>
        </>
      )}

      {estado !== "libre" && (
        <>
          <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 1 }}>
            En la mesa
            {declarados !== null && (
              <Box component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>
                {" "}
                · dijeron {personas(declarados)}
              </Box>
            )}
          </Typography>
          {datos === null ? (
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>Cargando…</Typography>
          ) : dentro.length === 0 ? (
            <Typography sx={{ fontSize: 14, color: "text.secondary" }}>
              Nadie ha escaneado el QR todavía.
            </Typography>
          ) : (
            <Stack spacing={0.5} sx={{ mb: 1 }}>
              {dentro.map((c) => (
                <Stack
                  key={c.id}
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{ py: 0.5, borderBottom: 1, borderColor: "divider" }}
                >
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <Typography sx={{ fontSize: 14 }}>{c.nombre}</Typography>
                    {c.rol === "anfitrion" && (
                      <Chip label="anfitrión" size="small" variant="outlined" />
                    )}
                  </Stack>
                  <Button size="small" disabled={ocupado} onClick={() => quitar(c.id, c.nombre)}>
                    Quitar
                  </Button>
                </Stack>
              ))}
            </Stack>
          )}

          <PanelComandaMesa mesaId={mesa.id} />

          {estado === "cuenta_pedida" && (
            <Button
              variant="contained"
              fullWidth
              disabled={ocupado}
              onClick={cobrar}
              sx={{ mt: 2, mb: 1.5 }}
            >
              Cobrar y cerrar
            </Button>
          )}

          <Button
            variant="outlined"
            color="error"
            fullWidth
            disabled={ocupado}
            onClick={liberar}
            sx={{ mt: estado === "cuenta_pedida" ? 0 : 2 }}
          >
            Liberar mesa
          </Button>
        </>
      )}

      {aviso && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {aviso}
        </Alert>
      )}
    </Card>
  );
}
