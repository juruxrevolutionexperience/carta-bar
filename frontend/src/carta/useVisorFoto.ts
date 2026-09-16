import { useCallback, useEffect, useState } from "react";

// Al abrir una foto se mete una entrada en el historial: asi el boton
// "atras" del movil cierra la foto en vez de salir de la pagina.
export function useVisorFoto() {
  const [src, setSrc] = useState<string | null>(null);

  const cerrar = useCallback((volviendoAtras: boolean) => {
    setSrc((actual) => {
      if (actual === null) return actual;
      if (!volviendoAtras) history.back();
      return null;
    });
  }, []);

  const abrir = useCallback((nuevoSrc: string) => {
    setSrc(nuevoSrc);
    history.pushState({ visorFoto: true }, "");
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

  return { src, abrir, cerrar };
}
