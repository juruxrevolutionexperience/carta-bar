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

-- NULL = sin contrasena establecida todavia (ver scripts/establecer_clave_admin.py).
-- Nunca guarda la contrasena en claro: pbkdf2_sha256$<iteraciones>$<sal>$<hash>.
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS clave_hash TEXT;

-- Texto de la hoja imprimible del QR ("Escanea para ver la carta"). Vacio =
-- se usa el texto por defecto.
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS texto_qr TEXT NOT NULL DEFAULT '';

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

-- El restaurante ha revisado los alergenos y la dieta del plato. Los platos que
-- ya existian se dan por revisados (default true); los nuevos entran sin
-- confirmar desde el codigo. Ver carta_bar.modelos.Plato.
ALTER TABLE platos ADD COLUMN IF NOT EXISTS alergenos_confirmados BOOLEAN NOT NULL DEFAULT true;

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

-- Metricas de uso: contadores por dia, no una fila por evento. No guardan
-- IPs ni el texto de las preguntas (pueden contener datos de salud). El dia
-- es el de España (ver metricas.py).
CREATE TABLE IF NOT EXISTS visitas_diarias (
    restaurante_id TEXT    NOT NULL,
    dia            DATE    NOT NULL,
    visitas        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (restaurante_id, dia)
);

-- preguntas = respondidas; conversaciones = las que empezaron sin historial;
-- rechazadas = cortadas por el tope diario de gasto.
CREATE TABLE IF NOT EXISTS preguntas_diarias (
    restaurante_id TEXT    NOT NULL,
    dia            DATE    NOT NULL,
    idioma         TEXT    NOT NULL,
    preguntas      INTEGER NOT NULL DEFAULT 0,
    conversaciones INTEGER NOT NULL DEFAULT 0,
    rechazadas     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (restaurante_id, dia, idioma)
);

-- Pedido en mesa (docs/PEDIDO-EN-MESA.md), primer bloque: mesas y sesiones.
-- El resto (propuestas, comandas, tickets) llega en el siguiente bloque.

CREATE TABLE IF NOT EXISTS mesas (
    restaurante_id TEXT NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    id             TEXT NOT NULL,
    nombre         TEXT NOT NULL,
    token_qr       TEXT NOT NULL UNIQUE,
    activa         BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (restaurante_id, id)
);

-- Plano del local: zonas (Terraza, Salon 1...) y, en cada mesa, su forma,
-- tamano y posicion. x, y, ancho y alto se miden en casillas de la
-- cuadricula del plano. Una mesa con activa = false esta "borrada" pero se
-- conserva porque tiene sesiones en el historico (nada se borra).
CREATE TABLE IF NOT EXISTS zonas (
    restaurante_id TEXT NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    id             TEXT NOT NULL,
    nombre         TEXT NOT NULL,
    orden          INTEGER NOT NULL,
    PRIMARY KEY (restaurante_id, id)
);

ALTER TABLE mesas ADD COLUMN IF NOT EXISTS zona_id   TEXT;
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS forma     TEXT    NOT NULL DEFAULT 'cuadrada';
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS x         REAL    NOT NULL DEFAULT 0;
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS y         REAL    NOT NULL DEFAULT 0;
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS ancho     REAL    NOT NULL DEFAULT 2;
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS alto      REAL    NOT NULL DEFAULT 2;
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS rotacion  INTEGER NOT NULL DEFAULT 0;
ALTER TABLE mesas ADD COLUMN IF NOT EXISTS capacidad INTEGER NOT NULL DEFAULT 4;

-- El plano paso de 12 x 9 casillas gordas a 48 x 30 unidades finas (como un
-- TPV: el local entero a la vista y mesas pequenas). plano_version dice en que
-- medida esta guardada cada zona: las que siguen en la 1 se convierten una sola
-- vez (posiciones x4 y x3, tamanos x1,5 redondeados hacia arriba, con lo que
-- ninguna mesa se sale ni se monta sobre otra) y pasan a la 2. Las zonas
-- nuevas nacen ya en la 2, asi que este bloque no las toca al reiniciar.
ALTER TABLE zonas ADD COLUMN IF NOT EXISTS plano_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE zonas ALTER COLUMN plano_version SET DEFAULT 2;

WITH pasadas AS (
    UPDATE zonas SET plano_version = 2 WHERE plano_version = 1
    RETURNING restaurante_id, id
)
UPDATE mesas m
SET x = m.x * 4, y = m.y * 3,
    ancho = CEIL(m.ancho * 1.5), alto = CEIL(m.alto * 1.5)
FROM pasadas p
WHERE m.restaurante_id = p.restaurante_id AND m.zona_id = p.id;

CREATE TABLE IF NOT EXISTS sesiones_mesa (
    id             TEXT PRIMARY KEY,
    restaurante_id TEXT NOT NULL,
    mesa_id        TEXT NOT NULL,
    estado         TEXT NOT NULL,
    abierta_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrada_en     TIMESTAMPTZ,
    FOREIGN KEY (restaurante_id, mesa_id) REFERENCES mesas(restaurante_id, id)
);

-- Solo una sesion abierta por mesa. Si dos personas escanean a la vez, decide
-- este indice, no un "if" en Python: el segundo INSERT falla y se une como
-- invitado a la que ya creo el primero.
CREATE UNIQUE INDEX IF NOT EXISTS una_sesion_abierta_por_mesa
    ON sesiones_mesa (restaurante_id, mesa_id)
    WHERE estado != 'cerrada';

CREATE TABLE IF NOT EXISTS comensales (
    id         TEXT PRIMARY KEY,
    sesion_id  TEXT NOT NULL REFERENCES sesiones_mesa(id) ON DELETE CASCADE,
    nombre     TEXT NOT NULL,
    rol        TEXT NOT NULL,
    idioma     TEXT NOT NULL DEFAULT 'es',
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bloque 1 del flujo de mesa (docs/PEDIDO-EN-MESA.md, "Bloque 1 en detalle").
-- estado admite ademas 'por_confirmar': la abrio un cliente con el QR y el
-- camarero aun no la ha aceptado (no hace falta tocar nada: estado es TEXT).
-- ultima_actividad nace en now() para las sesiones que ya existian, asi el
-- cierre automatico de 4 h empieza a contar desde que se aplica esto.
ALTER TABLE sesiones_mesa ADD COLUMN IF NOT EXISTS abierta_por           TEXT NOT NULL DEFAULT 'cliente';
ALTER TABLE sesiones_mesa ADD COLUMN IF NOT EXISTS comensales_declarados INTEGER;
ALTER TABLE sesiones_mesa ADD COLUMN IF NOT EXISTS confirmada_en         TIMESTAMPTZ;
ALTER TABLE sesiones_mesa ADD COLUMN IF NOT EXISTS ultima_actividad      TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE sesiones_mesa ADD COLUMN IF NOT EXISTS motivo_cierre         TEXT;
ALTER TABLE comensales    ADD COLUMN IF NOT EXISTS expulsado_en          TIMESTAMPTZ;

-- RLS activada en todas las tablas y SIN politicas: la clave publica (anon) y
-- las autenticadas de Supabase no pueden leer ni escribir nada. La app entra
-- con el usuario `postgres`, que se salta RLS (rolbypassrls = true, comprobado
-- el 2026-09-23). Toda tabla nueva debe anadir aqui su ENABLE.
ALTER TABLE uso_llm              ENABLE ROW LEVEL SECURITY;
ALTER TABLE restaurantes         ENABLE ROW LEVEL SECURITY;
ALTER TABLE categorias           ENABLE ROW LEVEL SECURITY;
ALTER TABLE platos               ENABLE ROW LEVEL SECURITY;
ALTER TABLE traducciones_platos  ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitas_diarias      ENABLE ROW LEVEL SECURITY;
ALTER TABLE preguntas_diarias    ENABLE ROW LEVEL SECURITY;
ALTER TABLE zonas                ENABLE ROW LEVEL SECURITY;
ALTER TABLE mesas                ENABLE ROW LEVEL SECURITY;
ALTER TABLE sesiones_mesa        ENABLE ROW LEVEL SECURITY;
ALTER TABLE comensales           ENABLE ROW LEVEL SECURITY;
