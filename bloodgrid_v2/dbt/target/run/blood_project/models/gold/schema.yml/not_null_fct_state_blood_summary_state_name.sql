
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select state_name
from "blood_warehouse"."main_gold"."fct_state_blood_summary"
where state_name is null



  
  
      
    ) dbt_internal_test