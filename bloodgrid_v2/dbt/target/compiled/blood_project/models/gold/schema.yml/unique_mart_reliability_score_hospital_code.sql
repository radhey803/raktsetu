
    
    

select
    hospital_code as unique_field,
    count(*) as n_records

from "blood_warehouse"."main_gold"."mart_reliability_score"
where hospital_code is not null
group by hospital_code
having count(*) > 1


