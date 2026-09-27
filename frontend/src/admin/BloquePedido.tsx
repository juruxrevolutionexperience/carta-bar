import type { Destino, GrupoOpciones } from "./api";
import { FilasPrecio, type FilaPrecio } from "./FilasPrecio";
import { resumenGrupo } from "./textosProductos";

// Lo de "Para pedir" de un plato mientras se edita: los formatos van como
// texto (ver FilasPrecio) y se convierten al guardar el plato.
export interface PedidoEditable {
  destino: Destino | null;
  alcohol: boolean;
  formatos: FilaPrecio[];
  grupos: string[];
}

interface Props {
  valor: PedidoEditable;
  onCambio: (valor: PedidoEditable) => void;
  grupos: GrupoOpciones[];
  destinoCategoria: Destino;
}

const TEXTO_DESTINO: Record<Destino, string> = { cocina: "Cocina", barra: "Barra" };

export function BloquePedido({ valor, onCambio, grupos, destinoCategoria }: Props) {
  function alternarGrupo(id: string) {
    onCambio({
      ...valor,
      grupos: valor.grupos.includes(id)
        ? valor.grupos.filter((g) => g !== id)
        : [...valor.grupos, id],
    });
  }

  return (
    <fieldset className="bloque-pedido">
      <legend>Para pedir desde la mesa</legend>

      <label htmlFor="pedido-destino">Dónde se prepara</label>
      <select
        id="pedido-destino"
        value={valor.destino ?? ""}
        onChange={(e) =>
          onCambio({ ...valor, destino: e.target.value === "" ? null : (e.target.value as Destino) })
        }
      >
        <option value="">Como su categoría ({TEXTO_DESTINO[destinoCategoria]})</option>
        <option value="cocina">Cocina</option>
        <option value="barra">Barra</option>
      </select>

      <label className="opcion">
        <input
          type="checkbox"
          checked={valor.alcohol}
          onChange={(e) => onCambio({ ...valor, alcohol: e.target.checked })}
        />
        Lleva alcohol
      </label>

      <label>Formatos (tapa, media, ración, caña, jarra…)</label>
      <p className="ayuda-campo">
        Sin formatos se pide a su precio de siempre. Con formatos, la carta los enseña con su
        precio y el cliente elige uno. No se traducen: se piden por su nombre.
      </p>
      <FilasPrecio
        filas={valor.formatos}
        onCambio={(formatos) => onCambio({ ...valor, formatos })}
        ejemploNombre="Ración"
        maximo={10}
        textoAnadir="Añadir formato"
      />

      <label>Extras y opciones</label>
      {grupos.length === 0 ? (
        <p className="ayuda-campo">
          Aún no hay grupos. Créalos en "Extras y opciones" del menú y luego márcalos aquí.
        </p>
      ) : (
        <div className="rejilla-opciones">
          {grupos.map((g) => (
            <label className="opcion" key={g.id}>
              <input
                type="checkbox"
                checked={valor.grupos.includes(g.id)}
                onChange={() => alternarGrupo(g.id)}
              />
              <span>
                {g.nombre} <span className="resumen-grupo">({resumenGrupo(g)})</span>
              </span>
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}
