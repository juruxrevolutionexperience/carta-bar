import { useEffect, useState, type FormEvent } from "react";

import { cargarQr, guardarTextoQr } from "./api";
import { HojaQR, type DatosQr } from "../shared/HojaQR";

export function SeccionQr() {
  const [datos, setDatos] = useState<DatosQr | null>(null);
  const [error, setError] = useState(false);
  const [texto, setTexto] = useState("");
  const [compacta, setCompacta] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<{ texto: string; tipo: "error" | "exito" } | null>(null);

  useEffect(() => {
    cargarQr()
      .then((cargados) => {
        setDatos(cargados);
        setTexto(cargados.texto);
      })
      .catch(() => setError(true));
  }, []);

  // Guardar un texto vacio es "volver al de por defecto": el servidor decide
  // cual es, asi que se vuelve a pedir en vez de repetirlo aqui.
  async function guardar(nuevo: string) {
    setAviso(null);
    setGuardando(true);
    try {
      const resp = await guardarTextoQr(nuevo);
      if (resp.status !== 204) throw new Error("fallo al guardar");
      const actualizados = await cargarQr();
      setDatos(actualizados);
      setTexto(actualizados.texto);
      setAviso({ texto: "Texto guardado.", tipo: "exito" });
    } catch {
      setAviso({ texto: "No se pudo guardar. Inténtalo de nuevo.", tipo: "error" });
    } finally {
      setGuardando(false);
    }
  }

  function enviar(ev: FormEvent) {
    ev.preventDefault();
    void guardar(texto);
  }

  if (error) return <section className="seccion">No se pudo cargar el QR.</section>;
  if (!datos) return <section className="seccion">Cargando…</section>;

  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Código QR de tu carta</h2>
        <p>
          Escanéalo con tu móvil para probar la carta, o imprime la hoja y ponla en las mesas.
        </p>
        <div className="rejilla-opciones" style={{ marginBottom: 14 }}>
          <label className="opcion">
            <input
              type="radio"
              name="tamano-qr"
              checked={!compacta}
              onChange={() => setCompacta(false)}
            />
            Hoja completa (nombre + QR + enlace)
          </label>
          <label className="opcion">
            <input
              type="radio"
              name="tamano-qr"
              checked={compacta}
              onChange={() => setCompacta(true)}
            />
            Tarjeta pequeña (para soporte de mesa)
          </label>
        </div>
        <HojaQR
          url={datos.url}
          nombre={datos.nombre}
          texto={texto.trim() || datos.texto}
          compacta={compacta}
        />
      </div>

      <div className="tarjeta">
        <h2>Texto de la hoja</h2>
        <form onSubmit={enviar}>
          <label htmlFor="texto-qr">Lo que se lee bajo el QR</label>
          <input
            type="text"
            id="texto-qr"
            maxLength={120}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
          />
          <button type="submit" className="primario" disabled={guardando}>
            Guardar
          </button>
          <button
            type="button"
            className="secundario"
            disabled={guardando}
            onClick={() => void guardar("")}
          >
            Volver al texto original
          </button>
          {aviso && <div className={`aviso visible ${aviso.tipo}`}>{aviso.texto}</div>}
        </form>
      </div>
    </section>
  );
}
