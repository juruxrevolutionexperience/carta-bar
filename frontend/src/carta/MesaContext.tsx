import { createContext, useContext, useState, type ReactNode } from "react";

import { pedirCuenta as pedirCuentaApi } from "./api";
import { useComandas } from "./useComandas";
import { useMesa } from "./useMesa";
import { usePropuestas } from "./usePropuestas";
import type { ResumenComanda } from "./types";

interface MesaContextValue extends ReturnType<typeof usePropuestas> {
  mesa: ReturnType<typeof useMesa>["mesa"];
  pidiendoNombre: boolean;
  entrar: (nombre: string) => void;
  // Se abre solo al proponer un plato (FormularioPropuesta), para que quede
  // claro que se ha añadido a una cesta compartida y no a un pedido ya
  // mandado (ver docs/PEDIDO-EN-MESA.md, "Bloque 2 en detalle").
  panelAbierto: boolean;
  abrirPanel: () => void;
  cerrarPanel: () => void;
  // Una vez confirmado, si ya se sirvio o no (bloque 3, "Bloque 3 en detalle").
  comandas: ResumenComanda[];
  // Solo el anfitrion, y solo con la mesa ya abierta ("Pedir la cuenta y
  // cobrar"). El cambio de estado llega solo, por el refresco de useMesa.
  pedirCuenta: () => Promise<boolean>;
}

const MesaContext = createContext<MesaContextValue | null>(null);

export function useMesaContext(): MesaContextValue {
  const ctx = useContext(MesaContext);
  if (!ctx) throw new Error("useMesaContext fuera de <MesaProvider>");
  return ctx;
}

export function MesaProvider({ children }: { children: ReactNode }) {
  const { mesa, pidiendoNombre, entrar } = useMesa();
  const propuestas = usePropuestas(mesa);
  const comandas = useComandas(mesa);
  const [panelAbierto, setPanelAbierto] = useState(false);

  const value: MesaContextValue = {
    mesa,
    pidiendoNombre,
    entrar,
    ...propuestas,
    panelAbierto,
    abrirPanel: () => setPanelAbierto(true),
    cerrarPanel: () => setPanelAbierto(false),
    comandas,
    pedirCuenta: pedirCuentaApi,
  };

  return <MesaContext.Provider value={value}>{children}</MesaContext.Provider>;
}
