import { createContext, useContext, useState, type ReactNode } from "react";

import { useMesa } from "./useMesa";
import { usePropuestas } from "./usePropuestas";

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
  const [panelAbierto, setPanelAbierto] = useState(false);

  const value: MesaContextValue = {
    mesa,
    pidiendoNombre,
    entrar,
    ...propuestas,
    panelAbierto,
    abrirPanel: () => setPanelAbierto(true),
    cerrarPanel: () => setPanelAbierto(false),
  };

  return <MesaContext.Provider value={value}>{children}</MesaContext.Provider>;
}
