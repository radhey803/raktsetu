

WITH current_stock AS (
    SELECT
        state_name,
        district_name,
        component_name,
        blood_group,
        hospital_code,
        units
    FROM "blood_warehouse"."main_gold"."fct_stock_current"
),

aggregated AS (
    SELECT
        state_name,
        district_name,
        component_name,
        blood_group,
        COUNT(DISTINCT hospital_code) AS total_reporting_banks,
        COUNT(DISTINCT CASE WHEN units > 0 THEN hospital_code END) AS stocked_banks,
        SUM(units) AS total_units,
        MIN(units) AS min_facility_units,
        MAX(units) AS max_facility_units
    FROM current_stock
    GROUP BY state_name, district_name, component_name, blood_group
)

SELECT
    state_name,
    district_name,
    component_name,
    blood_group,
    total_reporting_banks,
    stocked_banks,
    total_units,
    min_facility_units,
    max_facility_units,
    CASE 
        WHEN total_units = 0 THEN 'CRITICAL_DEPLETION'
        WHEN total_units <= 5 THEN 'HIGH_SHORTAGE'
        WHEN total_units <= 15 THEN 'MODERATE_SHORTAGE'
        ELSE 'ADEQUATE'
    END AS shortage_status
FROM aggregated