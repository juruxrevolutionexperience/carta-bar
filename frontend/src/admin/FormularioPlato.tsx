import { useState } from "react";

import {
  crearEspecial,
  eliminarEspecial,
  guardarPlatoExistente,
  subirFoto,
  type CuerpoPlato,
} from "./api";
import { BloqueFoto } from "./BloqueFoto";
import { comprimirImagen } from "./comprimirImagen";
import { SelectorFotoNueva } from "./SelectorFotoNueva";
import { TEXTO_ALERGENO, TEXTO_DIETA, TEXTO_ETIQUETA, type ClaveDieta } from "./textos";
import { CATEGORIA_ESPECIALES, type Alergeno, type Etiqueta, type Plato } from "./types";

interface Props {
  plato: Plato;
  onGuardado: (plato: Plato) => void;
  onCancelar: () => void;
  onEliminado: () => void;
}

export function FormularioPlato({ plato, onGuardado, onCancelar, onEliminado }: Props) {
  const [nombre, setNombre] = useState(plato.nombre);
  const [descripcion, setDescripcion] = useState(plato.descripcion);
  const [precioTxt, setPrecioTxt] = useState(plato.precio === null ? "" : String(plato.precio));
  const [ingredientesTxt, setIngredientesTxt] = useState((plato.ingredientes || []).join("\n"));
  const [alergenos, setAlergenos] = useState<Alergeno[]>(plato.alergenos || []);
  const [etiqueta, setEtiqueta] = useState<Etiqueta | "">(plato.etiqueta ?? "");
  const [dieta, setDieta] = useState<ClaveDieta[]>(
    (Object.keys(TEXTO_DIETA) as ClaveDieta[]).filter((clave) => plato[clave])
  );
  const [fotoActual, setFotoActual] = useState(plato.foto);
  const [fotoNueva, setFotoNueva] = useState<File | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  function alternarAlergeno(valor: Alergeno) {
    setAlergenos((actual) =>
      actual.includes(valor) ? actual.filter((a) => a !== valor) : [...actual, valor]
    );
  }

  function alternarDieta(valor: ClaveDieta) {
    setDieta((actual) =>
      actual.includes(valor) ? actual.filter((d) => d !== valor) : [...actual, valor]
    );
  }

  async function guardar() {
    setAviso(null);
    setGuardando(true);

    const cuerpo: CuerpoPlato = {
      nombre,
      descripcion,
      precio: precioTxt.trim() === "" ? null : parseFloat(precioTxt),
      ingredientes: ingredientesTxt
        .split("\n")
        .map((i) => i.trim())
        .filter((i) => i.length > 0),
      alergenos,
      etiqueta: etiqueta === "" ? null : etiqueta,
      vegano: dieta.includes("vegano"),
      vegetariano: dieta.includes("vegetariano"),
      sin_gluten: dieta.includes("sin_gluten"),
      sin_lactosa: dieta.includes("sin_lactosa"),
    };

    try {
      const esNuevo = !plato.id;
      const resp = esNuevo
        ? await crearEspecial(cuerpo)
        : await guardarPlatoExistente(plato.id as string, cuerpo);

      if (resp.status === 204) {
        onGuardado({ ...plato, ...cuerpo });
        return;
      }
      if (resp.status === 201) {
        let creado: Plato = await resp.json();
        if (fotoNueva) {
          try {
            const blob = await comprimirImagen(fotoNueva);
            const respFoto = await subirFoto(creado.id as string, blob);
            if (respFoto.ok) {
              const datos = await respFoto.json();
              creado = { ...creado, foto: datos.foto };
            } else {
              // El formulario se cierra justo despues (onGuardado): un aviso
              // en pantalla no llegaria a verse, por eso aqui si hace falta
              // interrumpir con un alert en vez del <div class="aviso"> normal.
              window.alert(
                "El especial se creó, pero no se pudo subir la foto. Edítalo para reintentarlo."
              );
            }
          } catch {
            window.alert(
              "El especial se creó, pero no se pudo subir la foto. Edítalo para reintentarlo."
            );
          }
        }
        onGuardado(creado);
        return;
      }
      setAviso(
        resp.status === 404
          ? "Este plato ya no existe."
          : "Revisa los datos: el precio debe ser mayor que cero."
      );
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setGuardando(false);
    }
  }

  async function eliminar() {
    if (!plato.id || !window.confirm("¿Eliminar este especial? No se puede deshacer.")) return;
    try {
      const resp = await eliminarEspecial(plato.id);
      if (resp.status === 204) {
        onEliminado();
        return;
      }
      setAviso("No se pudo eliminar. Inténtalo de nuevo.");
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    }
  }

  const puedeEliminar = plato.categoria === CATEGORIA_ESPECIALES && plato.id;

  return (
    <div className="tarjeta" style={{ padding: "16px", margin: "12px 0" }}>
      <label>Nombre</label>
      <input value={nombre} onChange={(e) => setNombre(e.target.value)} />

      <label>Descripción</label>
      <textarea value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />

      <label>Precio (vacío = a consultar)</label>
      <input
        type="number"
        step="0.01"
        min="0.01"
        value={precioTxt}
        onChange={(e) => setPrecioTxt(e.target.value)}
      />

      <label>Foto</label>
      {plato.id ? (
        <BloqueFoto plato={{ ...plato, foto: fotoActual }} onCambioFoto={setFotoActual} />
      ) : (
        <SelectorFotoNueva archivo={fotoNueva} onSeleccionar={setFotoNueva} />
      )}

      <label>Ingredientes (uno por línea)</label>
      <textarea value={ingredientesTxt} onChange={(e) => setIngredientesTxt(e.target.value)} />

      <div className="grupo-campo">
        <span>Alérgenos</span>
        <div className="rejilla-opciones">
          {(Object.entries(TEXTO_ALERGENO) as [Alergeno, string][]).map(([valor, texto]) => (
            <label className="opcion" key={valor}>
              <input
                type="checkbox"
                checked={alergenos.includes(valor)}
                onChange={() => alternarAlergeno(valor)}
              />
              {texto}
            </label>
          ))}
        </div>
      </div>

      <div className="grupo-campo">
        <span>Etiqueta</span>
        <div className="rejilla-opciones">
          <label className="opcion">
            <input
              type="radio"
              name="etiqueta"
              checked={etiqueta === ""}
              onChange={() => setEtiqueta("")}
            />
            Ninguna
          </label>
          {(Object.entries(TEXTO_ETIQUETA) as [Etiqueta, string][]).map(([valor, texto]) => (
            <label className="opcion" key={valor}>
              <input
                type="radio"
                name="etiqueta"
                checked={etiqueta === valor}
                onChange={() => setEtiqueta(valor)}
              />
              {texto}
            </label>
          ))}
        </div>
      </div>

      <div className="grupo-campo">
        <span>Dieta</span>
        <div className="rejilla-opciones">
          {(Object.entries(TEXTO_DIETA) as [ClaveDieta, string][]).map(([valor, texto]) => (
            <label className="opcion" key={valor}>
              <input
                type="checkbox"
                checked={dieta.includes(valor)}
                onChange={() => alternarDieta(valor)}
              />
              {texto}
            </label>
          ))}
        </div>
      </div>

      <button type="button" className="primario" disabled={guardando} onClick={guardar}>
        Guardar
      </button>
      <button type="button" className="secundario" onClick={onCancelar}>
        Cancelar
      </button>
      {puedeEliminar && (
        <button type="button" className="secundario" onClick={eliminar}>
          Eliminar especial
        </button>
      )}
      {aviso && <div className="aviso visible error">{aviso}</div>}
    </div>
  );
}
