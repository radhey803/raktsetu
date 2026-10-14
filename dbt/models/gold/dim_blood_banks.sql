{{ config(materialized = 'table') }}

SELECT
    hospital_code,
    hospital_name,
    hospital_address,
    hospital_contact,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    source_updated_at,
    scraped_at AS lakehouse_ingested_at
FROM {{ ref('stg_blood_banks') }}