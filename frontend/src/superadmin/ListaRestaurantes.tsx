import type { ResumenRestaurante } from "./api";

interface Props {
  restaurantes: ResumenRestaurante[] | null;
  error: boolean;
  seleccionado: string | null;
  onVerQr: (id: string) => void;
}

export function ListaRestaurantes({ restaurantes, error, seleccionado, onVerQr }: Props) {
  return (
    <div className="panel-tarjeta">
      <h2>Restaurantes</h2>
      {error && <p className="cargando">No se pudo cargar la lista.</p>}
      {!error && restaurantes === null && <p className="cargando">Cargando…</p>}
      {!error && restaurantes !== null && restaurantes.length === 0 && (
        <p className="cargando">No hay restaurantes todavía.</p>
      )}
      {!error && restaurantes !== null && restaurantes.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Subdominio</th>
              <th>Nombre</th>
              <th>Platos</th>
              <th>QR</th>
            </tr>
          </thead>
          <tbody>
            {restaurantes.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.nombre}</td>
                <td>{r.num_platos}</td>
                <td>
                  <button
                    type="button"
                    className="secundario"
                    aria-pressed={seleccionado === r.id}
                    onClick={() => onVerQr(r.id)}
                  >
                    Ver QR
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
