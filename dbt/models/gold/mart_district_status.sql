{{ config(materialized = 'table') }}

/*
================================================================================
MART DISTRICT STATUS (District Deficit & Supply Health)
================================================================================
Aggregates component-level inventory at the administrative district grain:
- total_reporting_banks: Count of licensed facilities reporting stock
- banks_with_zero: Count of facilities reporting zero units
- total_units: Total units in the district
- shortage_flag: Boolean flag indicating critical supply deficit
- severity_score: 0-100 numerical urgency score for ranking
- shortage_status: Triage classification
================================================================================
*/

WITH current_stock AS (
    SELECT
        state_name,
        district_name,
        component_name,
        blood_group,
        hospital_code,
        units
    FROM {{ ref('fct_stock_current') }}
),

aggregated AS (
    SELECT
        state_name,
        district_name,
        component_name,
        blood_group,
        COUNT(DISTINCT hospital_code) AS total_reporting_banks,
        COUNT(DISTINCT CASE WHEN units > 0 THEN hospital_code END) AS stocked_banks,
        COUNT(DISTINCT CASE WHEN units = 0 THEN hospital_code END) AS banks_with_zero,
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
    banks_with_zero,
    total_units,
    min_facility_units,
    max_facility_units,
    CASE WHEN total_units <= 5 THEN true ELSE false END AS shortage_flag,
    CASE 
        WHEN total_units = 0 THEN 100
        WHEN total_units <= 5 THEN 75
        WHEN total_units <= 15 THEN 40
        ELSE 10
    END AS severity_score,
    CASE 
        WHEN total_units = 0 THEN 'CRITICAL_DEPLETION'
        WHEN total_units <= 5 THEN 'HIGH_SHORTAGE'
        WHEN total_units <= 15 THEN 'MODERATE_SHORTAGE'
        ELSE 'ADEQUATE'
    END AS shortage_status
FROM aggregated
