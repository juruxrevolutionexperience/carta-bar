import { useEffect, useState } from "react";

import "./hojaQR.css";
import { qrPng, qrSvg, svgADataUrl } from "./qr";

export interface DatosQr {
  url: string;
  nombre: string;
  texto: string;
}

function descargar(href: string, archivo: string) {
  const enlace = document.createElement("a");
  enlace.href = href;
  enlace.download = archivo;
  enlace.click();
}

// La hoja lista para imprimir (nombre, QR grande y un texto) y los botones
// para usarla. Solo la hoja sale en papel: ver hojaQR.css.
export function HojaQR({ url, nombre, texto }: DatosQr) {
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

  // Nombre de archivo a partir del subdominio: "cartia.jurux.app" -> "cartia".
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

  return (
    <div className="hoja-qr-contenedor">
      <div className="hoja-qr">
        <h3 className="hoja-qr-nombre">{nombre}</h3>
        {svg && (
          <img className="hoja-qr-codigo" src={svgADataUrl(svg)} alt={`Código QR de ${url}`} />
        )}
        {!svg && !error && <div className="hoja-qr-codigo hoja-qr-espera">Generando…</div>}
        {error && <div className="hoja-qr-codigo hoja-qr-espera">No se pudo generar el QR.</div>}
        <p className="hoja-qr-texto">{texto}</p>
        <p className="hoja-qr-url">{url.replace(/^https?:\/\//, "")}</p>
      </div>

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
