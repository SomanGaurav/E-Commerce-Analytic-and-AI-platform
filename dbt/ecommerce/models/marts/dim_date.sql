with bounds as (
    select
        min(order_date) as min_date,
        max(order_date) as max_date
    from {{ ref('stg_orders') }}
),
spine as (
    select unnest(generate_series(
        (select min_date from bounds),
        (select max_date from bounds),
        interval 1 day
    )) as date_day
)
select
    date_day,
    extract(year from date_day) as year,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
    extract(dow from date_day) as day_of_week,
    strftime(date_day, '%Y-%m') as year_month
from spine
