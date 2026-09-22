import { useCallback, useEffect, useState } from "react";

// Al abrir una foto se mete una entrada en el historial: asi el boton
// "atras" del movil cierra el visor en vez de salir de la pagina. Navegar
// con las flechas dentro del visor (siguiente/mismo modal) no mete una
// entrada nueva cada vez: solo la primera apertura empuja el historial.
export function useVisorFoto() {
  const [platoId, setPlatoId] = useState<string | null>(null);

  const cerrar = useCallback((volviendoAtras: boolean) => {
    setPlatoId((actual) => {
      if (actual === null) return actual;
      if (!volviendoAtras) history.back();
      return null;
    });
  }, []);

  const abrir = useCallback((id: string) => {
    setPlatoId((actual) => {
      if (actual === null) history.pushState({ visorFoto: true }, "");
      return id;
    });
  }, []);

  useEffect(() => {
    const alVolver = () => cerrar(true);
    window.addEventListener("popstate", alVolver);
    return () => window.removeEventListener("popstate", alVolver);
  }, [cerrar]);

  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === "Escape") cerrar(false);
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [cerrar]);

  return { platoId, abrir, cerrar };
}
