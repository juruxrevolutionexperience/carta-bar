import { useCallback, useEffect, useState } from "react";

import { cargarMesas, cargarZonas, type Mesa, type Zona } from "./api";
import { PanelServicio } from "./PanelServicio";
import {
  TEXTO_ESTADO,
  agruparPorZona,
  contarPorEstado,
  estadoDe,
  personas,
  tiempoDesde,
} from "./servicioUtil";

// Más a menudo que el plano (8 s): aquí se está esperando a que aparezca una
// mesa por aceptar. El tiempo real de verdad llega con las comandas.
const REFRESCO_MS = 5000;

const TODAS = "todas";

// Lo que pide atencion sale primero: una mesa por aceptar bloquea al cliente
// que espera, una cuenta pedida bloquea la salida; abiertas y libres despues.
const PRIORIDAD: Record<string, number> = {
  por_confirmar: 0,
  cuenta_pedida: 1,
  abierta: 2,
  libre: 3,
};

function porUrgencia(a: Mesa, b: Mesa): number {
  return PRIORIDAD[estadoDe(a)] - PRIORIDAD[estadoDe(b)];
}

// El día a día de la sala: las mismas mesas y zonas del plano, pero en
// tarjetas grandes separadas por zona, para ver de un vistazo qué está libre,
// qué hay que aceptar y qué está abierto. El plano queda para montar el local.
export function SeccionServicio() {
  const [zonas, setZonas] = useState<Zona[] | null>(null);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [error, setError] = useState(false);
  const [filtro, setFiltro] = useState<string>(TODAS);
  const [seleccionada, setSeleccionada] = useState<string | null>(null);
  const [ahora, setAhora] = useState(() => Date.now());

  const recargar = useCallback(() => {
    Promise.all([cargarZonas(), cargarMesas()])
      .then(([zonasCargadas, mesasCargadas]) => {
        setZonas(zonasCargadas);
        setMesas(mesasCargadas);
        setAhora(Date.now());
        setError(false);
        setFiltro((actual) =>
          actual === TODAS || zonasCargadas.some((z) => z.id === actual) ? actual : TODAS
        );
      })
      .catch(() => setError(true));
  }, []);

  useEffect(recargar, [recargar]);

  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) recargar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [recargar]);

  if (zonas === null) {
    return (
      <div className="tarjeta">
        <p>{error ? "No se pudieron cargar las mesas." : "Cargando mesas…"}</p>
      </div>
    );
  }

  if (mesas.length === 0) {
    return (
      <div className="tarjeta">
        <h2>Aún no hay mesas</h2>
        <p>Monta el local en "Mesas" (el plano) y aquí aparecerán para el servicio.</p>
      </div>
    );
  }

  const grupos = agruparPorZona(zonas, mesas)
    .filter((g) => g.mesas.length > 0 && (filtro === TODAS || g.zona.id === filtro))
    .map((g) => ({ ...g, mesas: [...g.mesas].sort(porUrgencia) }));
  const urgentes = mesas
    .filter((m) => PRIORIDAD[estadoDe(m)] <= PRIORIDAD.cuenta_pedida)
    .filter((m) => filtro === TODAS || m.zona_id === filtro)
    .sort(porUrgencia);
  const cuenta = contarPorEstado(mesas);
  const elegida = mesas.find((m) => m.id === seleccionada) ?? null;

  return (
    <div className="servicio">
      <div className="resumen-servicio" aria-live="polite">
        {cuenta.por_confirmar > 0 && (
          <span className="chip-resumen estado-por_confirmar">
            {cuenta.por_confirmar} por aceptar
          </span>
        )}
        {cuenta.cuenta_pedida > 0 && (
          <span className="chip-resumen estado-cuenta_pedida">
            {cuenta.cuenta_pedida} piden la cuenta
          </span>
        )}
        <span className="chip-resumen estado-abierta">
          {cuenta.abierta} {cuenta.abierta === 1 ? "abierta" : "abiertas"}
        </span>
        <span className="chip-resumen estado-libre">
          {cuenta.libre} {cuenta.libre === 1 ? "libre" : "libres"}
        </span>
        {error && <span className="chip-resumen sin-conexion">Sin conexión</span>}
      </div>

      {zonas.length > 1 && (
        <div className="pestanas-zona" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={filtro === TODAS}
            className={"pestana-zona" + (filtro === TODAS ? " activa" : "")}
            onClick={() => setFiltro(TODAS)}
          >
            Todas
          </button>
          {zonas.map((z) => {
            const avisos = mesas.filter(
              (m) => m.zona_id === z.id && estadoDe(m) === "por_confirmar"
            ).length;
            return (
              <button
                key={z.id}
                type="button"
                role="tab"
                aria-selected={filtro === z.id}
                className={"pestana-zona" + (filtro === z.id ? " activa" : "")}
                onClick={() => setFiltro(z.id)}
              >
                {z.nombre}
                {avisos > 0 && <span className="punto-aviso" aria-label={`${avisos} por aceptar`} />}
              </button>
            );
          })}
        </div>
      )}

      {urgentes.length > 0 && (
        <section className="cola-atencion" aria-label="Piden atención">
          <h2>Atender ahora · {urgentes.length}</h2>
          <div className="rejilla-atencion">
            {urgentes.map((m) => {
              const estado = estadoDe(m);
              return (
                <button
                  key={m.id}
                  type="button"
                  className={"tarjeta-atencion estado-" + estado}
                  onClick={() => setSeleccionada(m.id)}
                >
                  <span className="nombre-mesa">{m.nombre}</span>
                  <span className="estado-tarjeta">{TEXTO_ESTADO[estado]}</span>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <div className="zona-trabajo">
        <div>
          {grupos.map(({ zona, mesas: deLaZona }) => {
            const ocupadas = deLaZona.filter((m) => estadoDe(m) !== "libre").length;
            return (
              <section key={zona.id} className="grupo-servicio">
                <h2 className="titulo-zona-servicio">
                  {zona.nombre}
                  <span>
                    {ocupadas}/{deLaZona.length}
                  </span>
                </h2>
                <div className="rejilla-mesas">
                  {deLaZona.map((m) => {
                    const estado = estadoDe(m);
                    const tiempo = tiempoDesde(m.abierta_en, ahora);
                    return (
                      <button
                        key={m.id}
                        type="button"
                        className={
                          "tarjeta-mesa estado-" +
                          estado +
                          (m.id === seleccionada ? " elegida" : "")
                        }
                        onClick={() => setSeleccionada(m.id)}
                      >
                        <span className="nombre-mesa">{m.nombre}</span>
                        <span className="estado-tarjeta">{TEXTO_ESTADO[estado]}</span>
                        <span className="detalle-tarjeta">
                          {estado === "libre"
                            ? `${m.capacidad} ${m.capacidad === 1 ? "plaza" : "plazas"}`
                            : [m.comensales ? personas(m.comensales) : "", tiempo]
                                .filter(Boolean)
                                .join(" · ")}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>

        {elegida ? (
          <PanelServicio
            key={elegida.id}
            mesa={elegida}
            ahora={ahora}
            onCambio={recargar}
            onCerrar={() => setSeleccionada(null)}
          />
        ) : (
          <div className="tarjeta panel-vacio">
            <p>Toca una mesa para abrirla, aceptarla o liberarla.</p>
          </div>
        )}
      </div>
    </div>
  );
}
