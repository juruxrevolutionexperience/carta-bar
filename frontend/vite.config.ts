import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Multi-pagina: cada pantalla migrada es una entrada propia, para poder
// migrar de una en una sin que el resto del sitio dependa de nada.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        "admin-login": fileURLToPath(new URL("./admin-login.html", import.meta.url)),
      },
    },
  },
});
