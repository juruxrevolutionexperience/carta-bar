import { useCallback, useEffect, useState } from "react";

import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

const COLOR_ESTADO: Record<string, string> = {
  por_confirmar: "warning.main",
  cuenta_pedida: "info.main",
  abierta: "primary.main",
  libre: "divider",
};

import { cargarMesas, cargarZonas, type Mesa, type Zona } from "./api";
import { PanelServicio } from "./PanelServicio";
import {
  TEXTO_ESTADO,
  agruparPorZona,
  contarPorEstado,
  estadoDe,
  personas,
  tiempoDesde,
} from "./servicioUtil";

// Más a menudo que el plano (8 s): aquí se está esperando a que aparezca una
// mesa por aceptar. El tiempo real de verdad llega con las comandas.
const REFRESCO_MS = 5000;

const TODAS = "todas";

// Lo que pide atencion sale primero: una mesa por aceptar bloquea al cliente
// que espera, una cuenta pedida bloquea la salida; abiertas y libres despues.
const PRIORIDAD: Record<string, number> = {
  por_confirmar: 0,
  cuenta_pedida: 1,
  abierta: 2,
  libre: 3,
};

function porUrgencia(a: Mesa, b: Mesa): number {
  return PRIORIDAD[estadoDe(a)] - PRIORIDAD[estadoDe(b)];
}

// El día a día de la sala: las mismas mesas y zonas del plano, pero en
// tarjetas grandes separadas por zona, para ver de un vistazo qué está libre,
// qué hay que aceptar y qué está abierto. El plano queda para montar el local.
export function SeccionServicio() {
  const [zonas, setZonas] = useState<Zona[] | null>(null);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [error, setError] = useState(false);
  const [filtro, setFiltro] = useState<string>(TODAS);
  const [seleccionada, setSeleccionada] = useState<string | null>(null);
  const [ahora, setAhora] = useState(() => Date.now());

  const recargar = useCallback(() => {
    Promise.all([cargarZonas(), cargarMesas()])
      .then(([zonasCargadas, mesasCargadas]) => {
        setZonas(zonasCargadas);
        setMesas(mesasCargadas);
        setAhora(Date.now());
        setError(false);
        setFiltro((actual) =>
          actual === TODAS || zonasCargadas.some((z) => z.id === actual) ? actual : TODAS
        );
      })
      .catch(() => setError(true));
  }, []);

  useEffect(recargar, [recargar]);

  useEffect(() => {
    const id = window.setInterval(() => {
      if (!document.hidden) recargar();
    }, REFRESCO_MS);
    return () => window.clearInterval(id);
  }, [recargar]);

  if (zonas === null) {
    return (
      <Card>
        <CardContent>
          <p>{error ? "No se pudieron cargar las mesas." : "Cargando mesas…"}</p>
        </CardContent>
      </Card>
    );
  }

  if (mesas.length === 0) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h3" sx={{ mb: 1 }}>
            Aún no hay mesas
          </Typography>
          <p>Monta el local en "Mesas" (el plano) y aquí aparecerán para el servicio.</p>
        </CardContent>
      </Card>
    );
  }

  const grupos = agruparPorZona(zonas, mesas)
    .filter((g) => g.mesas.length > 0 && (filtro === TODAS || g.zona.id === filtro))
    .map((g) => ({ ...g, mesas: [...g.mesas].sort(porUrgencia) }));
  const cuenta = contarPorEstado(mesas);
  const elegida = mesas.find((m) => m.id === seleccionada) ?? null;

  return (
    <div className="servicio">
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }} aria-live="polite">
        {cuenta.por_confirmar > 0 && (
          <Chip
            label={`${cuenta.por_confirmar} por aceptar`}
            color="warning"
            variant="outlined"
            size="small"
          />
        )}
        {cuenta.cuenta_pedida > 0 && (
          <Chip
            label={`${cuenta.cuenta_pedida} piden la cuenta`}
            color="info"
            variant="outlined"
            size="small"
          />
        )}
        <Chip
          label={`${cuenta.abierta} ${cuenta.abierta === 1 ? "abierta" : "abiertas"}`}
          color="primary"
          variant="outlined"
          size="small"
        />
        <Chip
          label={`${cuenta.libre} ${cuenta.libre === 1 ? "libre" : "libres"}`}
          variant="outlined"
          size="small"
        />
        {error && <Chip label="Sin conexión" color="error" variant="outlined" size="small" />}
      </Box>

      {zonas.length > 1 && (
        <Tabs
          value={filtro}
          onChange={(_, valor) => setFiltro(valor)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ mb: 2, minHeight: 36, "& .MuiTab-root": { minHeight: 36 } }}
        >
          <Tab value={TODAS} label="Todas" />
          {zonas.map((z) => {
            const avisos = mesas.filter(
              (m) => m.zona_id === z.id && estadoDe(m) === "por_confirmar"
            ).length;
            return (
              <Tab
                key={z.id}
                value={z.id}
                label={
                  avisos > 0 ? (
                    <Badge color="warning" variant="dot">
                      <Box sx={{ pr: 1 }}>{z.nombre}</Box>
                    </Badge>
                  ) : (
                    z.nombre
                  )
                }
              />
            );
          })}
        </Tabs>
      )}

      <div className="zona-trabajo">
        <div>
          {grupos.map(({ zona, mesas: deLaZona }) => {
            const ocupadas = deLaZona.filter((m) => estadoDe(m) !== "libre").length;
            return (
              <section key={zona.id} className="grupo-servicio">
                <h2 className="titulo-zona-servicio">
                  {zona.nombre}
                  <span>
                    {ocupadas}/{deLaZona.length}
                  </span>
                </h2>
                <div className="rejilla-mesas">
                  {deLaZona.map((m) => {
                    const estado = estadoDe(m);
                    const tiempo = tiempoDesde(m.abierta_en, ahora);
                    const elegida = m.id === seleccionada;
                    return (
                      <ButtonBase
                        key={m.id}
                        onClick={() => setSeleccionada(m.id)}
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "flex-start",
                          gap: 0.5,
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: "background.paper",
                          border: 2,
                          borderColor: elegida ? "primary.main" : COLOR_ESTADO[estado],
                          boxShadow: elegida ? 3 : 0,
                          textAlign: "left",
                        }}
                      >
                        <Typography sx={{ fontSize: 14.5, fontWeight: 700 }}>
                          {m.nombre}
                        </Typography>
                        <Typography sx={{ fontSize: 12.5, fontWeight: 600, color: COLOR_ESTADO[estado] }}>
                          {TEXTO_ESTADO[estado]}
                        </Typography>
                        <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                          {estado === "libre"
                            ? `${m.capacidad} ${m.capacidad === 1 ? "plaza" : "plazas"}`
                            : [m.comensales ? personas(m.comensales) : "", tiempo]
                                .filter(Boolean)
                                .join(" · ")}
                        </Typography>
                      </ButtonBase>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>

        {elegida ? (
          <PanelServicio
            key={elegida.id}
            mesa={elegida}
            ahora={ahora}
            onCambio={recargar}
            onCerrar={() => setSeleccionada(null)}
          />
        ) : (
          <Card className="panel-vacio">
            <CardContent>
              <p>Toca una mesa para abrirla, aceptarla o liberarla.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
