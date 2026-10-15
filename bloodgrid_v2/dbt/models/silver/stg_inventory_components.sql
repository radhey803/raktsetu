{{ config(materialized = 'view') }}

WITH base AS (
    SELECT
        run_id,
        scraped_at,
        hospital_code,
        TRIM(hospital_name) AS hospital_name,
        TRIM(state_name) AS state_name,
        TRIM(district_name) AS district_name,
        TRY_CAST(entry_date_raw AS TIMESTAMP) AS source_updated_at,
        CAST(components_raw AS JSON) AS comp_json
    FROM {{ source('bronze', 'raw_inventory') }}
    WHERE components_raw IS NOT NULL
      AND hospital_code IS NOT NULL
      AND LENGTH(components_raw) > 5
),

component_keys AS (
    SELECT 
        run_id,
        scraped_at,
        hospital_code,
        hospital_name,
        state_name,
        district_name,
        source_updated_at,
        comp_json,
        UNNEST(json_keys(comp_json)) AS component_name
    FROM base
),

avail_strings AS (
    SELECT 
        run_id,
        scraped_at,
        hospital_code,
        hospital_name,
        state_name,
        district_name,
        source_updated_at,
        component_name,
        (comp_json -> component_name) ->> 'available_WithQty' AS avail_str
    FROM component_keys
),

pairs AS (
    SELECT 
        run_id,
        scraped_at,
        hospital_code,
        hospital_name,
        state_name,
        district_name,
        source_updated_at,
        component_name,
        UNNEST(string_split(avail_str, ',')) AS pair
    FROM avail_strings
    WHERE avail_str IS NOT NULL 
      AND TRIM(avail_str) != ''
)

SELECT 
    run_id,
    scraped_at,
    hospital_code,
    hospital_name,
    state_name,
    district_name,
    TRIM(component_name) AS component_name,
    {{ normalize_blood_group("string_split(pair, ':')[1]") }} AS blood_group,
    GREATEST(0, COALESCE(TRY_CAST(TRIM(string_split(pair, ':')[2]) AS INTEGER), 0)) AS units,
    source_updated_at
FROM pairs
WHERE pair LIKE '%:%'
  AND TRIM(string_split(pair, ':')[1]) != ''
