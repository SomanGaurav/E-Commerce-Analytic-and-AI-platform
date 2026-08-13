select
    order_id,
    customer_id,
    order_date,
    status,
    order_total
from {{ source('raw', 'orders') }}
where order_id is not null
