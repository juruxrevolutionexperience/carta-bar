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
  CELDA,
  FILAS,
  TIPOS,
  ZOOM_MOVIL,
  corregirSiSeSale,
  huecoLibre,
  limitarZoom,
  nombreParaForma,
  zoomQueCabe,
  type TipoMesa,
} from "./planoUtil";
import { HerramientasPlano } from "./HerramientasPlano";
import { QrMesa } from "./QrMesa";

type Vista = "plano" | "lista";
// Como en un TPV: el ojo es el modo de servicio (ver el local y quién está
// sentado, sin poder mover nada) y el lápiz el de edición (montar el plano).
type Modo = "servicio" | "edicion";

// Cada cuánto se mira qué mesas tienen clientes. Poco: es un vistazo, no un
// tiempo real (eso llega con las comandas).
const REFRESCO_OCUPACION_MS = 8000;

export function SeccionMesas() {
  const [zonas, setZonas] = useState<Zona[] | null>(null);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [qr, setQr] = useState<DatosQr | null>(null);
  const [error, setError] = useState(false);
  const [vista, setVista] = useState<Vista>("plano");
  const [zonaActiva, setZonaActiva] = useState<string | null>(null);
  const [seleccionada, setSeleccionada] = useState<string | null>(null);
  // En el móvil los datos de la mesa suben como una hoja que tapa el plano. Solo
  // se abre a propósito (en servicio, al tocar; al editar, con un segundo toque
  // o el botón "Datos"): si saltara al tocar, no se podría arrastrar una mesa.
  // En pantalla grande el panel es una columna fija y esto no influye.
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [gestionando, setGestionando] = useState(false);
  const [compacta, setCompacta] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [modo, setModo] = useState<Modo>("servicio");
  const editando = modo === "edicion";
  const primeraCarga = useRef(true);
  const caja = useRef<HTMLDivElement>(null);

  function recargar() {
    Promise.all([cargarZonas(), cargarMesas(), cargarQr()])
      .then(([zonasCargadas, mesasCargadas, datosQr]) => {
        setZonas(zonasCargadas);
        setMesas(mesasCargadas);
        // Un local sin mesas se abre montándolo; uno ya montado, para verlo.
        if (primeraCarga.current) {
          primeraCarga.current = false;
          setModo(mesasCargadas.length === 0 ? "edicion" : "servicio");
        }
        // Una mesa guardada fuera de los límites del plano no se podría tocar:
        // se trae dentro y se guarda la corrección.
        for (const m of mesasCargadas) {
          const arreglada = corregirSiSeSale(m);
          if (arreglada) void cambiarMesa(m, arreglada);
        }
        setQr(datosQr);
        setZonaActiva((actual) =>
          zonasCargadas.some((z) => z.id === actual) ? actual : (zonasCargadas[0]?.id ?? null)
        );
        setSeleccionada(null);
      })
      .catch(() => setError(true));
  }

  useEffect(recargar, []);

  // Las mesas con clientes se ponen en rojo. Solo se actualiza ese dato: lo que
  // se esté moviendo en el plano no se toca.
  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.hidden || vista !== "plano") return;
      cargarMesas()
        .then((nuevas) => {
          const ocupadas = new Map(nuevas.map((m) => [m.id, m.ocupada === true]));
          setMesas((actual) =>
            actual.map((m) => (ocupadas.has(m.id) ? { ...m, ocupada: ocupadas.get(m.id) } : m))
          );
        })
        .catch(() => undefined);
    }, REFRESCO_OCUPACION_MS);
    return () => window.clearInterval(id);
  }, [vista]);

  // Cómo se ajusta el zoom solo (al abrir y al cambiar el tamaño de la
  // pantalla): "legible" (en el móvil, mesas que se leen y el plano centrado en
  // ellas; en pantalla grande, el local entero), "todo" (el local entero, tras
  // pulsar "ver todo") o "manual" (el gerente acercó o alejó: se respeta).
  const ajuste = useRef<"legible" | "todo" | "manual">("legible");
  const [centrar, setCentrar] = useState(0);
  const zoomActual = useRef(zoom);
  zoomActual.current = zoom;
  const ultimaMedida = useRef("");

  function ajustar(forzar = false) {
    const marco = caja.current?.querySelector(".plano-scroll");
    if (!(marco instanceof HTMLElement)) return;
    // El alto del hueco lo fija la hoja de estilos (max-height); se lee de ahi
    // para no repetir el valor en dos sitios.
    // Se mide en JS: algunos navegadores de móvil no resuelven max() en el
    // valor calculado.
    const tope = parseFloat(getComputedStyle(marco).maxHeight);
    const libre =
      (window.visualViewport?.height ?? window.innerHeight) -
      marco.getBoundingClientRect().top -
      24;
    const alto = Number.isFinite(tope) ? tope : Math.max(260, Math.floor(libre));
    const ancho = marco.clientWidth;
    if (!ancho || !alto) return;
    // Solo si cambió la pantalla: el lienzo también cambia de alto con el zoom,
    // y sin esto cada ajuste dispararía otro y el plano volvería al centro.
    const medida = `${ancho}x${alto}x${ajuste.current}`;
    if (!forzar && medida === ultimaMedida.current) return;
    ultimaMedida.current = medida;

    const cabe = zoomQueCabe(ancho, alto);
    const movil = window.matchMedia("(max-width: 999px)").matches;
    let nuevo = cabe;
    if (movil && ajuste.current === "legible") {
      // Que el plano llene el alto libre, con las mesas legibles; lo que no
      // quepa a lo ancho se recorre con el dedo.
      const llenaAlto = Math.floor((alto / (FILAS * CELDA)) * 100) / 100;
      nuevo = limitarZoom(Math.max(cabe, Math.min(llenaAlto, ZOOM_MOVIL)));
    }
    if (forzar || Math.abs(nuevo - zoomActual.current) > 0.001) {
      setZoom(nuevo);
      setCentrar((c) => c + 1);
    }
  }

  // En una pantalla grande no hay botones de zoom (como en un TPV: el local
  // cabe siempre), asi que el plano se reajusta solo al cambiar el tamaño de la
  // ventana o al girar el móvil.
  useEffect(() => {
    const lienzo = caja.current;
    if (!lienzo || typeof ResizeObserver === "undefined") return;
    const observador = new ResizeObserver(() => {
      if (ajuste.current !== "manual") ajustar();
    });
    observador.observe(lienzo);
    return () => observador.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zonas !== null, vista]);

  // Al abrir: en pantalla grande el local entero; en el móvil, legible.
  useEffect(() => {
    if (zonas) ajustar(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zonas !== null]);

  function zoomDelGerente(z: number) {
    ajuste.current = "manual";
    setZoom(limitarZoom(z));
  }

  function verTodo() {
    ajuste.current = "todo";
    ajustar(true);
  }

  const herramientas = (
    <HerramientasPlano zoom={zoom} onZoom={zoomDelGerente} onAjustar={verTodo} />
  );

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
      // La respuesta de guardar no trae la ocupación: se conserva la que había.
      setMesas((actual) =>
        actual.map((m) => (m.id === guardada.id ? { ...guardada, ocupada: m.ocupada } : m))
      );
    } catch {
      deshacer();
      if (cambios.zona_id) setZonaActiva(mesa.zona_id);
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    }
  }

  function anadirMesa(tipo: TipoMesa) {
    if (!zonaId) return;
    const { x, y } = huecoLibre(mesasDeLaZona, tipo.ancho, tipo.alto);
    void ejecutar(async () => {
      const resp = await crearMesa({
        nombre: nombreParaForma(tipo.forma, mesas.map((m) => m.nombre)),
        zona_id: zonaId,
        forma: tipo.forma,
        x,
        y,
        ancho: tipo.ancho,
        alto: tipo.alto,
        capacidad: tipo.capacidad,
      });
      if (resp.status !== 201) {
        setAviso("No se pudo crear la mesa. Inténtalo de nuevo.");
        return;
      }
      const creada: Mesa = await resp.json();
      setMesas((actual) => [...actual, creada]);
      setSeleccionada(creada.id);
      setPanelAbierto(false);
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
                <span className="ocupacion">
                  {mesas.filter((m) => m.zona_id === z.id && m.ocupada).length}/
                  {mesas.filter((m) => m.zona_id === z.id).length}
                </span>
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

          <div className="zona-trabajo">
            <div className="tarjeta tarjeta-plano">
              <div className="barra-plano">
                <div className="selector-modo" role="radiogroup" aria-label="Modo del plano">
                  <button
                    type="button"
                    role="radio"
                    aria-checked={!editando}
                    aria-label="Ver el local"
                    title="Ver el local"
                    className={"boton-modo" + (!editando ? " activo" : "")}
                    onClick={() => setModo("servicio")}
                  >
                    <svg viewBox="0 0 24 24">
                      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    role="radio"
                    aria-checked={editando}
                    aria-label="Editar el plano"
                    title="Editar el plano"
                    className={"boton-modo" + (editando ? " activo" : "")}
                    onClick={() => {
                      setModo("edicion");
                      setSeleccionada(null);
                    }}
                  >
                    <svg viewBox="0 0 24 24">
                      <path d="M4 20h4L19 9a2.1 2.1 0 00-3-3L5 17z" />
                      <path d="M14 7l3 3" />
                    </svg>
                  </button>
                </div>

                {/* Solo al editar: las formas para añadir, en una barra pegada al plano. */}
                {editando && (
                  <div className="paleta-formas" aria-label="Añadir una mesa">
                    {TIPOS.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        className="pieza"
                        title={`Añadir mesa ${t.etiqueta.toLowerCase()}`}
                        disabled={ocupado || !zonaId}
                        onClick={() => anadirMesa(t)}
                      >
                        <span className={`icono-forma forma-${t.forma}`} aria-hidden="true">
                          <i />
                        </span>
                        {t.etiqueta}
                      </button>
                    ))}
                  </div>
                )}

                {/* El zoom va siempre en esta fila: sobre el plano taparía mesas.
                    (En pantalla grande no se muestra.) */}
                {herramientas}
              </div>

              <div className="lienzo" ref={caja}>
                <PlanoZona
                  mesas={mesasDeLaZona}
                  seleccionada={seleccionada}
                  zoom={zoom}
                  editando={editando}
                  onSeleccionar={(id) => {
                    // Otra mesa (o ninguna): la hoja de datos se cierra. En
                    // servicio, tocar una mesa la abre; al editar, no.
                    if (id !== seleccionada) setPanelAbierto(id !== null && !editando);
                    setSeleccionada(id);
                  }}
                  onToque={(_, yaElegida) => {
                    if (yaElegida) setPanelAbierto(true);
                  }}
                  centrar={centrar}
                  onZoom={zoomDelGerente}
                  onCambio={(mesa, cambios) => void cambiarMesa(mesa, cambios)}
                />
                {editando && mesaElegida && !panelAbierto && (
                  <button
                    type="button"
                    className="boton-datos-mesa"
                    onClick={() => setPanelAbierto(true)}
                  >
                    Datos de «{mesaElegida.nombre}»
                  </button>
                )}
              </div>
              <p className="aviso-girar">Gira el móvil para ver el local más grande.</p>

              {mesasDeLaZona.length === 0 && (
                <p className="cargando">
                  {editando
                    ? "Esta zona aún no tiene mesas: pulsa un tipo de mesa para añadirla y arrástrala."
                    : "Esta zona aún no tiene mesas. Pulsa el lápiz para montarla."}
                </p>
              )}
            </div>

            {!mesaElegida && (
              <div className="tarjeta panel-vacio">
                <h3>{zonas.find((z) => z.id === zonaId)?.nombre}</h3>
                <p className="resumen-zona">
                  <span className="cifra">{mesasDeLaZona.filter((m) => m.ocupada).length}</span>
                  con clientes
                  <span className="cifra">{mesasDeLaZona.filter((m) => !m.ocupada).length}</span>
                  libres
                </p>
                <p className="leyenda-plano">
                  <span className="punto-ocupada" /> Mesa con clientes
                </p>
                <p>Toca una mesa del plano para ver sus datos y su QR.</p>
              </div>
            )}
            {mesaElegida && (
              <PanelMesa
                key={mesaElegida.id}
                mesa={mesaElegida}
                zonas={zonas}
                qr={qr}
                editando={editando}
                abiertoEnMovil={panelAbierto}
                ocupado={ocupado}
                onCambio={(cambios) => void cambiarMesa(mesaElegida, cambios)}
                onEliminar={eliminarElegida}
                onCerrar={() => {
                  setSeleccionada(null);
                  setPanelAbierto(false);
                }}
                onRegenerar={regenerar}
              />
            )}
          </div>
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
