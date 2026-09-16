import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { prevenirZoomIOS } from "../shared/prevenirZoomIOS";
import { App } from "./App";

prevenirZoomIOS();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
