{{ config(materialized = 'table') }}

/*
================================================================================
MART RELIABILITY SCORE FORMULA (0 - 100 Points)
================================================================================
1. Freshness Score (Max 50 Points):
   - Last updated < 24h (<= 1 day): 50 pts
   - Last updated < 3d (2 to 3 days): 35 pts
   - Last updated < 7d (4 to 6 days): 20 pts
   - Last updated < 14d (7 to 13 days): 8 pts
   - Older (>= 14 days or NULL): 0 pts

2. Valid Contact Score (Max 25 Points):
   - Phone number passes basic format check (>= 8 numeric digits): 25 pts
   - Missing or invalid phone: 0 pts

3. Component Completeness Score (Max 25 Points):
   - Tracks >= 3 distinct blood components (PRBC, Platelets, FFP, etc.): 25 pts
   - Tracks 1 or 2 blood components: 15 pts
   - No components reported: 0 pts

Reliability Labels:
   - High: Score >= 75
   - Medium: Score between 40 and 74
   - Low: Score < 40
================================================================================
*/

WITH facility_components AS (
    SELECT
        hospital_code,
        COUNT(DISTINCT component_name) AS distinct_components_count,
        SUM(units) AS total_units_in_stock
    FROM {{ ref('fct_stock_current') }}
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
    FROM {{ ref('dim_blood_banks') }} b
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
            WHEN days_since_update <= 3 THEN 35
            WHEN days_since_update <= 6 THEN 20
            WHEN days_since_update <= 13 THEN 8
            ELSE 0
        END AS freshness_points,
        -- 2. Contact Points (0-25): Phone number check (>= 8 digits)
        CASE
            WHEN regexp_matches(hospital_contact, '[0-9]{8,}') THEN 25
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
        WHEN (freshness_points + contact_points + completeness_points) >= 75 THEN 'High'
        WHEN (freshness_points + contact_points + completeness_points) >= 40 THEN 'Medium'
        ELSE 'Low'
    END AS reliability_label,
    CASE
        WHEN (freshness_points + contact_points + completeness_points) >= 75 THEN 'High'
        WHEN (freshness_points + contact_points + completeness_points) >= 40 THEN 'Medium'
        ELSE 'Low'
    END AS reliability_tier
FROM scored
