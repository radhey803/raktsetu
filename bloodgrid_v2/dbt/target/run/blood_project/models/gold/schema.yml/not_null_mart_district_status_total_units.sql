
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_units
from "blood_warehouse"."main_gold"."mart_district_status"
where total_units is null



  
  
      
    ) dbt_internal_test