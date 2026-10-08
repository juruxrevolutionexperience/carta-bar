import { createTheme, type Theme } from "@mui/material/styles";

// Paleta identica a la de estilos.css (variables CSS, usadas por las
// pantallas que todavia no estan migradas a MUI): un solo origen de verdad
// a mano, repetido aqui porque el tema de MUI no puede leer variables CSS en
// tiempo de construccion del objeto. Si una se toca, tocar la otra.
const paletaClara = {
  primary: { light: "#e3f2fd", main: "#2196f3", dark: "#1e88e5" },
  secondary: { light: "#ede7f6", main: "#673ab7", dark: "#5e35b1" },
  success: { light: "#b9f6ca", main: "#00c853", dark: "#00c853" },
  warning: { light: "#fff8e1", main: "#ffc107", dark: "#ffc107" },
  error: { light: "#ef9a9a", main: "#f44336", dark: "#c62828" },
  grey: {
    50: "#f8fafc",
    100: "#eef2f6",
    200: "#e3e8ef",
    300: "#cdd5df",
    500: "#697586",
    600: "#4b5565",
    700: "#364152",
    900: "#121926",
  },
};

const paletaOscura = {
  primary: { light: "#90caf9", main: "#2196f3", dark: "#1e88e5" },
  secondary: { light: "#d1c4e9", main: "#7c4dff", dark: "#651fff" },
  success: { light: "#b9f6ca", main: "#00e676", dark: "#00c853" },
  warning: { light: "#fff8e1", main: "#ffc107", dark: "#ffc107" },
  error: { light: "#ef9a9a", main: "#f44336", dark: "#c62828" },
};

export function crearTemaMui(modo: "light" | "dark"): Theme {
  const esOscuro = modo === "dark";
  return createTheme({
    palette: {
      mode: modo,
      primary: esOscuro ? paletaOscura.primary : paletaClara.primary,
      secondary: esOscuro ? paletaOscura.secondary : paletaClara.secondary,
      success: esOscuro ? paletaOscura.success : paletaClara.success,
      warning: esOscuro ? paletaOscura.warning : paletaClara.warning,
      error: esOscuro ? paletaOscura.error : paletaClara.error,
      background: esOscuro
        ? { default: "#1a223f", paper: "#111936" }
        : { default: "#f8fafc", paper: "#ffffff" },
      text: esOscuro
        ? { primary: "#d7dcec", secondary: "#8492c4" }
        : { primary: paletaClara.grey[700], secondary: paletaClara.grey[500] },
      divider: esOscuro ? "rgba(255,255,255,0.08)" : paletaClara.grey[200],
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: '"Roboto", system-ui, sans-serif',
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: "none" },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 8 },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: { borderRadius: 12 },
        },
      },
    },
  });
}
