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

-- Tienda ficticia: no se registran pagos ni datos bancarios.
CREATE TABLE IF NOT EXISTS productos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    precio NUMERIC(10, 2) NOT NULL CHECK (precio >= 0),
    stock INTEGER NOT NULL CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS pedidos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id BIGINT NOT NULL REFERENCES clientes(id),
    producto_id TEXT NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 10),
    precio_unitario NUMERIC(10, 2) NOT NULL CHECK (precio_unitario >= 0),
    estado TEXT NOT NULL DEFAULT 'simulado' CHECK (estado = 'simulado'),
    creado TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_pedidos_cliente ON pedidos(cliente_id);

CREATE TABLE IF NOT EXISTS reclamos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id BIGINT NOT NULL UNIQUE REFERENCES tickets(id),
    pedido_id BIGINT REFERENCES pedidos(id),
    producto_id TEXT REFERENCES productos(id),
    creado TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- La revisión original permanece intacta. Cada corrección es un evento nuevo.
CREATE TABLE IF NOT EXISTS correcciones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    revision_id BIGINT NOT NULL REFERENCES revisiones(id),
    decision TEXT NOT NULL CHECK (decision IN ('aprobar', 'editar', 'rechazar')),
    texto_final TEXT NOT NULL DEFAULT '',
    motivo TEXT NOT NULL,
    operador TEXT NOT NULL,
    creado TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_correcciones_revision ON correcciones(revision_id, id);

-- Conversaciones ficticias visibles para cliente y soporte. Las propuestas de IA
-- nunca se insertan aqui: solo una decision humana o un mensaje del operador.
CREATE TABLE IF NOT EXISTS mensajes_reclamo (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES reclamos(ticket_id),
    autor TEXT NOT NULL CHECK (autor IN ('cliente', 'soporte')),
    texto TEXT NOT NULL CHECK (char_length(btrim(texto)) BETWEEN 1 AND 8000),
    creado TIMESTAMPTZ NOT NULL DEFAULT now(),
    ejecucion_id BIGINT REFERENCES ejecuciones(id),
    rectifica_id BIGINT REFERENCES mensajes_reclamo(id),
    motivo TEXT,
    vigente BOOLEAN NOT NULL DEFAULT TRUE,
    tipo TEXT NOT NULL DEFAULT 'mensaje'
        CHECK (tipo IN ('inicio', 'mensaje', 'revision', 'rectificacion'))
);

CREATE INDEX IF NOT EXISTS ix_mensajes_reclamo_ticket
    ON mensajes_reclamo(ticket_id, id);

-- Al actualizar una base existente, cada reclamo conserva su primer mensaje.
INSERT INTO mensajes_reclamo (ticket_id, autor, texto, creado, tipo)
SELECT r.ticket_id, 'cliente', t.texto, t.creado, 'inicio'
FROM reclamos AS r JOIN tickets AS t ON t.id = r.ticket_id
WHERE NOT EXISTS (
    SELECT 1 FROM mensajes_reclamo AS m
    WHERE m.ticket_id = r.ticket_id AND m.autor = 'cliente'
);

-- Las respuestas anteriores a esta version tambien aparecen en el chat.
INSERT INTO mensajes_reclamo (ticket_id, autor, texto, creado, ejecucion_id, tipo)
SELECT e.ticket_id, 'soporte',
       COALESCE(c.texto_final, v.texto_final),
       COALESCE(c.creado, v.creado), e.id, 'revision'
FROM revisiones AS v
JOIN ejecuciones AS e ON e.id = v.ejecucion_id
JOIN reclamos AS r ON r.ticket_id = e.ticket_id
LEFT JOIN LATERAL (
    SELECT decision, texto_final, creado
    FROM correcciones WHERE revision_id = v.id ORDER BY id DESC LIMIT 1
) AS c ON TRUE
WHERE COALESCE(c.decision, v.decision) IN ('aprobar', 'editar')
  AND NOT EXISTS (
    SELECT 1 FROM mensajes_reclamo AS m WHERE m.ejecucion_id = e.id
  );
