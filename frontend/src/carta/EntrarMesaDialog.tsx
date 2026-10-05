import { useState } from "react";

import { useCartaContext } from "./CartaContext";
import { useMesaContext } from "./MesaContext";

// Se ve justo al escanear el QR de una mesa, antes de entrar: pide el nombre
// para que luego, en el pedido de la mesa, se sepa quien pidio que (en vez de
// "Comensal 2"). "Entrar sin decirlo" sigue funcionando igual que antes.
export function EntrarMesaDialog() {
  const { pidiendoNombre, entrar } = useMesaContext();
  const { mostrarSelectorIdioma } = useCartaContext();
  const [nombre, setNombre] = useState("");

  // Primero el idioma, luego el nombre: los dos son un "velo" a pantalla
  // completa y, si se vieran a la vez, este se pintaria encima sin dejar a
  // un turista elegir su idioma antes de que le pregunten como se llama.
  if (!pidiendoNombre || mostrarSelectorIdioma) return null;

  function confirmar() {
    entrar(nombre);
  }

  return (
    <div className="velo">
      <div className="caja-idioma">
        <h2>¡Bienvenido a la mesa!</h2>
        <p>Dinos tu nombre para saber quién ha pedido qué.</p>
        <input
          className="nota-propuesta"
          type="text"
          autoFocus
          placeholder="Tu nombre"
          maxLength={40}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && confirmar()}
        />
        <button type="button" className="boton-proponer" onClick={confirmar}>
          Entrar
        </button>
        <button type="button" className="vaciar-lista" onClick={() => entrar("")}>
          Seguir sin decirlo
        </button>
      </div>
    </div>
  );
}
