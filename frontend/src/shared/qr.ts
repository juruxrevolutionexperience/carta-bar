import QRCode from "qrcode";

// El QR se dibuja aqui, en el navegador: el servidor solo dice a que direccion
// apunta y que texto lleva la hoja. "M" corrige hasta un 15% de daño: aguanta
// una hoja arrugada o manchada en la mesa.
const OPCIONES = { errorCorrectionLevel: "M" as const, margin: 2 };

export function qrSvg(url: string): Promise<string> {
  return QRCode.toString(url, { ...OPCIONES, type: "svg" });
}

// Grande a proposito: se puede imprimir a tamaño cartel sin que se pixele.
export function qrPng(url: string): Promise<string> {
  return QRCode.toDataURL(url, { ...OPCIONES, width: 1200 });
}

export function svgADataUrl(svg: string): string {
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}
