
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select units
from "blood_warehouse"."main_gold"."fct_stock_current"
where units is null



  
  
      
    ) dbt_internal_test