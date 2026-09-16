import { useCartaContext } from "./CartaContext";
import { urlSegura } from "./seguridad";

export function Portada() {
  const { config, abrirSelectorIdioma, textos } = useCartaContext();

  const logo = urlSegura(config.logo);
  const portada = urlSegura(config.foto_portada);
  const nombre = config.nombre || "Carta";

  return (
    <>
      <div
        className="portada"
        id="portada"
        style={
          portada
            ? {
                backgroundImage:
                  "linear-gradient(180deg,rgba(23,19,16,.18),rgba(23,19,16,.5)),url('" +
                  portada +
                  "')",
              }
            : undefined
        }
      >
        <button className="btn-idioma" onClick={abrirSelectorIdioma}>
          <span>{textos.bandera || "🇪🇸"}</span>
        </button>
        <div className="logo-orbe">
          {logo ? <img src={logo} alt="" /> : <span className="inicial">{nombre.trim()[0] || "·"}</span>}
        </div>
      </div>

      <div className="identidad">
        <h1>{nombre}</h1>
        {config.subtitulo && <p className="sub">{config.subtitulo}</p>}
      </div>
    </>
  );
}
