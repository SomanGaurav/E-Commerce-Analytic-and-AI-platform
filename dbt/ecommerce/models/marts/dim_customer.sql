select
    customer_id,
    first_name,
    last_name,
    email,
    signup_date,
    region,
    segment
from {{ ref('stg_customers') }}
