
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select component_name
from "blood_warehouse"."main_gold"."fct_stock_current"
where component_name is null



  
  
      
    ) dbt_internal_test