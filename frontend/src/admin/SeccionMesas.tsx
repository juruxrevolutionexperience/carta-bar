import { useEffect, useState, type FormEvent } from "react";

import { HojaQR, type DatosQr } from "../shared/HojaQR";
import { cargarMesas, cargarQr, crearMesa, regenerarQrMesa, type Mesa } from "./api";

// La direccion que lleva el QR de una mesa: la de la carta del restaurante
// mas el token secreto de esa mesa. La carta aun no lo lee (llega con el
// siguiente bloque: proponer platos); hasta entonces abre la carta normal.
function urlDeMesa(base: string, token: string): string {
  const url = new URL(base);
  url.searchParams.set("mesa", token);
  return url.toString();
}

export function SeccionMesas() {
  const [mesas, setMesas] = useState<Mesa[] | null>(null);
  const [qr, setQr] = useState<DatosQr | null>(null);
  const [error, setError] = useState(false);
  const [nombre, setNombre] = useState("");
  const [compacta, setCompacta] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([cargarMesas(), cargarQr()])
      .then(([mesasCargadas, datosQr]) => {
        setMesas(mesasCargadas);
        setQr(datosQr);
      })
      .catch(() => setError(true));
  }, []);

  async function anadir(ev: FormEvent) {
    ev.preventDefault();
    const limpio = nombre.trim();
    if (!limpio) return;
    setAviso(null);
    setOcupado(true);
    try {
      const resp = await crearMesa(limpio);
      if (resp.status !== 201) throw new Error("no se creó");
      const creada: Mesa = await resp.json();
      setMesas((actual) => [...(actual ?? []), creada]);
      setNombre("");
    } catch {
      setAviso("No se pudo crear la mesa. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  }

  async function regenerar(mesa: Mesa) {
    const ok = window.confirm(
      `¿Cambiar el QR de "${mesa.nombre}"? El QR que ya tengas impreso dejará de funcionar.`
    );
    if (!ok) return;
    setAviso(null);
    setOcupado(true);
    try {
      const resp = await regenerarQrMesa(mesa.id);
      if (resp.status !== 200) throw new Error("no se regeneró");
      const nueva: Mesa = await resp.json();
      setMesas((actual) => actual?.map((m) => (m.id === nueva.id ? nueva : m)) ?? actual);
    } catch {
      setAviso("No se pudo cambiar el QR. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  }

  if (error) return <section className="seccion">No se pudieron cargar las mesas.</section>;
  if (!mesas || !qr) return <section className="seccion">Cargando…</section>;

  return (
    <section className="seccion">
      <div className="tarjeta">
        <h2>Mesas</h2>
        <p>Cada mesa tiene su propio QR. Imprímelo y déjalo en esa mesa.</p>

        <form className="form-mesa-nueva" onSubmit={anadir}>
          <input
            value={nombre}
            maxLength={60}
            placeholder="Nombre de la mesa (ej. Terraza 3)"
            aria-label="Nombre de la nueva mesa"
            onChange={(e) => setNombre(e.target.value)}
          />
          <button type="submit" className="primario" disabled={ocupado || !nombre.trim()}>
            Añadir
          </button>
        </form>
        {aviso && <div className="aviso visible error">{aviso}</div>}

        {mesas.length === 0 && <p className="cargando">Todavía no hay mesas.</p>}

        {mesas.length > 0 && (
          <div className="rejilla-opciones" style={{ marginTop: 14 }}>
            <label className="opcion">
              <input type="radio" name="tamano-mesa" checked={compacta} onChange={() => setCompacta(true)} />
              Tarjeta pequeña (soporte de mesa)
            </label>
            <label className="opcion">
              <input type="radio" name="tamano-mesa" checked={!compacta} onChange={() => setCompacta(false)} />
              Hoja completa
            </label>
          </div>
        )}

        {mesas.map((mesa) => (
          <details className="mesa-qr" key={mesa.id}>
            <summary>{mesa.nombre}</summary>
            <div className="mesa-qr-cuerpo">
              <HojaQR
                url={urlDeMesa(qr.url, mesa.token_qr)}
                nombre={mesa.nombre}
                texto={qr.texto}
                compacta={compacta}
              />
              <button
                type="button"
                className="secundario"
                disabled={ocupado}
                onClick={() => void regenerar(mesa)}
              >
                Cambiar el QR de esta mesa
              </button>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
