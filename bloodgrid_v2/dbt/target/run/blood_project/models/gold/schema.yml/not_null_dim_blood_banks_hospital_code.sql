
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select hospital_code
from "blood_warehouse"."main_gold"."dim_blood_banks"
where hospital_code is null



  
  
      
    ) dbt_internal_test