
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    hospital_code as unique_field,
    count(*) as n_records

from "blood_warehouse"."main_silver"."stg_blood_banks"
where hospital_code is not null
group by hospital_code
having count(*) > 1



  
  
      
    ) dbt_internal_test