
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select reliability_score
from "blood_warehouse"."main_gold"."mart_reliability_score"
where reliability_score is null



  
  
      
    ) dbt_internal_test