
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_blood_banks
from "blood_warehouse"."main_gold"."fct_state_blood_summary"
where total_blood_banks is null



  
  
      
    ) dbt_internal_test