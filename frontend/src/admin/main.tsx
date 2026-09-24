import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { prevenirZoomIOS } from "../shared/prevenirZoomIOS";
import { App } from "./App";
import { aplicarTema, temaGuardado } from "./tema";

prevenirZoomIOS();
// Antes de pintar nada: si no, el panel parpadea en claro antes de pasar a oscuro.
aplicarTema(temaGuardado());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
