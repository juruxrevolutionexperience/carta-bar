// touch-action (CSS) no cubre del todo Safari en iPhone: estos dos oyentes
// tapan el pellizco y el doble toque que se le escapan. Mismo comportamiento
// que ya tenian las paginas del panel antes de migrar a React.
export function prevenirZoomIOS(): void {
  (["gesturestart", "gesturechange", "gestureend"] as const).forEach((tipo) =>
    document.addEventListener(tipo, (e) => e.preventDefault(), { passive: false })
  );

  let ultimoToque = 0;
  document.addEventListener(
    "touchend",
    (e) => {
      const ahora = Date.now();
      const objetivo = e.target as HTMLElement | null;
      const esCampo = objetivo !== null && /^(INPUT|TEXTAREA|SELECT)$/.test(objetivo.tagName);
      if (ahora - ultimoToque <= 300 && !esCampo) {
        e.preventDefault();
        objetivo?.click();
      }
      ultimoToque = ahora;
    },
    { passive: false }
  );
}
