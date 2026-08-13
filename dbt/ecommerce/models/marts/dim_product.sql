select
    product_id,
    product_name,
    category,
    cost,
    price,
    margin
from {{ ref('stg_products') }}
