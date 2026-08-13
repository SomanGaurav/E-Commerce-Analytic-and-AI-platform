select
    product_id,
    trim(product_name) as product_name,
    category,
    cost,
    price,
    round(price - cost, 2) as margin
from {{ source('raw', 'products') }}
where product_id is not null
