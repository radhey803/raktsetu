

WITH ranked AS (
    SELECT
        hospital_code,
        hospital_name,
        state_name,
        district_name,
        component_name,
        blood_group,
        units,
        source_updated_at,
        snapshot_at,
        ROW_NUMBER() OVER (
            PARTITION BY hospital_code, component_name, blood_group
            ORDER BY snapshot_at DESC, source_updated_at DESC NULLS LAST
        ) AS rn
    FROM "blood_warehouse"."main_gold"."fct_stock_snapshot"
)

SELECT
    hospital_code,
    hospital_name,
    state_name,
    district_name,
    component_name,
    blood_group,
    units,
    source_updated_at,
    snapshot_at AS last_synced_at
FROM ranked
WHERE rn = 1