# Data Dictionary — Gold Layer

DuckDB database: `warehouse/ecommerce.duckdb`. Schemas: `raw` (bronze), `staging` (silver), `gold` (business layer).

## gold.dim_customer

| Column | Type | Description |
|---|---|---|
| customer_id | INTEGER | Primary key |
| first_name | VARCHAR | |
| last_name | VARCHAR | |
| email | VARCHAR | Lowercased |
| signup_date | DATE | |
| region | VARCHAR | One of: North America, Europe, Asia Pacific, Latin America, Middle East |
| segment | VARCHAR | One of: Consumer, Small Business, Enterprise |

## gold.dim_product

| Column | Type | Description |
|---|---|---|
| product_id | INTEGER | Primary key |
| product_name | VARCHAR | |
| category | VARCHAR | |
| cost | DOUBLE | |
| price | DOUBLE | |
| margin | DOUBLE | price - cost |

## gold.dim_date

| Column | Type | Description |
|---|---|---|
| date_day | DATE | Primary key, spans min/max order_date |
| year, month, day, day_of_week | INTEGER | |
| year_month | VARCHAR | e.g. "2026-08" |

## gold.fct_transactions

Grain: one row per order line item.

| Column | Type | Description |
|---|---|---|
| order_item_id | INTEGER | Primary key |
| order_id | INTEGER | FK to orders |
| customer_id | INTEGER | FK to dim_customer |
| product_id | INTEGER | FK to dim_product |
| order_date | DATE | |
| status | VARCHAR | completed, cancelled, or returned |
| quantity | INTEGER | |
| unit_price | DOUBLE | |
| line_amount | DOUBLE | quantity * unit_price |

## gold.mart_customer_performance

Grain: one row per customer.

| Column | Type | Description |
|---|---|---|
| customer_id | INTEGER | Primary key |
| total_orders, completed_orders, cancelled_orders, returned_orders | INTEGER | |
| total_revenue | DOUBLE | Sum of order_total for completed orders |
| avg_order_value | DOUBLE | total_revenue / completed_orders |
| cancellation_rate | DOUBLE | cancelled_orders / total_orders |
| first_order_date, last_order_date | DATE | |
| is_active_customer | BOOLEAN | last_order_date within 180 days |

## gold.review_enrichment (AI-generated)

| Column | Type | Description |
|---|---|---|
| review_id | INTEGER | Primary key, FK to raw.reviews |
| sentiment | VARCHAR | positive, neutral, or negative |
| issue_type | VARCHAR | shipping_delay, product_quality, wrong_item, customer_service, packaging_damage, or none |
| urgency | VARCHAR | low, medium, or high |

## gold.review_embeddings (AI-generated, RAG index)

| Column | Type | Description |
|---|---|---|
| review_id | INTEGER | Primary key, FK to raw.reviews (rating <= 3 only) |
| embedding | FLOAT[768] | nomic-embed-text embedding of review_text |

## Sample Business Questions

- **Revenue**: `SELECT sum(line_amount) FROM gold.fct_transactions WHERE status = 'completed'`
- **AOV by region**: join `gold.mart_customer_performance` on `dim_customer.region`, average `avg_order_value`
- **Top products**: join `fct_transactions` to `dim_product`, group by product, sum `line_amount`
- **Cancellation hotspots**: `gold.mart_customer_performance.cancellation_rate` by region/segment
- **What are customers complaining about?**: `gold.review_enrichment` grouped by `issue_type`, or ask the RAG assistant in the Streamlit app
