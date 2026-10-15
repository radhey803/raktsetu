
        
            delete from "blood_warehouse"."main_gold"."fct_stock_snapshot" as DBT_INCREMENTAL_TARGET
            using "fct_stock_snapshot__dbt_tmp20261015022958118955"
            where (
                
                    "fct_stock_snapshot__dbt_tmp20261015022958118955".hospital_code = DBT_INCREMENTAL_TARGET.hospital_code
                    and 
                
                    "fct_stock_snapshot__dbt_tmp20261015022958118955".component_name = DBT_INCREMENTAL_TARGET.component_name
                    and 
                
                    "fct_stock_snapshot__dbt_tmp20261015022958118955".blood_group = DBT_INCREMENTAL_TARGET.blood_group
                    and 
                
                    "fct_stock_snapshot__dbt_tmp20261015022958118955".snapshot_date = DBT_INCREMENTAL_TARGET.snapshot_date
                    
                
                
            );
        
    

    insert into "blood_warehouse"."main_gold"."fct_stock_snapshot" ("hospital_code", "hospital_name", "state_name", "district_name", "component_name", "blood_group", "units", "source_updated_at", "snapshot_at", "snapshot_date")
    (
        select "hospital_code", "hospital_name", "state_name", "district_name", "component_name", "blood_group", "units", "source_updated_at", "snapshot_at", "snapshot_date"
        from "fct_stock_snapshot__dbt_tmp20261015022958118955"
    )
  