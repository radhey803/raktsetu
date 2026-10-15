
    

    create  table
      "blood_warehouse"."main_gold"."dim_blood_banks__dbt_tmp"
  
    
    as (
      

SELECT
    hospital_code,
    hospital_name,
    hospital_address,
    hospital_contact,
    hospital_type,
    facility_type,
    state_name,
    district_name,
    source_updated_at,
    scraped_at AS lakehouse_ingested_at
FROM "blood_warehouse"."main_silver"."stg_blood_banks"
    );
    
  