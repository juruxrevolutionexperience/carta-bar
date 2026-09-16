interface Props {
  src: string | null;
  onCerrar: () => void;
}

export function VisorFoto({ src, onCerrar }: Props) {
  return (
    <div
      className="visor-foto"
      hidden={src === null}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCerrar();
      }}
    >
      <button className="visor-cerrar" aria-label="Cerrar" onClick={onCerrar}>
        ×
      </button>
      <img src={src || ""} alt="" />
    </div>
  );
}
