{{ config(materialized = 'table') }}

-- eRaktKosh omits blood groups that have run out, so a series missing from a bank's
-- latest scrape is reported as 0 units instead of carrying its last non-zero value forward.
WITH latest_scrape AS (
    SELECT hospital_code, lakehouse_ingested_at AS latest_at
    FROM {{ ref('dim_blood_banks') }}
),
ranked AS (
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
    FROM {{ ref('fct_stock_snapshot') }}
)
SELECT
    r.hospital_code,
    r.hospital_name,
    r.state_name,
    r.district_name,
    r.component_name,
    r.blood_group,
    CASE WHEN r.snapshot_at >= l.latest_at THEN r.units ELSE 0 END AS units,
    r.source_updated_at,
    COALESCE(l.latest_at, r.snapshot_at) AS last_synced_at
FROM ranked r
LEFT JOIN latest_scrape l ON r.hospital_code = l.hospital_code
WHERE r.rn = 1
