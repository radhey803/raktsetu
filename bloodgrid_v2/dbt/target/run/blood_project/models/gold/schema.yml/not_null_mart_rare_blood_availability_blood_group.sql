
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select blood_group
from "blood_warehouse"."main_gold"."mart_rare_blood_availability"
where blood_group is null



  
  
      
    ) dbt_internal_test