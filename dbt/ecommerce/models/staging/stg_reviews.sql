select
    review_id,
    order_id,
    customer_id,
    product_id,
    review_date,
    rating,
    trim(review_text) as review_text
from {{ source('raw', 'reviews') }}
where review_id is not null
