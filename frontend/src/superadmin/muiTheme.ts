import { createTheme, type Theme } from "@mui/material/styles";

// Mismo patron que admin/muiTheme.ts, pero con el secundario de Berry
// (morado) como color principal: es el acento que distingue este panel del
// panel del gerente (azul), ver estilos.css.
export function crearTemaMui(modo: "light" | "dark"): Theme {
  const esOscuro = modo === "dark";
  return createTheme({
    palette: {
      mode: modo,
      primary: esOscuro
        ? { light: "#d1c4e9", main: "#7c4dff", dark: "#651fff" }
        : { light: "#ede7f6", main: "#673ab7", dark: "#5e35b1" },
      error: { main: "#f44336" },
      success: { main: esOscuro ? "#00e676" : "#00c853" },
      background: esOscuro
        ? { default: "#1a223f", paper: "#111936" }
        : { default: "#f8fafc", paper: "#ffffff" },
      text: esOscuro
        ? { primary: "#d7dcec", secondary: "#8492c4" }
        : { primary: "#364152", secondary: "#697586" },
      divider: esOscuro ? "rgba(255,255,255,0.08)" : "#e3e8ef",
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: '"Roboto", system-ui, sans-serif',
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
      MuiButton: { styleOverrides: { root: { borderRadius: 8 } } },
      MuiCard: { styleOverrides: { root: { borderRadius: 12 } } },
    },
  });
}
