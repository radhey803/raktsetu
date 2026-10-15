
    
    

with all_values as (

    select
        reliability_tier as value_field,
        count(*) as n_records

    from "blood_warehouse"."main_gold"."mart_reliability_score"
    group by reliability_tier

)

select *
from all_values
where value_field not in (
    'HIGH','MODERATE','LOW'
)


