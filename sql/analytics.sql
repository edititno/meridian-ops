-- Operations analytics queries
-- Each query powers a dashboard panel. Written in portable ANSI SQL.

-- 1. SUPPLIER PERFORMANCE: on-time delivery rate and avg delay by supplier
-- name: supplier_performance
SELECT
    s.name AS supplier,
    s.region,
    COUNT(*) AS shipments,
    ROUND(AVG(CASE WHEN sh.delivered_date <= sh.promised_date THEN 1.0 ELSE 0.0 END) * 100, 1) AS on_time_pct,
    ROUND(AVG(GREATEST(sh.delivered_date - sh.promised_date, 0))::numeric, 1) AS avg_delay_days
FROM shipments sh
JOIN suppliers s ON s.supplier_id = sh.supplier_id
WHERE sh.delivered_date IS NOT NULL
GROUP BY s.name, s.region
ORDER BY on_time_pct DESC;

-- 2. LEAD TIME ANALYSIS: promised vs actual lead time trend by month
-- name: lead_time_trend
SELECT
    DATE_TRUNC('month', sh.promised_date)::date AS month,
    ROUND(AVG(sh.delivered_date - sh.promised_date)::numeric, 2) AS avg_slip_days,
    COUNT(*) AS shipments
FROM shipments sh
WHERE sh.delivered_date IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- 3. INVENTORY POSITION: latest on-hand vs trailing 30-day demand (weeks of supply)
-- name: inventory_position
WITH latest_inv AS (
    SELECT DISTINCT ON (product_id) product_id, on_hand, snapshot_date
    FROM inventory
    ORDER BY product_id, snapshot_date DESC
),
recent_demand AS (
    SELECT product_id, SUM(quantity) AS qty_30d
    FROM orders
    WHERE order_date >= (SELECT MAX(order_date) FROM orders) - INTERVAL '30 days'
    GROUP BY product_id
)
SELECT
    p.sku,
    p.name,
    li.on_hand,
    COALESCE(rd.qty_30d, 0) AS demand_30d,
    CASE WHEN COALESCE(rd.qty_30d, 0) = 0 THEN NULL
         ELSE ROUND(li.on_hand / (rd.qty_30d / 4.29), 1)
    END AS weeks_of_supply
FROM latest_inv li
JOIN products p ON p.product_id = li.product_id
LEFT JOIN recent_demand rd ON rd.product_id = li.product_id
ORDER BY weeks_of_supply ASC NULLS LAST;

-- 4. COSTED BOM: material cost per unit and margin by product
-- name: costed_bom
SELECT
    p.sku,
    p.name,
    p.unit_price,
    ROUND(SUM(b.qty_per_unit * c.unit_cost), 2) AS material_cost,
    ROUND(p.unit_price - SUM(b.qty_per_unit * c.unit_cost), 2) AS unit_margin,
    ROUND((p.unit_price - SUM(b.qty_per_unit * c.unit_cost)) / p.unit_price * 100, 1) AS margin_pct
FROM products p
JOIN bom b ON b.product_id = p.product_id
JOIN components c ON c.component_id = b.component_id
GROUP BY p.sku, p.name, p.unit_price
ORDER BY margin_pct ASC;

-- 5. DEMAND HISTORY: weekly units by product (feeds the forecasting model)
-- name: weekly_demand
SELECT
    p.sku,
    DATE_TRUNC('week', o.order_date)::date AS week,
    SUM(o.quantity) AS units
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_date < DATE_TRUNC('week', (SELECT MAX(order_date) FROM orders))
GROUP BY p.sku, 2
ORDER BY p.sku, week;

-- 6. REVENUE KPIs: trailing totals for the exec header
-- name: kpi_summary
SELECT
    COUNT(DISTINCT o.order_id) AS orders_90d,
    SUM(o.quantity) AS units_90d,
    ROUND(SUM(o.quantity * p.unit_price), 0) AS revenue_90d
FROM orders o
JOIN products p ON p.product_id = o.product_id
WHERE o.order_date >= (SELECT MAX(order_date) FROM orders) - INTERVAL '90 days';
