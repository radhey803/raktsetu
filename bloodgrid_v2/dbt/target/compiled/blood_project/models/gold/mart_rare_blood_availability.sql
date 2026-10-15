

/*
================================================================================
MART RARE BLOOD AVAILABILITY
================================================================================
Tracks life-critical rare blood phenotypes:
1. Bombay Blood Group (Oh+ / Oh-)
2. Rh-Negative Phenotypes (O-, A-, B-, AB-)
Includes direct facility contact info and location for emergency dispatch.
================================================================================
*/

WITH rare_stock AS (
    SELECT
        s.hospital_code,
        s.component_name,
        s.blood_group,
        s.units,
        s.source_updated_at,
        s.last_synced_at
    FROM "blood_warehouse"."main_gold"."fct_stock_current" s
    WHERE s.blood_group IN (
        'Bombay (Oh+)',
        'Bombay (Oh-)',
        'O-',
        'A-',
        'B-',
        'AB-'
    )
      AND s.units > 0
)

SELECT
    r.hospital_code,
    b.hospital_name,
    b.hospital_type,
    b.state_name,
    b.district_name,
    b.hospital_contact,
    b.hospital_address,
    r.component_name,
    r.blood_group,
    r.units,
    CASE 
        WHEN r.blood_group LIKE 'Bombay%' THEN 'ULTRA_RARE_BOMBAY'
        ELSE 'RH_NEGATIVE'
    END AS rarity_tier,
    r.source_updated_at,
    r.last_synced_at
FROM rare_stock r
JOIN "blood_warehouse"."main_gold"."dim_blood_banks" b ON r.hospital_code = b.hospital_code
ORDER BY 
    CASE WHEN r.blood_group LIKE 'Bombay%' THEN 1 ELSE 2 END,
    r.units DESC