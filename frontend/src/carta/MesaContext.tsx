import { createContext, useContext, type ReactNode } from "react";

import { useMesa } from "./useMesa";
import { usePropuestas } from "./usePropuestas";

const MesaContext = createContext<
  (ReturnType<typeof usePropuestas> & { mesa: ReturnType<typeof useMesa> }) | null
>(null);

export function useMesaContext() {
  const ctx = useContext(MesaContext);
  if (!ctx) throw new Error("useMesaContext fuera de <MesaProvider>");
  return ctx;
}

export function MesaProvider({ children }: { children: ReactNode }) {
  const mesa = useMesa();
  const propuestas = usePropuestas(mesa);
  return <MesaContext.Provider value={{ mesa, ...propuestas }}>{children}</MesaContext.Provider>;
}
