-- Operations Analytics Dashboard: PostgreSQL schema
-- Snowflake-compatible ANSI SQL where possible

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id     SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    region          TEXT NOT NULL,
    avg_lead_days   NUMERIC(5,1) NOT NULL,
    reliability     NUMERIC(3,2) NOT NULL CHECK (reliability BETWEEN 0 AND 1)
);

CREATE TABLE IF NOT EXISTS products (
    product_id      SERIAL PRIMARY KEY,
    sku             TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    unit_price      NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS components (
    component_id    SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    supplier_id     INT NOT NULL REFERENCES suppliers(supplier_id),
    unit_cost       NUMERIC(10,2) NOT NULL
);

-- Costed bill of materials: which components make up each product
CREATE TABLE IF NOT EXISTS bom (
    product_id      INT NOT NULL REFERENCES products(product_id),
    component_id    INT NOT NULL REFERENCES components(component_id),
    qty_per_unit    INT NOT NULL,
    PRIMARY KEY (product_id, component_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        SERIAL PRIMARY KEY,
    product_id      INT NOT NULL REFERENCES products(product_id),
    order_date      DATE NOT NULL,
    quantity        INT NOT NULL,
    channel         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    product_id      INT NOT NULL REFERENCES products(product_id),
    snapshot_date   DATE NOT NULL,
    on_hand         INT NOT NULL,
    PRIMARY KEY (product_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id     SERIAL PRIMARY KEY,
    supplier_id     INT NOT NULL REFERENCES suppliers(supplier_id),
    component_id    INT NOT NULL REFERENCES components(component_id),
    promised_date   DATE NOT NULL,
    delivered_date  DATE,
    quantity        INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_shipments_supplier ON shipments(supplier_id);
