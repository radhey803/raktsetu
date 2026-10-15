

SELECT
    hospital_name,
    hospital_address,
    hospital_contact,
    hospital_code,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    TRY_CAST(entry_date_raw AS TIMESTAMP) AS last_updated_at,
    components_raw,
    ingested_at
FROM "blood_warehouse"."bronze"."raw_inventory"
WHERE hospital_name IS NOT NULL
  AND state_name IS NOT NULL