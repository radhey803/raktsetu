

WITH facility_units AS (
    SELECT
        hospital_code,
        SUM(units) AS total_units
    FROM "blood_warehouse"."main_gold"."fct_stock_current"
    GROUP BY hospital_code
),

base_data AS (
    SELECT
        b.hospital_code,
        b.hospital_name,
        b.hospital_type,
        b.state_name,
        b.district_name,
        b.source_updated_at AS last_updated_at,
        COALESCE(u.total_units, 0) AS total_units,
        DATE_DIFF('day', b.source_updated_at, CURRENT_TIMESTAMP) AS days_since_last_update
    FROM "blood_warehouse"."main_silver"."stg_blood_banks" b
    LEFT JOIN facility_units u ON b.hospital_code = u.hospital_code
)

SELECT
    hospital_code,
    hospital_name,
    hospital_type,
    state_name,
    district_name,
    last_updated_at,
    days_since_last_update,
    total_units,
    CASE
        WHEN days_since_last_update > 30 THEN 'CRITICALLY STALE (>30 days)'
        WHEN days_since_last_update > 7 THEN 'OUTDATED (>7 days)'
        ELSE 'CURRENT'
    END AS data_freshness_status,
    CASE
        WHEN total_units = 0 THEN 'CRITICAL DEPLETION (0 Units)'
        WHEN total_units <= 5 THEN 'MODERATE DEFICIT REPORTED'
        ELSE 'NORMAL / NO REPORT'
    END AS stock_alert_level
FROM base_data