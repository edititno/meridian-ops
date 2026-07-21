"""ETL pipeline: generates realistic operational data and loads it into the database.

Run once after creating the schema:
    python src/etl.py
Uses DATABASE_URL env var (PostgreSQL). Falls back to local SQLite for dev.
"""
import os
import random
import datetime as dt

from db import get_engine, IS_SQLITE
from sqlalchemy import text

random.seed(42)

SUPPLIERS = [
    ("Cascade Components", "North America", 12, 0.94),
    ("Baltic Precision", "Europe", 21, 0.88),
    ("Shenzen Microparts", "Asia", 28, 0.81),
    ("Ridgeline Plastics", "North America", 9, 0.97),
    ("Aria Circuits", "Asia", 25, 0.76),
]

PRODUCTS = [
    ("SKU-1001", "TrailScout GPS Collar", "Wearables", 189.00),
    ("SKU-1002", "PulseBand Fitness Tracker", "Wearables", 129.00),
    ("SKU-1003", "HomeBase Charging Dock", "Accessories", 49.00),
    ("SKU-1004", "AeroSense Air Monitor", "Sensors", 99.00),
    ("SKU-1005", "NightWatch Camera Module", "Sensors", 159.00),
]

COMPONENTS = [
    ("GPS module", 1, 22.50), ("LTE modem", 5, 18.00), ("Li-ion battery", 3, 6.40),
    ("Molded casing", 4, 3.10), ("PCB assembly", 5, 11.75), ("OLED display", 3, 9.20),
    ("Accelerometer", 2, 4.80), ("Charging coil", 4, 2.90), ("Camera sensor", 5, 14.60),
    ("Air quality sensor", 2, 8.30),
]

# product -> list of (component_index, qty)
BOM = {
    1: [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)],
    2: [(3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1)],
    3: [(4, 1), (8, 2), (5, 1)],
    4: [(4, 1), (5, 1), (10, 1), (3, 1)],
    5: [(4, 1), (5, 1), (9, 1), (3, 1)],
}

START = dt.date.today() - dt.timedelta(days=540)
DAYS = 540

# Weekly seasonality + growth + product-level demand profiles
BASE_DEMAND = {1: 14, 2: 22, 3: 9, 4: 7, 5: 5}


def seasonal_factor(d: dt.date) -> float:
    dow = 1.25 if d.weekday() < 5 else 0.6            # weekday vs weekend
    month = 1.45 if d.month in (11, 12) else (0.85 if d.month in (1, 2) else 1.0)
    return dow * month


def main():
    engine = get_engine()
    with engine.begin() as conn:
        # Schema
        ddl_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
        ddl = open(ddl_path).read()
        if IS_SQLITE:
            ddl = ddl.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
            ddl = ddl.replace("NUMERIC(5,1)", "REAL").replace("NUMERIC(3,2)", "REAL").replace("NUMERIC(10,2)", "REAL")
        for stmt in ddl.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))

        # Idempotency: wipe existing rows
        for t in ["shipments", "inventory", "orders", "bom", "components", "products", "suppliers"]:
            conn.execute(text(f"DELETE FROM {t}"))

        for i, (name, region, lead, rel) in enumerate(SUPPLIERS, 1):
            conn.execute(text(
                "INSERT INTO suppliers (supplier_id, name, region, avg_lead_days, reliability) "
                "VALUES (:i, :n, :r, :l, :rel)"), dict(i=i, n=name, r=region, l=lead, rel=rel))

        for i, (sku, name, cat, price) in enumerate(PRODUCTS, 1):
            conn.execute(text(
                "INSERT INTO products (product_id, sku, name, category, unit_price) "
                "VALUES (:i, :s, :n, :c, :p)"), dict(i=i, s=sku, n=name, c=cat, p=price))

        for i, (name, sup, cost) in enumerate(COMPONENTS, 1):
            conn.execute(text(
                "INSERT INTO components (component_id, name, supplier_id, unit_cost) "
                "VALUES (:i, :n, :s, :c)"), dict(i=i, n=name, s=sup, c=cost))

        for pid, parts in BOM.items():
            for cid, qty in parts:
                conn.execute(text(
                    "INSERT INTO bom (product_id, component_id, qty_per_unit) VALUES (:p, :c, :q)"),
                    dict(p=pid, c=cid, q=qty))

        # Orders: daily, with noise, trend, seasonality
        for day in range(DAYS):
            d = START + dt.timedelta(days=day)
            growth = 1.0 + 0.35 * (day / DAYS)
            for pid, base in BASE_DEMAND.items():
                lam = base * seasonal_factor(d) * growth
                qty = max(0, int(random.gauss(lam, lam * 0.35)))
                if qty == 0:
                    continue
                channel = random.choices(["direct", "retail", "distributor"], [0.5, 0.3, 0.2])[0]
                conn.execute(text(
                    "INSERT INTO orders (product_id, order_date, quantity, channel) "
                    "VALUES (:p, :d, :q, :ch)"), dict(p=pid, d=d, q=qty, ch=channel))

        # Weekly inventory snapshots: start high, drain with demand, replenish
        on_hand = {pid: BASE_DEMAND[pid] * 60 for pid in BASE_DEMAND}
        for day in range(0, DAYS, 7):
            d = START + dt.timedelta(days=day)
            for pid in BASE_DEMAND:
                weekly_demand = int(BASE_DEMAND[pid] * 7 * seasonal_factor(d))
                on_hand[pid] = max(0, on_hand[pid] - weekly_demand)
                if on_hand[pid] < BASE_DEMAND[pid] * 20:          # reorder point
                    on_hand[pid] += BASE_DEMAND[pid] * random.randint(35, 55)
                conn.execute(text(
                    "INSERT INTO inventory (product_id, snapshot_date, on_hand) VALUES (:p, :d, :o)"),
                    dict(p=pid, d=d, o=on_hand[pid]))

        # Shipments: supplier reliability drives lateness
        for _ in range(600):
            sup_idx = random.randint(1, len(SUPPLIERS))
            _, _, lead, rel = SUPPLIERS[sup_idx - 1]
            comp = random.choice([i for i, c in enumerate(COMPONENTS, 1) if c[1] == sup_idx] or [1])
            promised = START + dt.timedelta(days=random.randint(0, DAYS - 1))
            slip = 0 if random.random() < rel else random.randint(1, 14)
            delivered = promised + dt.timedelta(days=slip)
            conn.execute(text(
                "INSERT INTO shipments (supplier_id, component_id, promised_date, delivered_date, quantity) "
                "VALUES (:s, :c, :p, :d, :q)"),
                dict(s=sup_idx, c=comp, p=promised, d=delivered, q=random.randint(100, 1200)))

    print("ETL complete: suppliers, products, BOMs, orders, inventory, shipments loaded.")


if __name__ == "__main__":
    main()
