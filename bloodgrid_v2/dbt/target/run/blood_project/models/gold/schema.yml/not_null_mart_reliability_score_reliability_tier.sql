
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select reliability_tier
from "blood_warehouse"."main_gold"."mart_reliability_score"
where reliability_tier is null



  
  
      
    ) dbt_internal_test