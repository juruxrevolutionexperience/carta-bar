-- Esquema de contabilidad de uso del LLM.
-- Idempotente: se puede aplicar tantas veces como haga falta.

CREATE TABLE IF NOT EXISTS uso_llm (
    id                      BIGSERIAL PRIMARY KEY,
    restaurante_id          TEXT        NOT NULL,
    llamada                 TEXT        NOT NULL,
    modelo                  TEXT        NOT NULL,
    tokens_entrada          INTEGER     NOT NULL DEFAULT 0,
    tokens_salida           INTEGER     NOT NULL DEFAULT 0,
    tokens_cache_escritura  INTEGER     NOT NULL DEFAULT 0,
    tokens_cache_lectura    INTEGER     NOT NULL DEFAULT 0,
    -- NUMERIC y no DOUBLE: con dinero, el redondeo binario acaba en
    -- descuadres al sumar miles de filas de fracciones de centimo.
    coste_usd               NUMERIC(14, 8) NOT NULL DEFAULT 0,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- La consulta caliente es "cuanto lleva gastado HOY este restaurante",
-- y se ejecuta antes de cada pregunta: sin este indice es un escaneo completo.
CREATE INDEX IF NOT EXISTS idx_uso_llm_restaurante_fecha
    ON uso_llm (restaurante_id, creado_en DESC);

-- NOTA: la Row Level Security que aisla unos restaurantes de otros se activa
-- en el paso 4, junto con los roles. Activarla ahora, sin politicas definidas,
-- bloquearia todos los accesos.
