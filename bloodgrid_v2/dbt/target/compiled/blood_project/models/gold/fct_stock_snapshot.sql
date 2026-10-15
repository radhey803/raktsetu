

SELECT
    hospital_code,
    hospital_name,
    state_name,
    district_name,
    component_name,
    blood_group,
    units,
    source_updated_at,
    scraped_at AS snapshot_at,
    CAST(scraped_at AS DATE) AS snapshot_date
FROM "blood_warehouse"."main_silver"."stg_inventory_components"


    WHERE scraped_at > (SELECT COALESCE(MAX(snapshot_at), '1970-01-01'::TIMESTAMP) FROM "blood_warehouse"."main_gold"."fct_stock_snapshot")
