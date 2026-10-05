import { useAvisosPersonal } from "./useAvisosPersonal";

const TEXTO: Record<string, string> = {
  nueva: "nueva, por aceptar",
  cuenta: "pide la cuenta",
};

// Banner flotante, visible encima de cualquier pantalla del panel: una mesa
// nueva o que pide la cuenta no deberia pasar desapercibida solo porque el
// camarero estuviera mirando Cocina en vez de Servicio.
export function AvisosPersonal() {
  const avisos = useAvisosPersonal();
  if (avisos.length === 0) return null;

  return (
    <div className="avisos-personal" role="status" aria-live="polite">
      {avisos.map((a) => (
        <div key={a.clave} className={"aviso-personal tipo-" + a.tipo}>
          <strong>{a.nombre}</strong> · {TEXTO[a.tipo]}
        </div>
      ))}
    </div>
  );
}
