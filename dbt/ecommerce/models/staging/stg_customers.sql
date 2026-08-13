select
    customer_id,
    trim(first_name) as first_name,
    trim(last_name) as last_name,
    lower(trim(email)) as email,
    signup_date,
    region,
    segment
from {{ source('raw', 'customers') }}
where customer_id is not null
