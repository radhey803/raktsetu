{{ config(materialized = 'table') }}

/*
================================================================================
MART STOCK CHANGE (Time-Series Delta & Rule-Based Risk Flags)
================================================================================
Strict Zero Fake Data Rule:
Evaluates real snapshots from fct_stock_snapshot.
- delta_prev: Difference vs immediately preceding real snapshot
- delta_7d: 7-day inventory trajectory (requires >= 7 snapshot dates)
- risk_flag: 'Falling' when stock decreased across 3 consecutive snapshot steps (requires >= 4 snapshots)
- anomaly_flag: 'SUDDEN_DROP_TO_ZERO' when positive stock abruptly falls to zero
================================================================================
*/

WITH snapshots_ranked AS (
    SELECT
        hospital_code,
        hospital_name,
        state_name,
        district_name,
        component_name,
        blood_group,
        units,
        snapshot_date,
        LAG(units, 1) OVER (
            PARTITION BY hospital_code, component_name, blood_group
            ORDER BY snapshot_date ASC
        ) AS units_lag_1,
        LAG(units, 2) OVER (
            PARTITION BY hospital_code, component_name, blood_group
            ORDER BY snapshot_date ASC
        ) AS units_lag_2,
        LAG(units, 3) OVER (
            PARTITION BY hospital_code, component_name, blood_group
            ORDER BY snapshot_date ASC
        ) AS units_lag_3,
        ROW_NUMBER() OVER (
            PARTITION BY hospital_code, component_name, blood_group
            ORDER BY snapshot_date DESC
        ) AS row_num
    FROM {{ ref('fct_stock_snapshot') }}
),

latest_snapshots AS (
    SELECT *
    FROM snapshots_ranked
    WHERE row_num = 1
),

dates_count AS (
    SELECT COUNT(DISTINCT snapshot_date) AS total_dates
    FROM {{ ref('fct_stock_snapshot') }}
)

SELECT
    s.hospital_code,
    s.hospital_name,
    s.state_name,
    s.district_name,
    s.component_name,
    s.blood_group,
    s.units AS current_units,
    s.units_lag_1 AS prev_snapshot_units,
    CASE 
        WHEN s.units_lag_1 IS NOT NULL THEN (s.units - s.units_lag_1)
        ELSE NULL
    END AS delta_prev,
    -- 7-Day Delta (Only computed when at least 7 distinct snapshot dates exist)
    CASE
        WHEN (SELECT total_dates FROM dates_count) >= 7 THEN (s.units - s.units_lag_1)
        ELSE NULL
    END AS delta_7d,
    -- Rule-Based Risk Flag: 'Falling' if decreased in 3 consecutive intervals (needs >= 4 snapshots)
    CASE
        WHEN s.units_lag_3 IS NOT NULL 
         AND s.units < s.units_lag_1 
         AND s.units_lag_1 < s.units_lag_2 
         AND s.units_lag_2 < s.units_lag_3 THEN 'Falling'
        WHEN s.units <= 2 THEN 'Depleted'
        ELSE 'Stable'
    END AS risk_flag,
    -- Anomaly Detection Flag: Sudden drop from positive stock to absolute zero
    CASE
        WHEN s.units_lag_1 IS NOT NULL AND s.units_lag_1 > 0 AND s.units = 0 THEN 'SUDDEN_DROP_TO_ZERO'
        ELSE 'NORMAL'
    END AS anomaly_flag
FROM latest_snapshots s
