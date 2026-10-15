
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        blood_group as value_field,
        count(*) as n_records

    from "blood_warehouse"."main_silver"."stg_inventory_components"
    group by blood_group

)

select *
from all_values
where value_field not in (
    'O+','O-','A+','A-','B+','B-','AB+','AB-','Bombay (Oh+)','Bombay (Oh-)'
)



  
  
      
    ) dbt_internal_test