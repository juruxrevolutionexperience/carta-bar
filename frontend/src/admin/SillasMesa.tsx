import { CELDA, repartirALoLargo, repartirSillas, type FormaMesa } from "./planoUtil";

interface Props {
  forma: FormaMesa;
  capacidad: number;
  ancho: number;
  alto: number;
}

// Medidas de una silla, en píxeles del plano (antes del zoom).
const LARGO = CELDA * 0.42;
const GRUESO = CELDA * 0.16;
const SEPARACION = CELDA * 0.05;

// Las sillas son decoración: el lector de pantalla ya oye el aforo en el texto
// de la mesa, así que aquí sobra (aria-hidden en el contenedor).
export function SillasMesa({ forma, capacidad, ancho, alto }: Props) {
  const anchoPx = ancho * CELDA;
  const altoPx = alto * CELDA;

  // En las mesas redondas las sillas van en corona alrededor del centro.
  if (forma === "redonda" || forma === "barril") {
    const radio = Math.min(anchoPx, altoPx) / 2 + SEPARACION + GRUESO / 2;
    return (
      <div className="sillas" aria-hidden="true">
        {Array.from({ length: Math.min(capacidad, 12) }, (_, i) => {
          const angulo = (i / Math.min(capacidad, 12)) * 2 * Math.PI - Math.PI / 2;
          return (
            <span
              key={i}
              className="silla"
              style={{
                width: LARGO,
                height: GRUESO,
                left: anchoPx / 2 + Math.cos(angulo) * radio - LARGO / 2,
                top: altoPx / 2 + Math.sin(angulo) * radio - GRUESO / 2,
                transform: `rotate(${angulo + Math.PI / 2}rad)`,
              }}
            />
          );
        })}
      </div>
    );
  }

  if (forma === "taburete") return null;

  const [arriba, derecha, abajo, izquierda] = repartirSillas(capacidad, ancho, alto);
  const sillas: { estilo: React.CSSProperties; clave: string }[] = [];

  repartirALoLargo(arriba).forEach((p, i) =>
    sillas.push({
      clave: `a${i}`,
      estilo: {
        width: LARGO,
        height: GRUESO,
        left: anchoPx * p - LARGO / 2,
        top: -GRUESO - SEPARACION,
      },
    })
  );
  repartirALoLargo(abajo).forEach((p, i) =>
    sillas.push({
      clave: `b${i}`,
      estilo: {
        width: LARGO,
        height: GRUESO,
        left: anchoPx * p - LARGO / 2,
        top: altoPx + SEPARACION,
      },
    })
  );
  repartirALoLargo(izquierda).forEach((p, i) =>
    sillas.push({
      clave: `i${i}`,
      estilo: {
        width: GRUESO,
        height: LARGO,
        left: -GRUESO - SEPARACION,
        top: altoPx * p - LARGO / 2,
      },
    })
  );
  repartirALoLargo(derecha).forEach((p, i) =>
    sillas.push({
      clave: `d${i}`,
      estilo: {
        width: GRUESO,
        height: LARGO,
        left: anchoPx + SEPARACION,
        top: altoPx * p - LARGO / 2,
      },
    })
  );

  return (
    <div className="sillas" aria-hidden="true">
      {sillas.map((s) => (
        <span key={s.clave} className="silla" style={s.estilo} />
      ))}
    </div>
  );
}
