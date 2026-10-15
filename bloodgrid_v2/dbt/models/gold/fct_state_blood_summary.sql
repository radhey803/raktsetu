{{config(materialized = 'table')}}

SELECT 
  state_name,
  district_name,
  COUNT(DISTINCT hospital_code) AS total_blood_banks,
  COUNT(DISTINCT CASE WHEN hospital_type = 'Govt.' THEN hospital_code END ) AS govt_banks,
  COUNT(DISTINCT CASE WHEN hospital_type != 'Govt.' THEN hospital_code END ) AS private_banks,
  COUNT(*) AS total_records,
  MIN(last_updated_at) AS oldest_update,
  MAX(last_updated_at) AS latest_update
FROM {{ref('stg_blood_inventory')}}
GROUP BY state_name , district_name
ORDER BY total_blood_banks DESC

  
