
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select hospital_name
from "blood_warehouse"."main_gold"."dim_blood_banks"
where hospital_name is null



  
  
      
    ) dbt_internal_test