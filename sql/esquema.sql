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

-- Esquema de la carta: cimiento del panel de gestion (Fase 3). Antes de esto
-- la carta vivia en ficheros JSON dentro de la imagen Docker; cambiar un
-- precio exigia reconstruir y redesplegar.

CREATE TABLE IF NOT EXISTS restaurantes (
    id                   TEXT PRIMARY KEY,
    nombre               TEXT NOT NULL,
    subtitulo            TEXT NOT NULL DEFAULT '',
    color_marca          TEXT NOT NULL DEFAULT '#000000',
    moneda               TEXT NOT NULL DEFAULT '€',
    foto_portada         TEXT NOT NULL DEFAULT '',
    logo                 TEXT NOT NULL DEFAULT '',
    aviso_alergenos      TEXT NOT NULL DEFAULT '',
    aviso_alergenos_i18n JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS categorias (
    restaurante_id TEXT NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    id             TEXT NOT NULL,
    nombre         TEXT NOT NULL,
    -- El frontend (web/index.html) ya lee nombre_i18n si existe; hasta ahora
    -- no habia dato que ponerle y caia siempre al nombre en espanol.
    nombre_i18n    JSONB NOT NULL DEFAULT '{}',
    orden          INTEGER NOT NULL,
    PRIMARY KEY (restaurante_id, id)
);

CREATE TABLE IF NOT EXISTS platos (
    restaurante_id TEXT NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    id             TEXT NOT NULL,
    categoria_id   TEXT NOT NULL,
    nombre         TEXT NOT NULL,
    descripcion    TEXT NOT NULL,
    -- NULL = "precio a consultar" (ver carta_bar.modelos.Plato).
    precio         NUMERIC(10,2),
    ingredientes   JSONB NOT NULL DEFAULT '[]',
    alergenos      JSONB NOT NULL DEFAULT '[]',
    vegano         BOOLEAN NOT NULL DEFAULT false,
    vegetariano    BOOLEAN NOT NULL DEFAULT false,
    sin_gluten     BOOLEAN NOT NULL DEFAULT false,
    sin_lactosa    BOOLEAN NOT NULL DEFAULT false,
    disponible     BOOLEAN NOT NULL DEFAULT true,
    etiqueta       TEXT,
    foto           TEXT,
    PRIMARY KEY (restaurante_id, id),
    FOREIGN KEY (restaurante_id, categoria_id)
        REFERENCES categorias(restaurante_id, id)
);

CREATE TABLE IF NOT EXISTS traducciones_platos (
    restaurante_id TEXT NOT NULL,
    plato_id       TEXT NOT NULL,
    idioma         TEXT NOT NULL,
    -- Hash de nombre+descripcion+ingredientes en espanol: si no cambia,
    -- traducir_carta() no vuelve a gastar en traducir (carta_bar.traductor).
    hash           TEXT NOT NULL,
    nombre         TEXT NOT NULL,
    descripcion    TEXT NOT NULL,
    ingredientes   JSONB NOT NULL DEFAULT '[]',
    PRIMARY KEY (restaurante_id, plato_id, idioma),
    FOREIGN KEY (restaurante_id, plato_id)
        REFERENCES platos(restaurante_id, id) ON DELETE CASCADE
);
