import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { prevenirZoomIOS } from "../shared/prevenirZoomIOS";
import { LoginForm } from "./LoginForm";

prevenirZoomIOS();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LoginForm />
  </StrictMode>
);
