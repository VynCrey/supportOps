CREATE TABLE IF NOT EXISTS clientes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT NOT NULL,
    plan TEXT NOT NULL CHECK (plan IN ('Basic', 'Pro', 'Enterprise'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(id),
    texto TEXT NOT NULL CHECK (char_length(btrim(texto)) BETWEEN 10 AND 4000),
    categoria_real TEXT,
    familia TEXT,
    prioridad TEXT NOT NULL DEFAULT 'media'
        CHECK (prioridad IN ('baja', 'media', 'alta')),
    estado TEXT NOT NULL DEFAULT 'abierto'
        CHECK (estado IN ('abierto', 'resuelto')),
    creado TIMESTAMPTZ NOT NULL DEFAULT now(),
    primera_respuesta TIMESTAMPTZ,
    resuelto TIMESTAMPTZ,
    CHECK (primera_respuesta IS NULL OR primera_respuesta >= creado),
    CHECK (resuelto IS NULL OR resuelto >= creado),
    CHECK (resuelto IS NULL OR primera_respuesta IS NULL
           OR resuelto >= primera_respuesta)
);

CREATE INDEX IF NOT EXISTS ix_tickets_cliente ON tickets(cliente_id);

CREATE TABLE IF NOT EXISTS eventos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES tickets(id),
    tipo TEXT NOT NULL,
    momento TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_eventos_ticket ON eventos(ticket_id);

CREATE TABLE IF NOT EXISTS documentos (
    id TEXT PRIMARY KEY,
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    texto TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_documentos_categoria ON documentos(categoria);

CREATE TABLE IF NOT EXISTS relaciones (
    origen TEXT NOT NULL,
    relacion TEXT NOT NULL,
    destino TEXT NOT NULL,
    PRIMARY KEY (origen, relacion, destino)
);

CREATE TABLE IF NOT EXISTS ejecuciones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES tickets(id),
    creado TIMESTAMPTZ NOT NULL DEFAULT now(),
    resultado JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ejecuciones_ticket ON ejecuciones(ticket_id);

CREATE TABLE IF NOT EXISTS revisiones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ejecucion_id BIGINT NOT NULL UNIQUE REFERENCES ejecuciones(id),
    decision TEXT NOT NULL CHECK (decision IN ('aprobar', 'editar', 'rechazar')),
    texto_final TEXT NOT NULL DEFAULT '',
    motivo TEXT NOT NULL,
    creado TIMESTAMPTZ NOT NULL DEFAULT now()
);
