

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
    FROM "blood_warehouse"."bronze"."raw_inventory"
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
    
CASE
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%OH+%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%OHPOS%' 
      OR UPPER(string_split(pair, ':')[1]) LIKE '%BOMBAY%OH+%' THEN 'Bombay (Oh+)'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%OH-%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%OHNEG%' 
      OR UPPER(string_split(pair, ':')[1]) LIKE '%BOMBAY%OH-%' THEN 'Bombay (Oh-)'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%OH%' 
      OR UPPER(string_split(pair, ':')[1]) LIKE '%BOMBAY%' THEN 'Bombay (Oh+)'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'AB+%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%AB+VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%ABPOS%' THEN 'AB+'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'AB-%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%AB-VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%ABNEG%' THEN 'AB-'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'A+%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%A+VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%APOS%' THEN 'A+'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'A-%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%A-VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%ANEG%' THEN 'A-'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'B+%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%B+VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%BPOS%' THEN 'B+'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'B-%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%B-VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%BNEG%' THEN 'B-'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'O+%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%O+VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%OPOS%' THEN 'O+'
    WHEN UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE 'O-%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%O-VE%' 
      OR UPPER(REPLACE(string_split(pair, ':')[1], ' ', '')) LIKE '%ONEG%' THEN 'O-'
    ELSE TRIM(string_split(pair, ':')[1])
END
 AS blood_group,
    GREATEST(0, COALESCE(TRY_CAST(TRIM(string_split(pair, ':')[2]) AS INTEGER), 0)) AS units,
    source_updated_at
FROM pairs
WHERE pair LIKE '%:%'
  AND TRIM(string_split(pair, ':')[1]) != ''