{{config (materialized = 'view')}}
SELECT
    TRIM("hospitalname") AS hospital_name,
    TRIM("hospitaladd") AS hospital_address,
    TRIM("hospitalcontact") AS hospital_contact,
    TRY_CAST ("hospitalCode" AS INTEGER) AS hospital_code,
    TRIM("hospitalType") AS hospital_type,
    TRIM("type") AS facility_type,
    TRIM("State") AS state_name,
    TRIM("District") AS district_name,
    TRY_CAST ("entrydate" AS TIMESTAMP) AS last_updated_at,
    TRIM("available_WithQty") AS available_stock,
    TRIM("not_available_WithQty") AS unavailable_stock,
    TRIM("components") AS components_raw,
    TRY_CAST ("count" AS INTEGER) AS record_count,
    TRY_CAST ("moderateStock" AS INTEGER) AS moderate_stock_flag,
    "ingested_at"
FROM
    {{source ('bronze', 'raw_blood_inventory')}}
WHERE
    "hospitalname" IS NOT NULL
    AND "State" IS NOT NULL
    AND TRIM("State") != ''