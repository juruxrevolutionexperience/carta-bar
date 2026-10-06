import { useEffect, useMemo, useRef, useState } from "react";

import "./estilos.css";
import { Carrusel } from "./Carrusel";
import { CartaProvider, useCartaContext } from "./CartaContext";
import { Chat } from "./Chat";
import { EntrarMesaDialog } from "./EntrarMesaDialog";
import { ListaPlatos } from "./ListaPlatos";
import { MesaProvider, useMesaContext } from "./MesaContext";
import { MiLista } from "./MiLista";
import { PanelPedidoMesa } from "./PanelPedidoMesa";
import { Portada } from "./Portada";
import { colorSeguro } from "./seguridad";
import { SelectorIdioma } from "./SelectorIdioma";
import { useListaCliente } from "./useListaCliente";
import { useVisorFoto } from "./useVisorFoto";
import { VisorFoto } from "./VisorFoto";

const DURACION_ACEPTADA_MS = 4000;

// Lo que el cliente ve de un vistazo en el movil: si el camarero aun no ha
// aceptado la mesa, si ya la acepto (un aviso breve con vibracion), o si ha
// pedido la cuenta. Sustituye a la barra fina de antes.
function BarraMesa() {
  const { mesa } = useMesaContext();
  const [aceptadaRecien, setAceptadaRecien] = useState(false);
  const estadoAnterior = useRef<string | null>(null);

  useEffect(() => {
    const actual = mesa?.estado ?? null;
    const anterior = estadoAnterior.current;
    estadoAnterior.current = actual;
    if (anterior !== "por_confirmar" || actual !== "abierta") return;
    setAceptadaRecien(true);
    try {
      navigator.vibrate?.([120, 80, 120]);
    } catch {
      // Sin vibracion (escritorio, iOS): el cambio de color sigue avisando.
    }
    const id = window.setTimeout(() => setAceptadaRecien(false), DURACION_ACEPTADA_MS);
    return () => window.clearTimeout(id);
  }, [mesa?.estado]);

  if (!mesa || mesa.estado === "cerrada") return null;

  let clase = "tarjeta-mesa";
  let titulo = "Mesa abierta";
  let detalle = "Podéis pedir lo que queráis desde la carta.";
  if (mesa.estado === "por_confirmar") {
    clase += " esperando";
    titulo = "Esperando al camarero";
    detalle = "Os avisamos en cuanto os acepte la mesa.";
  } else if (mesa.estado === "cuenta_pedida") {
    clase += " cuenta";
    titulo = "Cuenta pedida";
    detalle = "El camarero viene a cobrar.";
  } else if (aceptadaRecien) {
    clase += " aceptada";
    titulo = "¡Mesa aceptada!";
    detalle = "Ya podéis hacer vuestro pedido.";
  }

  return (
    <div className={clase} role="status" aria-live="polite">
      <strong>
        Mesa {mesa.mesa} · {titulo}
      </strong>
      <span>{detalle}</span>
    </div>
  );
}

function CartaApp() {
  const { carta, config, idioma, categoriasVisibles, cargando, t } = useCartaContext();
  const { mesa } = useMesaContext();
  const [categoriaId, setCategoriaId] = useState<string | null>(null);
  const visor = useVisorFoto();
  const lista = useListaCliente();
  const enMesa = mesa !== null && mesa.estado !== "cerrada";

  // Orden del "escaparate" del visor: todos los platos disponibles, categoria
  // a categoria en el mismo orden que la carta, para que las flechas naveguen
  // igual que si se fuera bajando por la carta entera.
  const platosEnOrden = useMemo(() => {
    const resultado = [];
    for (const cat of categoriasVisibles) {
      for (const p of carta) {
        if (p.categoria === cat.id && p.disponible) resultado.push(p);
      }
    }
    return resultado;
  }, [carta, categoriasVisibles]);

  // Efectos de pagina completa: titulo de la pestaña, idioma del documento
  // (para lectores de pantalla) y el color de marca del restaurante, que
  // afecta a elementos fuera de la portada (el lanzador del chat, focus...).
  useEffect(() => {
    if (config.nombre) document.title = config.nombre;
  }, [config.nombre]);

  useEffect(() => {
    if (idioma) document.documentElement.lang = idioma;
  }, [idioma]);

  useEffect(() => {
    const marca = colorSeguro(config.color_marca);
    if (marca) document.documentElement.style.setProperty("--marca", marca);
  }, [config.color_marca]);

  // Al terminar de cargar (o al cambiar de idioma), si la categoria activa
  // ya no existe o todavia no hay ninguna elegida, se selecciona la primera
  // visible — igual que hace aplicarIdioma() con el "aria-selected" de hoy.
  useEffect(() => {
    if (cargando) return;
    setCategoriaId((actual) => {
      if (actual && categoriasVisibles.some((c) => c.id === actual)) return actual;
      return categoriasVisibles[0]?.id ?? null;
    });
  }, [cargando, categoriasVisibles]);

  if (cargando) return null;

  return (
    <>
      <BarraMesa />
      <div className="app">
        <Portada />

        <h2 className="seccion-tit">{t("menu")}</h2>
        <Carrusel categoriaSeleccionada={categoriaId} onSeleccionar={setCategoriaId} />

        <div className="divisor"></div>

        <ListaPlatos
          categoriaId={categoriaId}
          onAbrirFoto={visor.abrir}
          onAnadirALista={lista.anadir}
        />

        <p className="pie">
          {config.aviso_alergenos_i18n?.[idioma] || config.aviso_alergenos || ""}
        </p>
      </div>

      <Chat />
      <VisorFoto
        platoId={visor.platoId}
        platos={platosEnOrden}
        onNavegar={visor.abrir}
        onCerrar={() => visor.cerrar(false)}
      />
      {enMesa ? <PanelPedidoMesa /> : <MiLista lista={lista} />}
      <SelectorIdioma />
      <EntrarMesaDialog />
    </>
  );
}

export function App() {
  return (
    <CartaProvider>
      <MesaProvider>
        <CartaApp />
      </MesaProvider>
    </CartaProvider>
  );
}
