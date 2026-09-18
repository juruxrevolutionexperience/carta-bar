import { useState, type FormEvent } from "react";

import { crearRestaurante, type ResumenRestaurante } from "./api";

interface Props {
  onCreado: (restaurante: ResumenRestaurante) => void;
}

export function FormularioNuevoRestaurante({ onCreado }: Props) {
  const [restauranteId, setRestauranteId] = useState("");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  async function enviar(ev: FormEvent) {
    ev.preventDefault();
    setAviso(null);
    setGuardando(true);

    try {
      const resp = await crearRestaurante({ restaurante_id: restauranteId, nombre, clave });
      if (resp.status === 201) {
        const creado: ResumenRestaurante = await resp.json();
        onCreado(creado);
        setAviso({ texto: `Restaurante "${creado.nombre}" creado.`, tipo: "exito" });
        setRestauranteId("");
        setNombre("");
        setClave("");
        return;
      }
      if (resp.status === 409) {
        setAviso({ texto: "Ese subdominio ya está en uso.", tipo: "error" });
        return;
      }
      setAviso({
        texto: "Revisa los datos: el subdominio solo admite minúsculas, números y guiones.",
        tipo: "error",
      });
    } catch {
      setAviso({ texto: "No se pudo conectar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="panel-tarjeta">
      <h2>Añadir restaurante</h2>
      <p style={{ color: "var(--tinta-media)", fontSize: "13px" }}>
        Crea el acceso (subdominio y contraseña). Su carta hay que cargarla aparte.
      </p>
      <form onSubmit={enviar}>
        <label htmlFor="restaurante_id">Subdominio</label>
        <input
          id="restaurante_id"
          placeholder="bar2"
          pattern="[a-z0-9-]+"
          title="Solo minúsculas, números y guiones"
          required
          value={restauranteId}
          onChange={(e) => setRestauranteId(e.target.value)}
        />
        <label htmlFor="nombre">Nombre</label>
        <input
          id="nombre"
          placeholder="Bar Pepe"
          required
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <label htmlFor="clave">Contraseña inicial</label>
        <input
          id="clave"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={clave}
          onChange={(e) => setClave(e.target.value)}
        />
        <div style={{ marginTop: "16px" }}>
          <button type="submit" disabled={guardando}>
            Crear restaurante
          </button>
        </div>
        {aviso && <div className={`aviso ${aviso.tipo}`}>{aviso.texto}</div>}
      </form>
    </div>
  );
}
