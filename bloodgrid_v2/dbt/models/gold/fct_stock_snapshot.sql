{{ config(
    materialized = 'incremental',
    unique_key = ['hospital_code', 'component_name', 'blood_group', 'snapshot_date']
) }}

SELECT
    hospital_code,
    hospital_name,
    state_name,
    district_name,
    component_name,
    blood_group,
    units,
    source_updated_at,
    scraped_at AS snapshot_at,
    CAST(scraped_at AS DATE) AS snapshot_date
FROM {{ ref('stg_inventory_components') }}

{% if is_incremental() %}
    WHERE scraped_at > (SELECT COALESCE(MAX(snapshot_at), '1970-01-01'::TIMESTAMP) FROM {{ this }})
{% endif %}
