CREATE TABLE bronze.raw_blood_inventory AS 
SELECT *, CURRENT_TIMESTAMP AS ingested_at
FROM read_csv_auto('INDIA_blood_inventory_async.csv');


SELECT COUNT (*) AS total_rows 
FROM bronze.raw_blood_inventory;


    SELECT State, 
        COUNT(distinct hospitalcode) AS banks 
        FROM bronze.raw_blood_inventory
        GROUP BY State
        ORDER BY banks DESC 
        LIMIT 5;
    
   
DESCRIBE bronze.raw_blood_inventory;


DROP TABLE bronze.raw_blood_inventory;


SELECT * FROM read_csv_auto('INDIA_blood_inventory_async.csv') LIMIT 1;
 





CREATE TABLE bronze.raw_blood_inventory AS
SELECT *, CURRENT_TIMESTAMP AS ingested_at
FROM read_csv(
    'INDIA_blood_inventory_async.csv',
    header = True,
    delim = ',',
    quote = '"',
    escape = '"',
    auto_detect = True,
    ignore_errors = True,
    null_padding = True
);


     
   SELECT COUNT(*) FROM bronze.raw_blood_inventory;
 