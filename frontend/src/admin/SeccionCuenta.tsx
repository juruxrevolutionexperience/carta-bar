import { useState, type FormEvent } from "react";

import { cambiarClave, cerrarSesion } from "./api";

export function SeccionCuenta() {
  const [claveActual, setClaveActual] = useState("");
  const [claveNueva, setClaveNueva] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  async function enviar(ev: FormEvent) {
    ev.preventDefault();
    setAviso(null);
    setGuardando(true);

    try {
      const resp = await cambiarClave(claveActual, claveNueva);
      if (resp.ok) {
        setAviso({ texto: "Contraseña actualizada.", tipo: "exito" });
        setClaveActual("");
        setClaveNueva("");
      } else if (resp.status === 401) {
        // 401 aqui significa "contraseña actual incorrecta", no sesion
        // caducada: cambiarClave() no redirige sola, a diferencia del resto.
        setAviso({ texto: "La contraseña actual no es correcta.", tipo: "error" });
      } else {
        setAviso({ texto: "No se pudo guardar. Inténtalo de nuevo.", tipo: "error" });
      }
    } catch {
      setAviso({ texto: "No se pudo conectar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Cambiar contraseña</h2>
        <form onSubmit={enviar}>
          <label htmlFor="actual">Contraseña actual</label>
          <input
            type="password"
            id="actual"
            autoComplete="current-password"
            required
            value={claveActual}
            onChange={(e) => setClaveActual(e.target.value)}
          />
          <label htmlFor="nueva">Contraseña nueva</label>
          <input
            type="password"
            id="nueva"
            autoComplete="new-password"
            minLength={8}
            required
            value={claveNueva}
            onChange={(e) => setClaveNueva(e.target.value)}
          />
          <button type="submit" className="primario" disabled={guardando}>
            Guardar
          </button>
          {aviso && <div className={`aviso visible ${aviso.tipo}`}>{aviso.texto}</div>}
        </form>
      </div>

      <div className="tarjeta">
        <button
          type="button"
          className="secundario"
          style={{ margin: 0, width: "100%" }}
          onClick={cerrarSesion}
        >
          Cerrar sesión
        </button>
      </div>
    </section>
  );
}
