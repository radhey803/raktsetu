

/*
================================================================================
MART STOCK CHANGE (7-Day Consumption & Days-of-Cover)
================================================================================
Absolute Rule: ZERO fake data.
This model strictly evaluates whether >= 7 distinct real snapshot dates exist
in the lakehouse. If fewer than 7 real snapshot dates exist, it yields an honest
empty dataset rather than extrapolating or fabricating trend rates.
================================================================================
*/

WITH date_check AS (
    SELECT COUNT(DISTINCT snapshot_date) AS distinct_dates_count
    FROM "blood_warehouse"."main_gold"."fct_stock_snapshot"
),

snapshots_ranked AS (
    SELECT
        s.hospital_code,
        s.hospital_name,
        s.state_name,
        s.district_name,
        s.component_name,
        s.blood_group,
        s.units,
        s.snapshot_date,
        DENSE_RANK() OVER (ORDER BY s.snapshot_date DESC) AS date_rank_desc
    FROM "blood_warehouse"."main_gold"."fct_stock_snapshot" s
    -- Only execute calculations if at least 7 distinct real snapshot dates exist
    WHERE (SELECT distinct_dates_count FROM date_check) >= 7
),

latest_vs_7d AS (
    SELECT
        curr.hospital_code,
        curr.hospital_name,
        curr.state_name,
        curr.district_name,
        curr.component_name,
        curr.blood_group,
        curr.units AS current_units,
        prev.units AS units_7d_ago,
        (curr.units - prev.units) AS delta_7d,
        GREATEST(0.0, (prev.units - curr.units) / 7.0) AS est_daily_consumption_rate
    FROM (SELECT * FROM snapshots_ranked WHERE date_rank_desc = 1) curr
    INNER JOIN (SELECT * FROM snapshots_ranked WHERE date_rank_desc = 7) prev
      ON curr.hospital_code = prev.hospital_code
     AND curr.component_name = prev.component_name
     AND curr.blood_group = prev.blood_group
)

SELECT
    hospital_code,
    hospital_name,
    state_name,
    district_name,
    component_name,
    blood_group,
    current_units,
    units_7d_ago,
    delta_7d,
    ROUND(est_daily_consumption_rate, 2) AS daily_consumption_rate,
    CASE 
        WHEN est_daily_consumption_rate > 0 THEN ROUND(current_units / est_daily_consumption_rate, 1)
        ELSE NULL
    END AS days_of_cover_estimate
FROM latest_vs_7d