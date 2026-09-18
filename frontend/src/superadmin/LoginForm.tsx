import { useState, type FormEvent } from "react";

import "./estilos.css";

export function LoginForm() {
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(ev: FormEvent) {
    ev.preventDefault();
    setError(null);
    setEnviando(true);

    try {
      const resp = await fetch("/superadmin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clave }),
      });
      if (resp.ok) {
        window.location.href = "/superadmin";
        return;
      }
      setError("Contraseña incorrecta");
    } catch {
      setError("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="tarjeta">
      <h1>Panel superadmin</h1>
      <p className="sub">Acceso del dueño de la plataforma — no es el panel de ningún restaurante</p>
      {error && <div className="error">{error}</div>}
      <form onSubmit={enviar}>
        <label htmlFor="clave">Contraseña</label>
        <input
          type="password"
          id="clave"
          name="clave"
          autoComplete="current-password"
          required
          value={clave}
          onChange={(ev) => setClave(ev.target.value)}
        />
        <button type="submit" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
