
  
  create view "blood_warehouse"."main_silver"."stg_blood_banks__dbt_tmp" as (
    

WITH ranked AS (
    SELECT
        run_id,
        scraped_at,
        hospital_code,
        TRIM(hospital_name) AS hospital_name,
        TRIM(hospital_address) AS hospital_address,
        TRIM(hospital_contact) AS hospital_contact,
        TRIM(hospital_type) AS hospital_type,
        TRIM(facility_type) AS facility_type,
        TRIM(state_name) AS state_name,
        TRIM(district_name) AS district_name,
        TRY_CAST(entry_date_raw AS TIMESTAMP) AS source_updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY hospital_code
            ORDER BY scraped_at DESC, TRY_CAST(entry_date_raw AS TIMESTAMP) DESC NULLS LAST
        ) AS rn
    FROM "blood_warehouse"."bronze"."raw_inventory"
    WHERE hospital_code IS NOT NULL
      AND hospital_name IS NOT NULL
      AND state_name IS NOT NULL
)

SELECT
    run_id,
    scraped_at,
    hospital_code,
    hospital_name,
    hospital_address,
    hospital_contact,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    source_updated_at
FROM ranked
WHERE rn = 1
  );
