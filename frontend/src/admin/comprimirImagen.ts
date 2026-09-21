// Redimensiona al ancho maximo indicado (1600px por defecto) y comprime a JPEG
// calidad 0.8 en el propio navegador: el servidor no necesita procesar imagenes.
export function comprimirImagen(archivo: File, anchoMax = 1600): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const lector = new FileReader();
    lector.onerror = () => reject(new Error("lectura fallida"));
    lector.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("imagen invalida"));
      img.onload = () => {
        const escala = Math.min(1, anchoMax / img.width);
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * escala);
        canvas.height = Math.round(img.height * escala);
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("sin contexto de canvas"));
          return;
        }
        // JPEG no tiene transparencia: un logo PNG con fondo transparente
        // saldria negro si no se pinta antes un fondo blanco.
        ctx.fillStyle = "#fff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (blob) => (blob ? resolve(blob) : reject(new Error("compresion fallida"))),
          "image/jpeg",
          0.8
        );
      };
      img.src = lector.result as string;
    };
    lector.readAsDataURL(archivo);
  });
}
