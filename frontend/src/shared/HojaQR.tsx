import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import "./hojaQR.css";
import { qrPng, qrSvg, svgADataUrl } from "./qr";

export interface DatosQr {
  url: string;
  nombre: string;
  texto: string;
}

interface Props extends DatosQr {
  // Hoja completa (nombre + QR + texto + URL) o tarjeta minima para un
  // soporte pequeno de mesa: solo el QR grande y el texto, sin nombre ni URL
  // (mas facil de leer de un vistazo y mas barata de imprimir).
  compacta?: boolean;
}

function descargar(href: string, archivo: string) {
  const enlace = document.createElement("a");
  enlace.href = href;
  enlace.download = archivo;
  enlace.click();
}

// La hoja lista para imprimir (nombre, QR grande y un texto) y los botones
// para usarla. Solo la hoja sale en papel: ver hojaQR.css.
export function HojaQR({ url, nombre, texto, compacta = false }: Props) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    setSvg(null);
    setError(false);
    qrSvg(url)
      .then(setSvg)
      .catch(() => setError(true));
  }, [url]);

  // Nombre de archivo a partir del subdominio: "la-catedral.jurux.app" -> "la-catedral".
  const base = "qr-" + new URL(url).hostname.split(".")[0];

  async function bajarPng() {
    descargar(await qrPng(url), `${base}.png`);
  }

  function bajarSvg() {
    if (!svg) return;
    descargar(svgADataUrl(svg), `${base}.svg`);
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(url);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      // Sin permiso de portapapeles: el enlace sigue visible en la hoja.
    }
  }

  const contenido: ReactNode = (
    <>
      {!compacta && <h3 className="hoja-qr-nombre">{nombre}</h3>}
      {svg && (
        <img className="hoja-qr-codigo" src={svgADataUrl(svg)} alt={`Código QR de ${url}`} />
      )}
      {!svg && !error && <div className="hoja-qr-codigo hoja-qr-espera">Generando…</div>}
      {error && <div className="hoja-qr-codigo hoja-qr-espera">No se pudo generar el QR.</div>}
      <p className="hoja-qr-texto">{texto}</p>
      {!compacta && <p className="hoja-qr-url">{url.replace(/^https?:\/\//, "")}</p>}
    </>
  );

  return (
    <div className="hoja-qr-contenedor">
      <div className="hoja-qr">{contenido}</div>

      {/* Copia solo para papel, colgada directamente del body: al imprimir se
          quita todo lo demas de la pagina (ver hojaQR.css). Ocultar el panel
          con "visibility" no vale: seguiria ocupando sitio y saldrian varias
          hojas. */}
      {createPortal(
        <div className={"hoja-qr-impresion" + (compacta ? " compacta" : "")}>
          <div className="hoja-qr">{contenido}</div>
        </div>,
        document.body
      )}

      <div className="hoja-qr-acciones">
        <button type="button" className="hoja-qr-boton principal" onClick={() => window.print()}>
          Imprimir
        </button>
        <button type="button" className="hoja-qr-boton" onClick={bajarPng} disabled={!svg}>
          Descargar PNG
        </button>
        <button type="button" className="hoja-qr-boton" onClick={bajarSvg} disabled={!svg}>
          Descargar SVG
        </button>
        <button type="button" className="hoja-qr-boton" onClick={copiar}>
          {copiado ? "¡Copiado!" : "Copiar enlace"}
        </button>
        <a className="hoja-qr-boton" href={url} target="_blank" rel="noopener noreferrer">
          Abrir la carta
        </a>
      </div>
    </div>
  );
}
