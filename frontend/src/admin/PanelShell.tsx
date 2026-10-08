import { useEffect, useState } from "react";

import {
  IconChevronDown,
  IconMenu2,
  IconMoon,
  IconSun,
} from "@tabler/icons-react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";

import { SECCIONES, tituloDe, type Seccion } from "./secciones";
import type { Tema } from "./tema";

// Mismo valor que --ancho-menu y --alto-barra en estilos.css: el padding del
// contenido (.app) reserva exactamente este hueco, asi que si uno cambia hay
// que cambiar el otro.
const ANCHO_DRAWER = 260;
const ALTO_BARRA = 56;

const CLAVE_MONTAJE_ABIERTO = "cartaBar.menu.montajeAbierto";

interface Props {
  seccion: Seccion;
  abierto: boolean;
  onCambiar: (s: Seccion) => void;
  onAbrir: () => void;
  onCerrar: () => void;
  tema: Tema;
  onAlternarTema: () => void;
}

// Barra superior + menu lateral, con los componentes reales de MUI (AppBar +
// Drawer), no una imitacion en CSS. Sustituye a BarraSuperior.tsx y
// MenuLateral.tsx. En movil, y tambien en escritorio dentro de Mesas (el
// plano quiere toda la pantalla, como un TPV), el menu es "temporary": se
// abre con la hamburguesa y no reserva hueco fijo.
export function PanelShell({
  seccion,
  abierto,
  onCambiar,
  onAbrir,
  onCerrar,
  tema,
  onAlternarTema,
}: Props) {
  const muiTheme = useTheme();
  const esMovil = useMediaQuery(muiTheme.breakpoints.down("md"));
  const flotante = esMovil || seccion === "mesas";

  const [montajeAbierto, setMontajeAbierto] = useState(() => {
    try {
      return localStorage.getItem(CLAVE_MONTAJE_ABIERTO) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(CLAVE_MONTAJE_ABIERTO, montajeAbierto ? "1" : "0");
    } catch {
      // Sin almacenamiento: no pasa nada, simplemente no se recuerda.
    }
  }, [montajeAbierto]);

  const diaADia = SECCIONES.filter((s) => !s.montaje);
  const montaje = SECCIONES.filter((s) => s.montaje);

  function elegir(id: Seccion) {
    onCambiar(id);
    if (flotante) onCerrar();
  }

  function item(s: (typeof SECCIONES)[number]) {
    const activo = s.id === seccion;
    return (
      <ListItemButton
        key={s.id}
        selected={activo}
        onClick={() => elegir(s.id)}
        sx={{
          borderRadius: 2,
          mb: 0.5,
          color: activo ? "primary.main" : "text.secondary",
          "&.Mui-selected": {
            backgroundColor: (t) =>
              t.palette.mode === "dark" ? "rgba(144,202,249,0.16)" : "primary.light",
          },
        }}
      >
        <ListItemIcon sx={{ minWidth: 36, color: "inherit" }}>{s.icono}</ListItemIcon>
        <ListItemText
          primary={s.texto}
          slotProps={{ primary: { fontSize: 14.5, fontWeight: activo ? 600 : 400 } }}
        />
      </ListItemButton>
    );
  }

  const contenidoMenu = (
    <Box sx={{ width: ANCHO_DRAWER, display: "flex", flexDirection: "column", height: "100%" }}>
      <Box sx={{ px: 2.5, py: 2.5 }}>
        <Typography sx={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.02em" }}>
          Carta Bar
        </Typography>
        <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.25 }}>
          Panel de gestión
        </Typography>
      </Box>
      <Divider />
      <List sx={{ px: 1.5, py: 1.5, overflowY: "auto", overflowX: "hidden" }}>
        {diaADia.map(item)}
        <ListItemButton
          onClick={() => setMontajeAbierto((v) => !v)}
          sx={{ borderRadius: 2, mt: 1 }}
        >
          <ListItemText
            primary="MONTAJE"
            slotProps={{
              primary: {
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: "text.secondary",
              },
            }}
          />
          <IconChevronDown
            size={16}
            style={{
              transform: montajeAbierto ? "rotate(180deg)" : "none",
              transition: "transform 0.15s ease",
            }}
          />
        </ListItemButton>
        <Collapse in={montajeAbierto}>{montaje.map(item)}</Collapse>
      </List>
    </Box>
  );

  return (
    <>
      <AppBar
        position="fixed"
        color="default"
        elevation={0}
        sx={{
          backgroundColor: "background.paper",
          borderBottom: 1,
          borderColor: "divider",
          zIndex: (t) => t.zIndex.drawer + 1,
          ...(flotante ? {} : { ml: `${ANCHO_DRAWER}px`, width: `calc(100% - ${ANCHO_DRAWER}px)` }),
        }}
      >
        <Toolbar sx={{ minHeight: `${ALTO_BARRA}px !important` }}>
          {flotante && (
            <IconButton edge="start" onClick={onAbrir} aria-label="Abrir el menú" sx={{ mr: 1.5 }}>
              <IconMenu2 size={22} />
            </IconButton>
          )}
          <Typography sx={{ fontSize: 15, fontWeight: 600, flexGrow: 1 }}>
            {tituloDe(seccion)}
          </Typography>
          <Typography
            sx={{
              fontSize: 11.5,
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: "text.secondary",
              mr: 1,
              display: { xs: "none", sm: "block" },
            }}
          >
            CARTA BAR
          </Typography>
          <IconButton
            onClick={onAlternarTema}
            aria-label={tema === "claro" ? "Cambiar al tema oscuro" : "Cambiar al tema claro"}
            title={tema === "claro" ? "Tema oscuro" : "Tema claro"}
          >
            {tema === "claro" ? <IconMoon size={20} /> : <IconSun size={20} />}
          </IconButton>
        </Toolbar>
      </AppBar>
      <Drawer
        variant={flotante ? "temporary" : "permanent"}
        open={flotante ? abierto : true}
        onClose={onCerrar}
        ModalProps={{ keepMounted: true }}
        sx={{
          width: ANCHO_DRAWER,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: ANCHO_DRAWER,
            boxSizing: "border-box",
            borderRight: 1,
            borderColor: "divider",
            overflowX: "hidden",
          },
        }}
      >
        <Toolbar sx={{ minHeight: `${ALTO_BARRA}px !important` }} />
        {contenidoMenu}
      </Drawer>
    </>
  );
}
