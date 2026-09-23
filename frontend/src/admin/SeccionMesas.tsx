import { useEffect, useRef, useState } from "react";

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
import {
  DISENO,
  FORMAS,
  huecoLibre,
  limitarZoom,
  siguienteNombre,
  zoomQueCabe,
  type FormaMesa,
} from "./planoUtil";
import { HerramientasPlano } from "./HerramientasPlano";
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
  const [zoom, setZoom] = useState(1);
  // Con el plano bloqueado se puede tocar una mesa para ver sus datos, pero no
  // moverla sin querer. Es lo normal una vez el plano ya está montado.
  const [bloqueado, setBloqueado] = useState(false);
  const caja = useRef<HTMLDivElement>(null);

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

  function ajustar() {
    const marco = caja.current?.querySelector(".plano-scroll");
    if (!(marco instanceof HTMLElement)) return;
    // El alto del hueco lo fija la hoja de estilos (max-height); se lee de ahi
    // para no repetir el valor en dos sitios.
    const alto = parseFloat(getComputedStyle(marco).maxHeight);
    if (marco.clientWidth && alto) setZoom(zoomQueCabe(marco.clientWidth, alto));
  }

  // Al abrir, el plano entero a la vista: es lo primero que quiere ver el
  // gerente, y en un móvil a tamaño real solo se vería un tercio.
  useEffect(() => {
    if (zonas) ajustar();
    // Solo al cargar: después manda el zoom que elija el gerente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zonas !== null]);

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
      <div className="selector-vista" role="radiogroup" aria-label="Vista de las mesas">
        <label>
          <input
            type="radio"
            name="vista-mesas"
            checked={vista === "plano"}
            onChange={() => setVista("plano")}
          />
          Plano
        </label>
        <label>
          <input
            type="radio"
            name="vista-mesas"
            checked={vista === "lista"}
            onChange={() => setVista("lista")}
          />
          Lista de QR
        </label>
      </div>
      {aviso && <div className="aviso visible error">{aviso}</div>}

      {vista === "plano" && (
        <>
          <div className="fila-zonas">
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
                <span className="ocupacion">{mesas.filter((m) => m.zona_id === z.id).length}</span>
              </button>
            ))}
            </div>
            <button
              type="button"
              className={"boton-zonas" + (gestionando ? " activa" : "")}
              aria-label="Gestionar las zonas del local"
              aria-pressed={gestionando}
              onClick={() => setGestionando((g) => !g)}
            >
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="3.2" />
                <path d="M19.4 15a1.6 1.6 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.6 1.6 0 00-1.8-.3 1.6 1.6 0 00-1 1.5V21a2 2 0 11-4 0v-.1A1.6 1.6 0 007 19.4a1.6 1.6 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.6 1.6 0 00.3-1.8 1.6 1.6 0 00-1.5-1H1a2 2 0 110-4h.1A1.6 1.6 0 002.6 7a1.6 1.6 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.6 1.6 0 001.8.3H7a1.6 1.6 0 001-1.5V1a2 2 0 114 0v.1a1.6 1.6 0 001 1.5 1.6 1.6 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.6 1.6 0 00-.3 1.8V7a1.6 1.6 0 001.5 1H21a2 2 0 110 4h-.1a1.6 1.6 0 00-1.5 1z" />
              </svg>
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
            <p className="ayuda">Pulsa una forma para añadirla. Arrástrala para colocarla.</p>
            <div className="paleta-formas">
              {FORMAS.map((f) => (
                <button
                  key={f}
                  type="button"
                  className="pieza"
                  disabled={ocupado || !zonaId || bloqueado}
                  onClick={() => anadirMesa(f)}
                >
                  <span className={`icono-forma forma-${f}`} aria-hidden="true">
                    <i />
                  </span>
                  {DISENO[f].etiqueta}
                </button>
              ))}
            </div>

            <div className="lienzo" ref={caja}>
              <PlanoZona
                mesas={mesasDeLaZona}
                seleccionada={seleccionada}
                zoom={zoom}
                bloqueado={bloqueado}
                onSeleccionar={setSeleccionada}
                onCambio={(mesa, cambios) => void cambiarMesa(mesa, cambios)}
              />
              <HerramientasPlano
                zoom={zoom}
                bloqueado={bloqueado}
                onZoom={(z) => setZoom(limitarZoom(z))}
                onAjustar={ajustar}
                onBloquear={() => setBloqueado((b) => !b)}
              />
            </div>

            {mesasDeLaZona.length === 0 && (
              <p className="cargando">
                Esta zona aún no tiene mesas: pulsa una forma para empezar.
              </p>
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
            <div className="selector-vista" role="radiogroup" aria-label="Tamaño del QR">
              <label>
                <input
                  type="radio"
                  name="tamano-mesa"
                  checked={compacta}
                  onChange={() => setCompacta(true)}
                />
                Tarjeta pequeña
              </label>
              <label>
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
