import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { pedirCuenta as pedirCuentaApi } from "./api";
import { useComandas } from "./useComandas";
import { useMesa } from "./useMesa";
import { usePropuestas } from "./usePropuestas";
import type { ResumenComanda } from "./types";

interface MesaContextValue extends ReturnType<typeof usePropuestas> {
  mesa: ReturnType<typeof useMesa>["mesa"];
  pidiendoNombre: boolean;
  entrar: (nombre: string) => void;
  // Solo lo abre el cliente, cuando quiere revisar o enviar. Antes se abria
  // solo al anadir cada plato y cortaba el ir eligiendo: decidido con el
  // dueno el 2026-10-04 tras probarlo en el bar.
  panelAbierto: boolean;
  abrirPanel: () => void;
  cerrarPanel: () => void;
  // Lo que se acaba de anadir, para un aviso breve que se quita solo: el
  // cliente sabe que ha entrado sin que nada le tape la carta.
  recienAnadido: { nombre: string; vez: number } | null;
  anunciarAnadido: (nombre: string) => void;
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

// Para componentes que se reutilizan fuera de la carta (la vista previa de
// un plato en el panel del gerente usa el mismo PlatoCard, sin MesaProvider
// alrededor): null en vez de reventar, y quien lo use trata "sin mesa" igual
// que "null" de toda la vida.
export function useMesaContextOpcional(): MesaContextValue | null {
  return useContext(MesaContext);
}

export function MesaProvider({ children }: { children: ReactNode }) {
  const { mesa, pidiendoNombre, entrar } = useMesa();
  const propuestas = usePropuestas(mesa);
  const comandas = useComandas(mesa);
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [recienAnadido, setRecienAnadido] = useState<{ nombre: string; vez: number } | null>(
    null
  );
  const temporizador = useRef<number | undefined>(undefined);

  function anunciarAnadido(nombre: string) {
    // `vez` cambia aunque se repita el mismo plato: reinicia la animacion.
    setRecienAnadido((actual) => ({ nombre, vez: (actual?.vez ?? 0) + 1 }));
    window.clearTimeout(temporizador.current);
    temporizador.current = window.setTimeout(() => setRecienAnadido(null), 3200);
  }

  useEffect(() => () => window.clearTimeout(temporizador.current), []);

  const value: MesaContextValue = {
    mesa,
    pidiendoNombre,
    entrar,
    ...propuestas,
    panelAbierto,
    abrirPanel: () => {
      setRecienAnadido(null);
      setPanelAbierto(true);
    },
    cerrarPanel: () => setPanelAbierto(false),
    recienAnadido,
    anunciarAnadido,
    comandas,
    pedirCuenta: pedirCuentaApi,
  };

  return <MesaContext.Provider value={value}>{children}</MesaContext.Provider>;
}
