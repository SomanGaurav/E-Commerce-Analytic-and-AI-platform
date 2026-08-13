"""Generate synthetic e-commerce data: customers, products, orders, order_items, reviews.

Usage: python generate_synthetic_data.py [--out-dir data/raw] [--seed 42]
"""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]
SEGMENTS = ["Consumer", "Small Business", "Enterprise"]
CATEGORIES = ["Electronics", "Home & Kitchen", "Apparel", "Sports & Outdoors", "Books", "Beauty", "Toys"]
ORDER_STATUSES = ["completed", "completed", "completed", "completed", "cancelled", "returned"]

ISSUE_TEMPLATES = {
    "shipping_delay": [
        "My order took way longer than expected to arrive, over {days} days late.",
        "Shipping was extremely slow, I waited {days} extra days for this to show up.",
        "The delivery estimate was wrong, package arrived {days} days after it was promised.",
    ],
    "product_quality": [
        "The {product} broke after just a few uses, very disappointed in the build quality.",
        "Quality of the {product} is much worse than the pictures suggested.",
        "This {product} feels cheap and started malfunctioning within a week.",
    ],
    "wrong_item": [
        "I ordered a {product} but received a completely different item.",
        "The {product} I got does not match the description at all.",
    ],
    "customer_service": [
        "Support never responded to my emails about my {product} issue.",
        "Customer service was unhelpful when I asked about returning my {product}.",
    ],
    "packaging_damage": [
        "The {product} arrived damaged, packaging was clearly not sufficient.",
        "Box was crushed and the {product} inside had scratches.",
    ],
}

POSITIVE_TEMPLATES = [
    "Really happy with this {product}, works exactly as described.",
    "Great quality {product} and arrived earlier than expected.",
    "Excellent value for money, would buy this {product} again.",
    "The {product} exceeded my expectations, highly recommend.",
]

NEUTRAL_TEMPLATES = [
    "The {product} is okay, does what it says but nothing special.",
    "Average experience with this {product}, works fine.",
]


def gen_customers(fake: Faker, n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        signup = fake.date_between(start_date="-3y", end_date="today")
        rows.append({
            "customer_id": i,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "signup_date": signup,
            "region": random.choice(REGIONS),
            "segment": random.choice(SEGMENTS),
        })
    return pd.DataFrame(rows)


def gen_products(fake: Faker, n: int) -> pd.DataFrame:
    rows = []
    for i in range(1, n + 1):
        category = random.choice(CATEGORIES)
        cost = round(random.uniform(5, 200), 2)
        price = round(cost * random.uniform(1.3, 2.5), 2)
        rows.append({
            "product_id": i,
            "product_name": f"{fake.word().capitalize()} {category[:-1] if category.endswith('s') else category}",
            "category": category,
            "cost": cost,
            "price": price,
        })
    return pd.DataFrame(rows)


def gen_orders_and_items(fake: Faker, n_orders: int, n_customers: int, products: pd.DataFrame):
    order_rows = []
    item_rows = []
    item_id = 1
    for order_id in range(1, n_orders + 1):
        customer_id = random.randint(1, n_customers)
        order_date = fake.date_between(start_date="-2y", end_date="today")
        status = random.choice(ORDER_STATUSES)
        n_items = random.randint(1, 4)
        chosen = products.sample(n=n_items)
        order_total = 0.0
        for _, prod in chosen.iterrows():
            qty = random.randint(1, 3)
            unit_price = prod["price"]
            order_total += qty * unit_price
            item_rows.append({
                "order_item_id": item_id,
                "order_id": order_id,
                "product_id": int(prod["product_id"]),
                "quantity": qty,
                "unit_price": unit_price,
            })
            item_id += 1
        order_rows.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "order_date": order_date,
            "status": status,
            "order_total": round(order_total, 2),
        })
    return pd.DataFrame(order_rows), pd.DataFrame(item_rows)


def gen_reviews(fake: Faker, orders: pd.DataFrame, order_items: pd.DataFrame, products: pd.DataFrame, n: int) -> pd.DataFrame:
    completed = orders[orders["status"] != "cancelled"]
    sample_orders = completed.sample(n=min(n, len(completed)))
    rows = []
    review_id = 1
    for _, order in sample_orders.iterrows():
        items = order_items[order_items["order_id"] == order["order_id"]]
        if items.empty:
            continue
        product_id = int(items.iloc[0]["product_id"])
        product_name = products.loc[products["product_id"] == product_id, "product_name"].values[0]
        rating_roll = random.random()
        if rating_roll < 0.3:
            rating = random.choice([1, 2])
            issue_type = random.choice(list(ISSUE_TEMPLATES.keys()))
            template = random.choice(ISSUE_TEMPLATES[issue_type])
            text = template.format(product=product_name, days=random.randint(3, 14))
        elif rating_roll < 0.45:
            rating = 3
            text = random.choice(NEUTRAL_TEMPLATES).format(product=product_name)
            issue_type = "none"
        else:
            rating = random.choice([4, 5])
            text = random.choice(POSITIVE_TEMPLATES).format(product=product_name)
            issue_type = "none"
        review_date = order["order_date"] + timedelta(days=random.randint(2, 30))
        rows.append({
            "review_id": review_id,
            "order_id": int(order["order_id"]),
            "customer_id": int(order["customer_id"]),
            "product_id": product_id,
            "review_date": review_date,
            "rating": rating,
            "review_text": text,
            "true_issue_type": issue_type,
        })
        review_id += 1
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/raw")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-customers", type=int, default=500)
    parser.add_argument("--n-products", type=int, default=120)
    parser.add_argument("--n-orders", type=int, default=3000)
    parser.add_argument("--n-reviews", type=int, default=800)
    args = parser.parse_args()

    random.seed(args.seed)
    fake = Faker()
    Faker.seed(args.seed)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    customers = gen_customers(fake, args.n_customers)
    products = gen_products(fake, args.n_products)
    orders, order_items = gen_orders_and_items(fake, args.n_orders, args.n_customers, products)
    reviews = gen_reviews(fake, orders, order_items, products, args.n_reviews)

    customers.to_csv(out_dir / "customers.csv", index=False)
    products.to_csv(out_dir / "products.csv", index=False)
    orders.to_csv(out_dir / "orders.csv", index=False)
    order_items.to_csv(out_dir / "order_items.csv", index=False)
    reviews.to_csv(out_dir / "reviews.csv", index=False)

    print(f"customers:   {len(customers)}")
    print(f"products:    {len(products)}")
    print(f"orders:      {len(orders)}")
    print(f"order_items: {len(order_items)}")
    print(f"reviews:     {len(reviews)}")
    print(f"Written to {out_dir.resolve()}")


if __name__ == "__main__":
    main()
