with orders_agg as (
    select
        customer_id,
        count(distinct order_id) as total_orders,
        count(distinct case when status = 'completed' then order_id end) as completed_orders,
        count(distinct case when status = 'cancelled' then order_id end) as cancelled_orders,
        count(distinct case when status = 'returned' then order_id end) as returned_orders,
        sum(case when status = 'completed' then order_total else 0 end) as total_revenue,
        max(order_date) as last_order_date,
        min(order_date) as first_order_date
    from {{ ref('stg_orders') }}
    group by customer_id
)
select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.region,
    c.segment,
    coalesce(o.total_orders, 0) as total_orders,
    coalesce(o.completed_orders, 0) as completed_orders,
    coalesce(o.cancelled_orders, 0) as cancelled_orders,
    coalesce(o.returned_orders, 0) as returned_orders,
    coalesce(o.total_revenue, 0) as total_revenue,
    case when o.completed_orders > 0 then round(o.total_revenue / o.completed_orders, 2) else 0 end as avg_order_value,
    case when o.total_orders > 0 then round(o.cancelled_orders * 1.0 / o.total_orders, 4) else 0 end as cancellation_rate,
    o.first_order_date,
    o.last_order_date,
    case when o.last_order_date >= current_date - interval 180 day then true else false end as is_active_customer
from {{ ref('dim_customer') }} c
left join orders_agg o on c.customer_id = o.customer_id
