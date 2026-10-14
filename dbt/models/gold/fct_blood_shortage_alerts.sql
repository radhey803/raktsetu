{{config (materialized = 'table')}}
WITH
    base_data AS (
        SELECT
            hospital_code,
            hospital_name,
            hospital_type,
            state_name,
            district_name,
            last_updated_at,
            available_stock,
            unavailable_stock,
            moderate_stock_flag,
            DATE_DIFF('day', last_updated_at, CURRENT_TIMESTAMP) AS days_since_last_update
        FROM
            {{ref ('stg_blood_inventory')}}
    )
SELECT
    hospital_code,
    hospital_name,
    hospital_type,
    state_name,
    district_name,
    last_updated_at,
    days_since_last_update,
    moderate_stock_flag,
    CASE
        WHEN days_since_last_update > 30 THEN 'CRITICALLY STALE (>30 days)'
        WHEN days_since_last_update > 7 THEN 'OUTDATED (>7 days)'
        ELSE 'CURRENT'
    END AS data_freshness_status,
    CASE
        WHEN moderate_stock_flag = 1 THEN 'MODERATE DEFICIT REPORTED'
        ELSE 'NORMAL / NO REPORT'
    END AS stock_alert_level
FROM
    base_data