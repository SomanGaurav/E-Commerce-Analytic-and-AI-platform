select
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    round(quantity * unit_price, 2) as line_amount
from {{ source('raw', 'order_items') }}
where order_item_id is not null
