import { useEffect, useState } from "react";

import {
  abrirMesa,
  cargarSesionMesa,
  confirmarMesa,
  expulsarComensal,
  liberarMesa,
  type Mesa,
  type SesionConComensales,
} from "./api";
import { TEXTO_ESTADO, estadoDe, personas, tiempoDesde } from "./servicioUtil";

interface Props {
  mesa: Mesa;
  ahora: number;
  // Tras cada acción: la pantalla vuelve a pedir las mesas para pintar el estado.
  onCambio: () => void;
  onCerrar: () => void;
}

const MAX_COMENSALES = 50;

// Lo que el camarero hace con una mesa durante el servicio: abrirla, aceptar la
// que abrió un cliente, liberarla y quitar a alguien que no debería estar. Se
// monta con key={mesa.id}: al tocar otra mesa arranca limpio.
export function PanelServicio({ mesa, ahora, onCambio, onCerrar }: Props) {
  const estado = estadoDe(mesa);
  const [datos, setDatos] = useState<SesionConComensales | null>(null);
  const [comensales, setComensales] = useState(Math.min(mesa.capacidad, MAX_COMENSALES));
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  // Se vuelve a pedir cuando el listado dice que algo cambió (alguien entró,
  // la aceptaron, caducó...), no en cada refresco.
  useEffect(() => {
    if (estado === "libre") {
      setDatos(null);
      return;
    }
    let vigente = true;
    cargarSesionMesa(mesa.id)
      .then((d) => vigente && setDatos(d))
      .catch(() => vigente && setAviso("No se pudo cargar quién está en la mesa."));
    return () => {
      vigente = false;
    };
  }, [mesa.id, estado, mesa.comensales]);

  async function hacer(accion: () => Promise<Response>) {
    setOcupado(true);
    setAviso(null);
    try {
      const resp = await accion();
      if (!resp.ok) {
        setAviso((await resp.text()) || "No se pudo hacer. Inténtalo otra vez.");
      }
    } catch {
      setAviso("Sin conexión. Inténtalo otra vez.");
    } finally {
      setOcupado(false);
      onCambio();
    }
  }

  function liberar() {
    const texto =
      estado === "por_confirmar"
        ? `¿Liberar "${mesa.nombre}"? Si nadie está sentado ahí, es lo correcto.`
        : `¿Liberar "${mesa.nombre}"? Los clientes perderán la mesa en su móvil.`;
    if (!window.confirm(texto)) return;
    void hacer(() => liberarMesa(mesa.id));
  }

  function quitar(id: string, nombre: string) {
    if (!window.confirm(`¿Quitar a ${nombre} de la mesa? Ya no podrá pedir desde su móvil.`)) {
      return;
    }
    void hacer(() => expulsarComensal(id));
  }

  const dentro = datos?.comensales.filter((c) => c.expulsado_en === null) ?? [];
  const declarados = datos?.sesion.comensales_declarados ?? null;
  const tiempo = tiempoDesde(mesa.abierta_en, ahora);

  return (
    <div className="tarjeta panel-mesa panel-servicio">
      <div className="cabecera-panel">
        <h3>{mesa.nombre}</h3>
        <button type="button" className="cerrar-panel" aria-label="Cerrar" onClick={onCerrar}>
          <svg viewBox="0 0 24 24">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>

      <p className={"estado-servicio estado-" + estado}>
        {TEXTO_ESTADO[estado]}
        {tiempo && ` · ${tiempo}`}
      </p>

      {estado === "libre" && (
        <>
          <p className="explicacion">
            Ábrela si se sienta alguien sin usar el QR. Si no, el primero que lo escanee la abrirá
            y te saldrá aquí para aceptarla.
          </p>
          <label>Comensales</label>
          <div className="contador-comensales">
            <button
              type="button"
              aria-label="Uno menos"
              disabled={comensales <= 1}
              onClick={() => setComensales((n) => Math.max(1, n - 1))}
            >
              −
            </button>
            <span>{comensales}</span>
            <button
              type="button"
              aria-label="Uno más"
              disabled={comensales >= MAX_COMENSALES}
              onClick={() => setComensales((n) => Math.min(MAX_COMENSALES, n + 1))}
            >
              +
            </button>
          </div>
          <button
            type="button"
            className="primario boton-servicio"
            disabled={ocupado}
            onClick={() => void hacer(() => abrirMesa(mesa.id, comensales))}
          >
            Abrir mesa
          </button>
        </>
      )}

      {estado === "por_confirmar" && (
        <>
          <p className="explicacion">
            Un cliente la ha abierto con el QR. Sal a la mesa y, si de verdad están ahí, acéptala:
            hasta entonces no llega nada a cocina.
          </p>
          <button
            type="button"
            className="primario boton-servicio"
            disabled={ocupado}
            onClick={() => void hacer(() => confirmarMesa(mesa.id))}
          >
            Aceptar mesa
          </button>
        </>
      )}

      {estado !== "libre" && (
        <>
          <h4 className="titulo-comensales">
            En la mesa
            {declarados !== null && <span> · dijeron {personas(declarados)}</span>}
          </h4>
          {datos === null ? (
            <p className="explicacion">Cargando…</p>
          ) : dentro.length === 0 ? (
            <p className="explicacion">Nadie ha escaneado el QR todavía.</p>
          ) : (
            <ul className="lista-comensales">
              {dentro.map((c) => (
                <li key={c.id}>
                  <span className="nombre-comensal">{c.nombre}</span>
                  {c.rol === "anfitrion" && <span className="insignia-anfitrion">anfitrión</span>}
                  <button
                    type="button"
                    className="quitar-comensal"
                    disabled={ocupado}
                    onClick={() => quitar(c.id, c.nombre)}
                  >
                    Quitar
                  </button>
                </li>
              ))}
            </ul>
          )}

          <button
            type="button"
            className="secundario peligro boton-servicio"
            disabled={ocupado}
            onClick={liberar}
          >
            Liberar mesa
          </button>
        </>
      )}

      {aviso && <div className="aviso visible error">{aviso}</div>}
    </div>
  );
}
