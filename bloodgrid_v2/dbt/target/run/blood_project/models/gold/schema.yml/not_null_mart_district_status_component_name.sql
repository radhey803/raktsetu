
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select component_name
from "blood_warehouse"."main_gold"."mart_district_status"
where component_name is null



  
  
      
    ) dbt_internal_test