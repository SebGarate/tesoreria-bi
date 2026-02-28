-- ============================================================
-- PROYECTO: Automatización de Reportes de Tesorería
-- Archivo:  consultas_tesoreria.sql
-- Autor:    Sebastian Garate
-- Desc:     Consultas SQL para análisis operativo de tesorería
-- ============================================================

-- ============================================================
-- 0. CREACIÓN DE TABLAS (ejecutar una sola vez)
-- ============================================================

CREATE TABLE IF NOT EXISTS productos (
    producto_id      SERIAL PRIMARY KEY,
    nombre_producto  VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS movimientos (
    id_movimiento   SERIAL PRIMARY KEY,
    fecha           DATE          NOT NULL,
    producto_id     INT           REFERENCES productos(producto_id),
    tipo_operacion  VARCHAR(10)   CHECK (tipo_operacion IN ('ingreso','egreso')),
    monto           NUMERIC(15,2) NOT NULL,
    moneda          VARCHAR(3)    CHECK (moneda IN ('PEN','USD')),
    contraparte     VARCHAR(50),
    descripcion     VARCHAR(100)
);

-- ============================================================
-- 1. FLUJO NETO DIARIO
--    Ingresos - Egresos agrupados por fecha y moneda
-- ============================================================

SELECT
    fecha,
    moneda,
    SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE 0 END) AS total_ingresos,
    SUM(CASE WHEN tipo_operacion = 'egreso'  THEN monto ELSE 0 END) AS total_egresos,
    SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END) AS flujo_neto
FROM movimientos
GROUP BY fecha, moneda
ORDER BY fecha, moneda;


-- ============================================================
-- 2. POSICIÓN DE LIQUIDEZ ACUMULADA
--    Saldo acumulado día a día (útil para gráfico de línea)
-- ============================================================

SELECT
    fecha,
    moneda,
    SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END) AS flujo_neto_dia,
    SUM(SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END))
        OVER (PARTITION BY moneda ORDER BY fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        AS saldo_acumulado
FROM movimientos
GROUP BY fecha, moneda
ORDER BY fecha, moneda;


-- ============================================================
-- 3. ANÁLISIS POR PRODUCTO (JOIN con tabla productos)
--    Total movido y conteo de operaciones por producto
-- ============================================================

SELECT
    p.nombre_producto,
    m.moneda,
    COUNT(m.id_movimiento)                                        AS n_operaciones,
    SUM(CASE WHEN m.tipo_operacion = 'ingreso' THEN m.monto ELSE 0 END) AS total_ingresos,
    SUM(CASE WHEN m.tipo_operacion = 'egreso'  THEN m.monto ELSE 0 END) AS total_egresos,
    ROUND(
        SUM(CASE WHEN m.tipo_operacion = 'ingreso' THEN m.monto ELSE 0 END) /
        NULLIF(COUNT(m.id_movimiento), 0), 2
    ) AS ticket_promedio_ingreso
FROM movimientos m
JOIN productos p ON m.producto_id = p.producto_id
GROUP BY p.nombre_producto, m.moneda
ORDER BY total_ingresos DESC;


-- ============================================================
-- 4. TOP 5 CONTRAPARTES POR VOLUMEN OPERADO
-- ============================================================

SELECT
    contraparte,
    COUNT(*)               AS n_operaciones,
    SUM(monto)             AS volumen_total,
    ROUND(AVG(monto), 2)   AS monto_promedio
FROM movimientos
GROUP BY contraparte
ORDER BY volumen_total DESC
LIMIT 5;


-- ============================================================
-- 5. RESUMEN SEMANAL — FLUJO POR SEMANA Y PRODUCTO
--    Para identificar semanas de mayor/menor liquidez
-- ============================================================

SELECT
    DATE_TRUNC('week', fecha)::DATE AS semana_inicio,
    p.nombre_producto,
    moneda,
    SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END) AS flujo_neto_semana
FROM movimientos m
JOIN productos p ON m.producto_id = p.producto_id
GROUP BY DATE_TRUNC('week', fecha), p.nombre_producto, moneda
ORDER BY semana_inicio, p.nombre_producto;


-- ============================================================
-- 6. ALERTA DE LIQUIDEZ DIARIA
--    Días donde el flujo neto en PEN fue negativo (riesgo)
-- ============================================================

SELECT
    fecha,
    SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END) AS flujo_neto_pen,
    CASE
        WHEN SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END) < 0
        THEN '⚠ ALERTA: Flujo negativo'
        ELSE 'OK'
    END AS estado_liquidez
FROM movimientos
WHERE moneda = 'PEN'
GROUP BY fecha
HAVING SUM(CASE WHEN tipo_operacion = 'ingreso' THEN monto ELSE -monto END) < 0
ORDER BY flujo_neto_pen ASC;