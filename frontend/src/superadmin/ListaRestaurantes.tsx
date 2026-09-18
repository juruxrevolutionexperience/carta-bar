import type { ResumenRestaurante } from "./api";

interface Props {
  restaurantes: ResumenRestaurante[] | null;
  error: boolean;
}

export function ListaRestaurantes({ restaurantes, error }: Props) {
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
            </tr>
          </thead>
          <tbody>
            {restaurantes.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.nombre}</td>
                <td>{r.num_platos}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
