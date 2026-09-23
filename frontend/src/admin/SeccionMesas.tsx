import { useEffect, useState } from "react";

import type { DatosQr } from "../shared/HojaQR";
import {
  actualizarMesa,
  cargarMesas,
  cargarQr,
  cargarZonas,
  crearMesa,
  eliminarMesa,
  regenerarQrMesa,
  type CambiosMesa,
  type Mesa,
  type Zona,
} from "./api";
import { OrganizarZonas } from "./OrganizarZonas";
import { PanelMesa } from "./PanelMesa";
import { PlanoZona } from "./PlanoZona";
import { DISENO, FORMAS, huecoLibre, siguienteNombre, type FormaMesa } from "./planoUtil";
import { QrMesa } from "./QrMesa";

type Vista = "plano" | "lista";

export function SeccionMesas() {
  const [zonas, setZonas] = useState<Zona[] | null>(null);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [qr, setQr] = useState<DatosQr | null>(null);
  const [error, setError] = useState(false);
  const [vista, setVista] = useState<Vista>("plano");
  const [zonaActiva, setZonaActiva] = useState<string | null>(null);
  const [seleccionada, setSeleccionada] = useState<string | null>(null);
  const [gestionando, setGestionando] = useState(false);
  const [compacta, setCompacta] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  function recargar() {
    Promise.all([cargarZonas(), cargarMesas(), cargarQr()])
      .then(([zonasCargadas, mesasCargadas, datosQr]) => {
        setZonas(zonasCargadas);
        setMesas(mesasCargadas);
        setQr(datosQr);
        setZonaActiva((actual) =>
          zonasCargadas.some((z) => z.id === actual) ? actual : (zonasCargadas[0]?.id ?? null)
        );
        setSeleccionada(null);
      })
      .catch(() => setError(true));
  }

  useEffect(recargar, []);

  if (error) return <section className="seccion">No se pudieron cargar las mesas.</section>;
  if (!zonas || !qr) return <section className="seccion">Cargando…</section>;

  const zonaId = zonas.some((z) => z.id === zonaActiva) ? zonaActiva : (zonas[0]?.id ?? null);
  const mesasDeLaZona = mesas.filter((m) => m.zona_id === zonaId);
  const mesaElegida = mesas.find((m) => m.id === seleccionada) ?? null;

  async function ejecutar(accion: () => Promise<void>) {
    setAviso(null);
    setOcupado(true);
    try {
      await accion();
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setOcupado(false);
    }
  }

  // Se ve el cambio al instante (mover con el dedo tiene que ser fluido) y se
  // deshace si el servidor lo rechaza.
  async function cambiarMesa(mesa: Mesa, cambios: CambiosMesa) {
    setAviso(null);
    setMesas((actual) => actual.map((m) => (m.id === mesa.id ? { ...m, ...cambios } : m)));
    if (cambios.zona_id) setZonaActiva(cambios.zona_id);
    const deshacer = () => setMesas((actual) => actual.map((m) => (m.id === mesa.id ? mesa : m)));
    try {
      const resp = await actualizarMesa(mesa.id, cambios);
      if (!resp.ok) {
        deshacer();
        if (cambios.zona_id) setZonaActiva(mesa.zona_id);
        setAviso("No se pudo guardar el cambio.");
        return;
      }
      const guardada: Mesa = await resp.json();
      setMesas((actual) => actual.map((m) => (m.id === guardada.id ? guardada : m)));
    } catch {
      deshacer();
      if (cambios.zona_id) setZonaActiva(mesa.zona_id);
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    }
  }

  function anadirMesa(forma: FormaMesa) {
    if (!zonaId) return;
    const d = DISENO[forma];
    const { x, y } = huecoLibre(mesasDeLaZona, d.ancho, d.alto);
    void ejecutar(async () => {
      const resp = await crearMesa({
        nombre: siguienteNombre(mesas.map((m) => m.nombre)),
        zona_id: zonaId,
        forma,
        x,
        y,
        ancho: d.ancho,
        alto: d.alto,
        capacidad: d.capacidad,
      });
      if (resp.status !== 201) {
        setAviso("No se pudo crear la mesa. Inténtalo de nuevo.");
        return;
      }
      const creada: Mesa = await resp.json();
      setMesas((actual) => [...actual, creada]);
      setSeleccionada(creada.id);
    });
  }

  function eliminarElegida() {
    if (!mesaElegida) return;
    if (!window.confirm(`¿Eliminar "${mesaElegida.nombre}"? Su QR dejará de funcionar.`)) return;
    void ejecutar(async () => {
      const resp = await eliminarMesa(mesaElegida.id);
      if (resp.status === 204 || resp.status === 404) {
        setMesas((actual) => actual.filter((m) => m.id !== mesaElegida.id));
        setSeleccionada(null);
      } else if (resp.status === 409) {
        setAviso("Hay clientes sentados en esta mesa: espera a que se cierre.");
      } else {
        setAviso("No se pudo eliminar. Inténtalo de nuevo.");
      }
    });
  }

  function regenerar(mesa: Mesa) {
    const ok = window.confirm(
      `¿Cambiar el QR de "${mesa.nombre}"? El QR que ya tengas impreso dejará de funcionar.`
    );
    if (!ok) return;
    void ejecutar(async () => {
      const resp = await regenerarQrMesa(mesa.id);
      if (resp.status !== 200) {
        setAviso("No se pudo cambiar el QR. Inténtalo de nuevo.");
        return;
      }
      const nueva: Mesa = await resp.json();
      setMesas((actual) => actual.map((m) => (m.id === nueva.id ? nueva : m)));
    });
  }

  return (
    <section className="seccion">
      <div className="tarjeta">
        <div className="cabecera-seccion">
          <h2>Mesas</h2>
          <div className="rejilla-opciones">
            <label className="opcion">
              <input
                type="radio"
                name="vista-mesas"
                checked={vista === "plano"}
                onChange={() => setVista("plano")}
              />
              Plano
            </label>
            <label className="opcion">
              <input
                type="radio"
                name="vista-mesas"
                checked={vista === "lista"}
                onChange={() => setVista("lista")}
              />
              Lista de QR
            </label>
          </div>
        </div>
        {aviso && <div className="aviso visible error">{aviso}</div>}
      </div>

      {vista === "plano" && (
        <>
          <div className="pestanas-zona" role="tablist">
            {zonas.map((z) => (
              <button
                key={z.id}
                type="button"
                role="tab"
                aria-selected={z.id === zonaId}
                className={"pestana-zona" + (z.id === zonaId ? " activa" : "")}
                onClick={() => {
                  setZonaActiva(z.id);
                  setSeleccionada(null);
                }}
              >
                {z.nombre}
              </button>
            ))}
            <button
              type="button"
              className={"pestana-zona gestionar" + (gestionando ? " activa" : "")}
              onClick={() => setGestionando((g) => !g)}
            >
              ⚙ Zonas
            </button>
          </div>

          {gestionando && (
            <OrganizarZonas
              zonas={zonas}
              mesas={mesas}
              onCambio={setZonas}
              onRecargar={recargar}
            />
          )}

          <div className="tarjeta">
            <p className="ayuda">Pulsa una forma para añadir una mesa. Arrástrala para colocarla.</p>
            <div className="paleta-formas">
              {FORMAS.map((f) => (
                <button
                  key={f}
                  type="button"
                  className="secundario"
                  disabled={ocupado || !zonaId}
                  onClick={() => anadirMesa(f)}
                >
                  <span className={`icono-forma forma-${f}`} aria-hidden="true" />
                  {DISENO[f].etiqueta}
                </button>
              ))}
            </div>

            <PlanoZona
              mesas={mesasDeLaZona}
              seleccionada={seleccionada}
              onSeleccionar={setSeleccionada}
              onCambio={(mesa, cambios) => void cambiarMesa(mesa, cambios)}
            />
            {mesasDeLaZona.length === 0 && (
              <p className="cargando">Esta zona aún no tiene mesas: pulsa una forma para empezar.</p>
            )}
          </div>

          {mesaElegida && (
            <PanelMesa
              key={mesaElegida.id}
              mesa={mesaElegida}
              zonas={zonas}
              qr={qr}
              ocupado={ocupado}
              onCambio={(cambios) => void cambiarMesa(mesaElegida, cambios)}
              onEliminar={eliminarElegida}
              onRegenerar={regenerar}
            />
          )}
        </>
      )}

      {vista === "lista" && (
        <div className="tarjeta">
          <p>Cada mesa tiene su propio QR. Imprímelo y déjalo en esa mesa.</p>
          {mesas.length === 0 && <p className="cargando">Todavía no hay mesas.</p>}
          {mesas.length > 0 && (
            <div className="rejilla-opciones" style={{ marginBottom: 12 }}>
              <label className="opcion">
                <input
                  type="radio"
                  name="tamano-mesa"
                  checked={compacta}
                  onChange={() => setCompacta(true)}
                />
                Tarjeta pequeña (soporte de mesa)
              </label>
              <label className="opcion">
                <input
                  type="radio"
                  name="tamano-mesa"
                  checked={!compacta}
                  onChange={() => setCompacta(false)}
                />
                Hoja completa
              </label>
            </div>
          )}
          {zonas.map((z) => {
            const deLaZona = mesas.filter((m) => m.zona_id === z.id);
            if (deLaZona.length === 0) return null;
            return (
              <div key={z.id}>
                <h3 className="titulo-zona-lista">{z.nombre}</h3>
                {deLaZona.map((m) => (
                  <details className="mesa-qr" key={m.id}>
                    <summary>{m.nombre}</summary>
                    <QrMesa
                      mesa={m}
                      qr={qr}
                      compacta={compacta}
                      ocupado={ocupado}
                      onRegenerar={regenerar}
                    />
                  </details>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
