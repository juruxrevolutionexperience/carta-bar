import { useCartaContext } from "./CartaContext";

export function SelectorIdioma() {
  const { idiomas, mostrarSelectorIdioma, cambiarIdioma } = useCartaContext();

  return (
    <div className="velo" hidden={!mostrarSelectorIdioma}>
      <div className="caja-idioma">
        <h2>Elige tu idioma</h2>
        <p>Choose your language · Sprache wählen</p>
        <div className="opciones-idioma">
          {Object.entries(idiomas).map(([cod, datos]) => (
            <button className="op-idioma" key={cod} onClick={() => cambiarIdioma(cod)}>
              <span className="bandera">{datos.bandera}</span>
              {datos.nombre_idioma}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
