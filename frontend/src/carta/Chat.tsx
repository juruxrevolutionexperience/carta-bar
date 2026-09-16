import { useEffect, useRef, useState, type FormEvent } from "react";

import { preguntar as preguntarApi } from "./api";
import { useCartaContext } from "./CartaContext";
import { formatearNegritas } from "./formatearNegritas";
import type { MensajeUI, TurnoHistorial } from "./types";

// Web Speech API: el reconocimiento lo hace el navegador, asi que no pasa por
// el backend, no consume tokens y no cuesta nada. Solo lo soportan Chrome,
// Edge y Safari; en el resto el boton se queda oculto y el chat funciona
// igual escribiendo. Requiere HTTPS (o localhost) para pedir permiso de
// microfono.
const MotorVoz = window.SpeechRecognition || window.webkitSpeechRecognition;
const VOZ_IDIOMA: Record<string, string> = { es: "es-ES", en: "en-US", de: "de-DE", fr: "fr-FR" };

// Desactivado tras la prueba en produccion: daba problemas. Reactivar
// cambiando esta constante a true cuando se retome (ver APARCADO en
// docs/PENDIENTE.md: "Transcripcion de voz en el servidor, para iPhone").
const MICROFONO_ACTIVADO = false;

const MAX_HISTORIAL = 8;
const MAX_MENSAJE = 1000;

export function Chat() {
  const { idioma, t, textos } = useCartaContext();

  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState<MensajeUI[]>([]);
  const [chatIniciado, setChatIniciado] = useState(false);
  const [entrada, setEntrada] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [escuchando, setEscuchando] = useState(false);

  const historialRef = useRef<TurnoHistorial[]>([]);
  const entradaRef = useRef<HTMLInputElement>(null);
  const hiloRef = useRef<HTMLDivElement>(null);
  const reconocedorRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (hiloRef.current) hiloRef.current.scrollTop = hiloRef.current.scrollHeight;
  }, [mensajes]);

  function recordar(rol: TurnoHistorial["rol"], texto: string) {
    historialRef.current = [
      ...historialRef.current,
      { rol, texto: texto.slice(0, MAX_MENSAJE) },
    ].slice(-MAX_HISTORIAL);
  }

  function abrir() {
    setAbierto(true);
    setTimeout(() => entradaRef.current?.focus(), 320);
  }

  async function enviarPregunta(texto: string) {
    if (!texto) return;

    setMensajes((actual) => {
      const base = !chatIniciado ? [{ rol: "bot" as const, texto: t("bienvenida_chat") }] : actual;
      return [...base, { rol: "yo", texto }, { rol: "bot", texto: "", pendiente: true }];
    });
    setChatIniciado(true);
    setEntrada("");
    setEnviando(true);

    try {
      const respuesta = await preguntarApi(texto, idioma, historialRef.current);
      setMensajes((actual) => [...actual.slice(0, -1), { rol: "bot", texto: respuesta }]);
      recordar("cliente", texto);
      recordar("asistente", respuesta);
    } catch {
      setMensajes((actual) => [...actual.slice(0, -1), { rol: "bot", texto: t("error_chat") }]);
    } finally {
      setEnviando(false);
      entradaRef.current?.focus();
    }
  }

  function alEnviar(e: FormEvent) {
    e.preventDefault();
    enviarPregunta(entrada.trim());
  }

  // --------------------------------------------------------- dictado voz

  function pintarMicro(activo: boolean) {
    setEscuchando(activo);
  }

  function escuchar() {
    if (!MotorVoz) return;
    const reconocedor = new MotorVoz();
    reconocedorRef.current = reconocedor;
    reconocedor.lang = VOZ_IDIOMA[idioma] || "es-ES";
    reconocedor.interimResults = true; // el texto va apareciendo mientras habla
    reconocedor.continuous = false; // se corta solo al terminar la frase
    reconocedor.maxAlternatives = 1;

    reconocedor.onresult = (e) => {
      let dicho = "";
      for (const tramo of e.results) dicho += tramo[0].transcript;
      const recortado = dicho.slice(0, 500); // el mismo tope que valida el backend
      setEntrada(recortado);
      if (e.results[e.results.length - 1].isFinal) {
        pintarMicro(false);
        reconocedor.stop();
        if (recortado.trim()) enviarPregunta(recortado.trim());
      }
    };
    reconocedor.onerror = (e) => {
      pintarMicro(false);
      // Denegado el permiso, el navegador ya no vuelve a preguntar: el boton
      // solo puede fallar otra vez, asi que no se vuelve a mostrar aqui (se
      // controla con MICROFONO_ACTIVADO, hoy en false de todas formas).
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        setMensajes((actual) => [...actual, { rol: "bot", texto: t("voz_sin_permiso") }]);
      }
    };
    reconocedor.onend = () => pintarMicro(false);

    reconocedor.start();
    pintarMicro(true);
  }

  function alPulsarMicro() {
    if (escuchando) {
      reconocedorRef.current?.stop();
      pintarMicro(false);
      return;
    }
    try {
      escuchar();
    } catch {
      pintarMicro(false);
    }
  }

  const sugerencias = textos.sugerencias || [];

  return (
    <>
      <button className="lanzador" aria-label={t("preguntar")} onClick={abrir}>
        <span className="punto"></span>
        💬
      </button>

      <section className={"panel" + (abierto ? " abierto" : "")} aria-hidden={!abierto}>
        <div className="panel-top">
          <h2>{t("titulo_chat")}</h2>
          <button className="cerrar" aria-label="Cerrar" onClick={() => setAbierto(false)}>
            ×
          </button>
        </div>
        <div className="hilo" ref={hiloRef}>
          {!chatIniciado && <div className="msg bot">{t("bienvenida_chat")}</div>}
          {mensajes.map((m, i) => (
            <div className={"msg " + m.rol} key={i}>
              {m.pendiente ? (
                <span className="puntos">
                  <span></span>
                  <span></span>
                  <span></span>
                </span>
              ) : (
                formatearNegritas(m.texto)
              )}
            </div>
          ))}
        </div>
        <div className="sugerencias">
          {sugerencias.map((txt) => (
            <button
              className="sug"
              key={txt}
              onClick={() => {
                setEntrada(txt);
                enviarPregunta(txt);
              }}
            >
              {txt}
            </button>
          ))}
        </div>
        <form className="barra" onSubmit={alEnviar}>
          <input
            ref={entradaRef}
            placeholder={escuchando ? t("voz_escuchando") : t("escribe")}
            autoComplete="off"
            value={entrada}
            onChange={(e) => setEntrada(e.target.value)}
          />
          <button
            type="button"
            className={"microfono" + (escuchando ? " escuchando" : "")}
            aria-pressed={escuchando}
            aria-label={escuchando ? t("voz_parar") : t("voz_hablar")}
            title={escuchando ? t("voz_parar") : t("voz_hablar")}
            hidden={!(MICROFONO_ACTIVADO && MotorVoz)}
            onClick={MICROFONO_ACTIVADO && MotorVoz ? alPulsarMicro : undefined}
          >
            🎤
          </button>
          <button type="submit" disabled={enviando}>
            {t("enviar")}
          </button>
        </form>
      </section>
    </>
  );
}
