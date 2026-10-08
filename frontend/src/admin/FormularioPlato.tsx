import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  cargarProductos,
  crearEspecial,
  crearPlato,
  eliminarPlato,
  guardarPedidoPlato,
  guardarPlatoExistente,
  pedidoVacio,
  subirFoto,
  type ConfigProductos,
  type CuerpoPlato,
  type DatosPedidoPlato,
} from "./api";
import { BloqueFoto } from "./BloqueFoto";
import { BloquePedido, type PedidoEditable } from "./BloquePedido";
import { filasAValores, valoresAFilas } from "./FilasPrecio";
import { comprimirImagen } from "./comprimirImagen";
import { SelectorFotoNueva } from "./SelectorFotoNueva";
import { VistaPreviaPlato } from "./VistaPreviaPlato";
import { TEXTO_ALERGENO, TEXTO_DIETA, TEXTO_ETIQUETA, type ClaveDieta } from "./textos";
import {
  type Alergeno,
  type Categoria,
  type Etiqueta,
  type Plato,
} from "./types";

interface Props {
  plato: Plato;
  onGuardado: (plato: Plato) => void;
  onCancelar: () => void;
  onEliminado: () => void;
  // Solo al dar de alta un plato normal: las categorias entre las que elegir.
  // Sin esto, un plato nuevo es un especial del dia (comportamiento de siempre).
  categoriasElegibles?: Categoria[];
}

export function FormularioPlato({
  plato,
  onGuardado,
  onCancelar,
  onEliminado,
  categoriasElegibles,
}: Props) {
  const [categoria, setCategoria] = useState(categoriasElegibles?.[0]?.id ?? "");
  const [alergenosRevisados, setAlergenosRevisados] = useState(plato.alergenos_confirmados);
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

  // "Para pedir" (destino, formatos, extras, alcohol) vive aparte del plato:
  // se carga al abrir el formulario y se guarda justo después del plato.
  const [productos, setProductos] = useState<ConfigProductos | null>(null);
  const [errorProductos, setErrorProductos] = useState(false);
  const [pedido, setPedido] = useState<PedidoEditable | null>(null);
  const [pedidoInicial, setPedidoInicial] = useState<DatosPedidoPlato>(pedidoVacio());

  useEffect(() => {
    let vigente = true;
    cargarProductos()
      .then((config) => {
        if (!vigente) return;
        const actual = (plato.id && config.platos[plato.id]) || pedidoVacio();
        const inicial: DatosPedidoPlato = {
          destino: actual.destino,
          alcohol: actual.alcohol,
          formatos: actual.formatos,
          grupos: actual.grupos,
        };
        setProductos(config);
        setPedidoInicial(inicial);
        setPedido({ ...inicial, formatos: valoresAFilas(inicial.formatos) });
      })
      .catch(() => vigente && setErrorProductos(true));
    return () => {
      vigente = false;
    };
  }, [plato.id]);

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

  // Foto recien elegida y aun sin subir: se ve en la vista previa por una URL local.
  const [urlFotoNueva, setUrlFotoNueva] = useState<string | null>(null);
  useEffect(() => {
    if (!fotoNueva) {
      setUrlFotoNueva(null);
      return;
    }
    const url = URL.createObjectURL(fotoNueva);
    setUrlFotoNueva(url);
    return () => URL.revokeObjectURL(url);
  }, [fotoNueva]);

  const platoPrevio = {
    id: plato.id ?? "nuevo",
    nombre: nombre.trim() || "Nombre del plato",
    descripcion,
    precio: precioTxt.trim() === "" ? null : parseFloat(precioTxt),
    categoria: plato.id || categoriasElegibles === undefined ? plato.categoria : categoria,
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
    disponible: true,
    foto: urlFotoNueva ?? fotoActual,
    alergenos_confirmados: alergenosRevisados,
  };

  const esPlatoNormalNuevo = !plato.id && categoriasElegibles !== undefined;

  async function guardar() {
    setAviso(null);
    if (esPlatoNormalNuevo && !categoria) {
      setAviso("Elige una categoría.");
      return;
    }
    if (esPlatoNormalNuevo && !alergenosRevisados) {
      setAviso("Confirma que has revisado los alérgenos del plato.");
      return;
    }
    // Se valida antes de guardar nada: un formato a medias no debe dejar el
    // plato guardado y su "para pedir" sin guardar.
    let datosPedido: DatosPedidoPlato | null = null;
    if (pedido) {
      const formatos = filasAValores(pedido.formatos, false);
      if (typeof formatos === "string") {
        setAviso(`Formatos: ${formatos}`);
        return;
      }
      datosPedido = { ...pedido, formatos };
    }
    const cambioPedido =
      datosPedido !== null && JSON.stringify(datosPedido) !== JSON.stringify(pedidoInicial);

    async function guardarPedido(id: string): Promise<boolean> {
      if (!cambioPedido || datosPedido === null) return true;
      try {
        const resp = await guardarPedidoPlato(id, datosPedido);
        return resp.ok;
      } catch {
        return false;
      }
    }
    const AVISO_PEDIDO =
      "El plato se guardó, pero no lo de «Para pedir» (formatos, extras…). Ábrelo y guárdalo otra vez.";

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
      alergenos_confirmados: alergenosRevisados,
    };

    try {
      const esNuevo = !plato.id;
      const resp = esNuevo
        ? esPlatoNormalNuevo
          ? await crearPlato({ ...cuerpo, categoria })
          : await crearEspecial(cuerpo)
        : await guardarPlatoExistente(plato.id as string, cuerpo);

      if (resp.status === 204) {
        if (!(await guardarPedido(plato.id as string))) window.alert(AVISO_PEDIDO);
        onGuardado({ ...plato, ...cuerpo });
        return;
      }
      if (resp.status === 201) {
        let creado: Plato = await resp.json();
        // Como con la foto: el formulario se cierra enseguida, así que un
        // fallo aquí se avisa con un alert.
        if (!(await guardarPedido(creado.id as string))) window.alert(AVISO_PEDIDO);
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
                "El plato se creó, pero no se pudo subir la foto. Edítalo para reintentarlo."
              );
            }
          } catch {
            window.alert(
              "El plato se creó, pero no se pudo subir la foto. Edítalo para reintentarlo."
            );
          }
        }
        onGuardado(creado);
        return;
      }
      setAviso(
        resp.status === 404
          ? esPlatoNormalNuevo
            ? "Esa categoría ya no existe."
            : "Este plato ya no existe."
          : "Revisa los datos: el precio debe ser mayor que cero."
      );
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    } finally {
      setGuardando(false);
    }
  }

  async function eliminar() {
    if (!plato.id || !window.confirm(`¿Eliminar "${plato.nombre}"? No se puede deshacer.`)) return;
    try {
      const resp = await eliminarPlato(plato.id);
      if (resp.status === 204) {
        onEliminado();
        return;
      }
      setAviso("No se pudo eliminar. Inténtalo de nuevo.");
    } catch {
      setAviso("No se pudo conectar. Inténtalo de nuevo.");
    }
  }

  const puedeEliminar = Boolean(plato.id);

  return (
    <Card sx={{ my: 1.5 }}>
      <CardContent>
        <Stack spacing={2}>
          {esPlatoNormalNuevo && (
            <FormControl size="small" fullWidth>
              <InputLabel id="categoria-plato">Categoría</InputLabel>
              <Select
                labelId="categoria-plato"
                label="Categoría"
                value={categoria}
                onChange={(e) => setCategoria(e.target.value)}
              >
                {categoriasElegibles.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <TextField
            label="Nombre"
            size="small"
            fullWidth
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />

          <TextField
            label="Descripción"
            size="small"
            fullWidth
            multiline
            minRows={2}
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
          />

          <TextField
            label="Precio (vacío = a consultar)"
            size="small"
            type="number"
            slotProps={{ htmlInput: { step: 0.01, min: 0.01 } }}
            value={precioTxt}
            onChange={(e) => setPrecioTxt(e.target.value)}
          />

          <Box>
            <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 0.5 }}>Foto</Typography>
            {plato.id ? (
              <BloqueFoto plato={{ ...plato, foto: fotoActual }} onCambioFoto={setFotoActual} />
            ) : (
              <SelectorFotoNueva archivo={fotoNueva} onSeleccionar={setFotoNueva} />
            )}
          </Box>

          <TextField
            label="Ingredientes (uno por línea)"
            size="small"
            fullWidth
            multiline
            minRows={2}
            value={ingredientesTxt}
            onChange={(e) => setIngredientesTxt(e.target.value)}
          />

          <Box>
            <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>Alérgenos</Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {(Object.entries(TEXTO_ALERGENO) as [Alergeno, string][]).map(([valor, texto]) => (
                <FormControlLabel
                  key={valor}
                  sx={{ width: { xs: "100%", sm: "48%" }, mr: 0 }}
                  control={
                    <Checkbox
                      size="small"
                      checked={alergenos.includes(valor)}
                      onChange={() => alternarAlergeno(valor)}
                    />
                  }
                  label={<Typography sx={{ fontSize: 14 }}>{texto}</Typography>}
                />
              ))}
            </Box>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>Etiqueta</Typography>
            <RadioGroup
              row
              value={etiqueta}
              onChange={(e) => setEtiqueta(e.target.value as Etiqueta | "")}
            >
              <FormControlLabel value="" control={<Radio size="small" />} label="Ninguna" />
              {(Object.entries(TEXTO_ETIQUETA) as [Etiqueta, string][]).map(([valor, texto]) => (
                <FormControlLabel
                  key={valor}
                  value={valor}
                  control={<Radio size="small" />}
                  label={texto}
                />
              ))}
            </RadioGroup>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 13, fontWeight: 600, mb: 0.5 }}>Dieta</Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {(Object.entries(TEXTO_DIETA) as [ClaveDieta, string][]).map(([valor, texto]) => (
                <FormControlLabel
                  key={valor}
                  sx={{ width: { xs: "100%", sm: "48%" }, mr: 0 }}
                  control={
                    <Checkbox
                      size="small"
                      checked={dieta.includes(valor)}
                      onChange={() => alternarDieta(valor)}
                    />
                  }
                  label={<Typography sx={{ fontSize: 14 }}>{texto}</Typography>}
                />
              ))}
            </Box>
          </Box>

          {pedido && productos ? (
            <BloquePedido
              valor={pedido}
              onCambio={setPedido}
              grupos={productos.grupos}
              destinoCategoria={
                productos.destinos_categoria[
                  plato.id || categoriasElegibles === undefined ? plato.categoria : categoria
                ] ?? "cocina"
              }
            />
          ) : (
            errorProductos && (
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                No se pudo cargar «Para pedir» (formatos, extras…). El resto del plato se guarda
                igual.
              </Typography>
            )
          )}

          <VistaPreviaPlato plato={platoPrevio} />

          <Box>
            <FormControlLabel
              control={
                <Checkbox
                  checked={alergenosRevisados}
                  onChange={(e) => setAlergenosRevisados(e.target.checked)}
                />
              }
              label={
                <Typography sx={{ fontSize: 14 }}>
                  He revisado los alérgenos y la dieta de este plato
                </Typography>
              }
            />
            {!alergenosRevisados && (
              <Typography sx={{ fontSize: 12.5, color: "text.secondary", mt: 0.5 }}>
                Mientras no lo marques, la carta mostrará «consultar alérgenos» en este plato y el
                chat no se lo recomendará a quien tenga alergias o siga una dieta.
              </Typography>
            )}
          </Box>

          {aviso && <Alert severity="error">{aviso}</Alert>}

          <Stack direction="row" spacing={1}>
            <Button variant="contained" disabled={guardando} onClick={guardar}>
              Guardar
            </Button>
            <Button variant="outlined" onClick={onCancelar}>
              Cancelar
            </Button>
            {puedeEliminar && (
              <Button variant="outlined" color="error" onClick={eliminar}>
                Eliminar plato
              </Button>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
