{{config (materialized = 'table')}}
WITH
    ranked_hospitals AS (
        SELECT
            hospital_code,
            hospital_name,
            hospital_address,
            hospital_contact,
            hospital_type,
            facility_type,
            state_name,
            district_name,
            last_updated_at,
            ROW_NUMBER() OVER (
                PARTITION BY
                    hospital_code
                ORDER BY
                    last_updated_at DESC NULLS LAST
            ) AS rn
        FROM
            {{ref ('stg_blood_inventory')}}
        WHERE
            hospital_code IS NOT NULL
    )
SELECT
    hospital_code,
    hospital_name,
    hospital_address,
    hospital_contact,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    last_updated_at
FROM
    ranked_hospitals
WHERE
    rn = 1