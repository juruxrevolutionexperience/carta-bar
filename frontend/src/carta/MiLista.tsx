import { useState } from "react";

import { useCartaContext } from "./CartaContext";
import type { Plato } from "./types";
import type { useListaCliente } from "./useListaCliente";

interface Props {
  lista: ReturnType<typeof useListaCliente>;
}

// Recordatorio personal del cliente, no un pedido: se guarda solo en su
// movil (ver useListaCliente.ts). El aviso de abajo lo deja claro tambien en
// pantalla, para que nadie espere que el camarero se entere solo.
export function MiLista({ lista }: Props) {
  const { carta, config, t } = useCartaContext();
  const [abierta, setAbierta] = useState(false);
  const moneda = config.moneda || "€";

  const filas = Object.entries(lista.cantidades)
    .map(([id, cantidad]) => ({ plato: carta.find((p) => p.id === id), cantidad }))
    .filter((f): f is { plato: Plato; cantidad: number } => Boolean(f.plato));

  const importeTotal = filas.reduce(
    (suma, f) => suma + (f.plato.precio || 0) * f.cantidad,
    0
  );

  return (
    <>
      <button
        type="button"
        className="lanzador lanzador-lista"
        onClick={() => setAbierta(true)}
        aria-label={t("mi_lista")}
      >
        🛒
        {lista.total > 0 && <span className="cuenta-lista">{lista.total}</span>}
      </button>

      <div className={"panel" + (abierta ? " abierto" : "")}>
        <div className="panel-top">
          <h2>{t("mi_lista")}</h2>
          <button type="button" className="cerrar" aria-label="Cerrar" onClick={() => setAbierta(false)}>
            ×
          </button>
        </div>

        <div className="hilo-lista">
          {filas.length === 0 && <p className="vacio">{t("lista_vacia")}</p>}
          {filas.map(({ plato, cantidad }) => (
            <div className="fila-lista" key={plato.id}>
              <div className="fila-lista-info">
                <span className="fila-lista-nombre">{plato.nombre}</span>
                {plato.precio != null && (
                  <span className="fila-lista-precio">
                    {(plato.precio * cantidad).toFixed(2).replace(".", ",")} {moneda}
                  </span>
                )}
              </div>
              <div className="fila-lista-cantidad">
                <button
                  type="button"
                  aria-label={`Quitar una unidad de ${plato.nombre}`}
                  onClick={() => lista.cambiar(plato.id, cantidad - 1)}
                >
                  −
                </button>
                <span>{cantidad}</span>
                <button
                  type="button"
                  aria-label={`Añadir una unidad de ${plato.nombre}`}
                  onClick={() => lista.cambiar(plato.id, cantidad + 1)}
                >
                  +
                </button>
              </div>
            </div>
          ))}
        </div>

        {filas.length > 0 && (
          <div className="pie-lista">
            <div className="total-lista">
              <span>{t("total")}</span>
              <strong>
                {importeTotal.toFixed(2).replace(".", ",")} {moneda}
              </strong>
            </div>
            <p className="aviso-lista">{t("aviso_lista")}</p>
            <button type="button" className="vaciar-lista" onClick={lista.vaciar}>
              {t("vaciar_lista")}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
