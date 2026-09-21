import { useEffect, useRef, useState, type FormEvent } from "react";

import { cambiarNombre, cargarMarca, quitarImagenMarca, subirImagenMarca } from "./api";
import { comprimirImagen } from "./comprimirImagen";
import type { ConfigMarca, TipoImagenMarca } from "./types";

interface BloqueProps {
  tipo: TipoImagenMarca;
  titulo: string;
  ayuda: string;
  url: string;
  claseMiniatura: string;
  anchoMax: number;
  onCambio: (url: string) => void;
}

function BloqueImagen({ tipo, titulo, ayuda, url, claseMiniatura, anchoMax, onCambio }: BloqueProps) {
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function subir() {
    const archivo = inputRef.current?.files?.[0];
    if (!archivo) return;
    setError(null);
    setOcupado(true);
    try {
      const blob = await comprimirImagen(archivo, anchoMax);
      const resp = await subirImagenMarca(tipo, blob);
      if (!resp.ok) throw new Error("fallo al subir");
      const datos = await resp.json();
      onCambio(datos.url);
    } catch {
      setError("No se pudo subir la imagen.");
    } finally {
      setOcupado(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function quitar() {
    setError(null);
    setOcupado(true);
    try {
      const resp = await quitarImagenMarca(tipo);
      if (resp.status !== 204) throw new Error("fallo al quitar");
      onCambio("");
    } catch {
      setError("No se pudo quitar la imagen.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="tarjeta">
      <h2>{titulo}</h2>
      <p>{ayuda}</p>
      <div className="bloque-foto">
        {url ? (
          <img className={`miniatura-foto ${claseMiniatura}`} src={url} alt="" />
        ) : (
          <div className={`miniatura-foto vacia ${claseMiniatura}`}>Sin imagen</div>
        )}
        <div className="acciones-foto">
          <label className="boton-archivo">
            {ocupado ? "Subiendo…" : url ? "Cambiar" : "Subir"}
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              disabled={ocupado}
              onChange={subir}
            />
          </label>
          {url && (
            <button type="button" onClick={quitar} disabled={ocupado}>
              Quitar
            </button>
          )}
          {error && <div className="aviso visible error">{error}</div>}
        </div>
      </div>
    </div>
  );
}

export function SeccionMarca() {
  const [marca, setMarca] = useState<ConfigMarca | null>(null);
  const [error, setError] = useState(false);
  const [nombre, setNombre] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  useEffect(() => {
    cargarMarca()
      .then((datos) => {
        setMarca(datos);
        setNombre(datos.nombre ?? "");
      })
      .catch(() => setError(true));
  }, []);

  async function guardarNombre(ev: FormEvent) {
    ev.preventDefault();
    setAviso(null);
    setGuardando(true);
    try {
      const resp = await cambiarNombre(nombre);
      if (resp.status === 204) {
        setAviso({ texto: "Nombre guardado.", tipo: "exito" });
      } else if (resp.status === 422) {
        setAviso({ texto: "El nombre debe tener entre 1 y 80 caracteres.", tipo: "error" });
      } else {
        setAviso({ texto: "No se pudo guardar. Inténtalo de nuevo.", tipo: "error" });
      }
    } catch {
      setAviso({ texto: "No se pudo conectar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  if (error) return <section className="seccion">No se pudo cargar la marca.</section>;
  if (!marca) return <section className="seccion">Cargando…</section>;

  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Nombre del negocio</h2>
        <form onSubmit={guardarNombre}>
          <label htmlFor="nombre-negocio">Nombre</label>
          <input
            type="text"
            id="nombre-negocio"
            maxLength={80}
            required
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
          <button type="submit" className="primario" disabled={guardando}>
            Guardar
          </button>
          {aviso && <div className={`aviso visible ${aviso.tipo}`}>{aviso.texto}</div>}
        </form>
      </div>

      <BloqueImagen
        tipo="logo"
        titulo="Logo"
        ayuda="Se ve en un círculo sobre la portada de la carta."
        url={marca.logo ?? ""}
        claseMiniatura="redonda"
        anchoMax={512}
        onCambio={(url) => setMarca((actual) => ({ ...actual, logo: url }))}
      />
      <BloqueImagen
        tipo="portada"
        titulo="Foto de portada"
        ayuda="La imagen grande de la parte de arriba de la carta."
        url={marca.foto_portada ?? ""}
        claseMiniatura="ancha"
        anchoMax={1600}
        onCambio={(url) => setMarca((actual) => ({ ...actual, foto_portada: url }))}
      />
    </section>
  );
}
