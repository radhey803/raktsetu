
    

    create  table
      "blood_warehouse"."main_gold"."mart_reliability_score__dbt_tmp"
  
    
    as (
      

/*
================================================================================
MART RELIABILITY SCORE FORMULA (0 - 100 Points)
================================================================================
1. Freshness Score (Max 50 Points):
   - Last updated within 24 hours (<= 1 day): 50 pts
   - Last updated within 7 days (2 to 7 days): 35 pts
   - Last updated within 30 days (8 to 30 days): 15 pts
   - Critically stale (> 30 days or NULL): 0 pts

2. Valid Contact Score (Max 25 Points):
   - Contains phone number (matches digits >= 8): 25 pts
   - Has street address but unverified phone: 10 pts
   - Missing both contact and address: 0 pts

3. Component Completeness Score (Max 25 Points):
   - Tracks >= 3 distinct blood components (PRBC, Platelets, FFP, etc.): 25 pts
   - Tracks 1 or 2 blood components: 15 pts
   - No components reported: 0 pts
================================================================================
*/

WITH facility_components AS (
    SELECT
        hospital_code,
        COUNT(DISTINCT component_name) AS distinct_components_count,
        SUM(units) AS total_units_in_stock
    FROM "blood_warehouse"."main_gold"."fct_stock_current"
    GROUP BY hospital_code
),

base_facilities AS (
    SELECT
        b.hospital_code,
        b.hospital_name,
        b.hospital_type,
        b.facility_type,
        b.state_name,
        b.district_name,
        b.hospital_contact,
        b.hospital_address,
        b.source_updated_at,
        DATE_DIFF('day', b.source_updated_at, CURRENT_TIMESTAMP) AS days_since_update,
        COALESCE(c.distinct_components_count, 0) AS distinct_components_count,
        COALESCE(c.total_units_in_stock, 0) AS total_units_in_stock
    FROM "blood_warehouse"."main_gold"."dim_blood_banks" b
    LEFT JOIN facility_components c ON b.hospital_code = c.hospital_code
),

scored AS (
    SELECT
        hospital_code,
        hospital_name,
        hospital_type,
        facility_type,
        state_name,
        district_name,
        hospital_contact,
        hospital_address,
        source_updated_at,
        days_since_update,
        distinct_components_count,
        total_units_in_stock,
        -- 1. Freshness Points (0-50)
        CASE
            WHEN days_since_update <= 1 THEN 50
            WHEN days_since_update <= 7 THEN 35
            WHEN days_since_update <= 30 THEN 15
            ELSE 0
        END AS freshness_points,
        -- 2. Contact Points (0-25)
        CASE
            WHEN hospital_contact LIKE '%Phone%' OR regexp_matches(hospital_contact, '[0-9]{8,}') THEN 25
            WHEN hospital_address IS NOT NULL AND LENGTH(hospital_address) > 10 THEN 10
            ELSE 0
        END AS contact_points,
        -- 3. Component Completeness Points (0-25)
        CASE
            WHEN distinct_components_count >= 3 THEN 25
            WHEN distinct_components_count >= 1 THEN 15
            ELSE 0
        END AS completeness_points
    FROM base_facilities
)

SELECT
    hospital_code,
    hospital_name,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    hospital_contact,
    hospital_address,
    source_updated_at,
    days_since_update,
    distinct_components_count,
    total_units_in_stock,
    freshness_points,
    contact_points,
    completeness_points,
    (freshness_points + contact_points + completeness_points) AS reliability_score,
    CASE
        WHEN (freshness_points + contact_points + completeness_points) >= 75 THEN 'HIGH'
        WHEN (freshness_points + contact_points + completeness_points) >= 50 THEN 'MODERATE'
        ELSE 'LOW'
    END AS reliability_tier
FROM scored
    );
    
  