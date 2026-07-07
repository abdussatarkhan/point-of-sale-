"""
Generate demo sales history from 2021-01-01 up to today, so the dashboard,
reports, and sales history pages have years of realistic trend data.

Unlike the old version (fixed avg-sales-per-day), this generates sales
MONTH BY MONTH and keeps adding transactions until that month's total
revenue lands inside a target range (default 30,000 - 90,000 in your
store currency). Revenue within the month is spread across days, with
weekends and month-end (payday) days getting a bit more traffic.

Run seed_products.py FIRST if your products table is empty — this script
picks random existing products and users to build each sale.

Usage:
    python seed_sales.py
        # 2021-01-01 -> today, each month lands between 30k and 90k

    python seed_sales.py --start 2021-01-01 --end 2024-12-31 --min-monthly 40000 --max-monthly 70000

    python seed_sales.py --wipe
        # delete existing sales/sale_items/sale_payments first (recommended
        # the first time you run this, so old demo data doesn't mix in)

This inserts directly with a backdated `created_at`, so it does NOT touch
current product stock levels (that would make today's stock numbers
meaningless for a demo). Un-comment the stock-deduction block below if you
want historical sales to also draw down stock_qty.
"""
import argparse
import calendar
import os
import random
import string
from datetime import datetime, timedelta

import pymysql
import pymysql.cursors

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB = dict(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    port=int(os.environ.get("MYSQL_PORT", 3306)),
    user=os.environ.get("MYSQL_USER", "root"),
    password=os.environ.get("MYSQL_PASSWORD", ""),
    database=os.environ.get("MYSQL_DB", "counter_pos"),
    cursorclass=pymysql.cursors.DictCursor,
)

PAYMENT_METHODS = ["cash", "card", "mobile_wallet", "credit", "other"]
PAYMENT_WEIGHTS = [0.45, 0.35, 0.12, 0.05, 0.03]

# Store hours the register is realistically in use
OPEN_HOUR, CLOSE_HOUR = 8, 21


def business_day_weight(dt):
    """Weekends and month-end paydays are a bit busier — purely cosmetic."""
    w = 1.0
    if dt.weekday() >= 5:
        w *= 1.35
    if dt.day >= 28:
        w *= 1.15
    return w


def random_time_on(date):
    hour = random.randint(OPEN_HOUR, CLOSE_HOUR - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return date.replace(hour=hour, minute=minute, second=second, microsecond=0)


def generate_invoice_no(dt, used):
    while True:
        rand = "".join(random.choices(string.digits, k=4))
        inv = f"INV-{dt.strftime('%Y%m%d%H%M%S')}-{rand}"
        if inv not in used:
            used.add(inv)
            return inv


def month_range(start, end):
    """Yield (year, month, first_day, last_day) tuples covering [start, end]."""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        first_day = datetime(y, m, 1)
        last_dom = calendar.monthrange(y, m)[1]
        last_day = datetime(y, m, last_dom)
        yield y, m, max(first_day, start), min(last_day, end)
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def build_one_sale(cur, products, users, created_at, used_invoices):
    """Insert one randomized sale and return its total revenue."""
    cashier_id = random.choice(users)

    n_items = random.randint(1, 6)
    chosen = random.sample(products, k=min(n_items, len(products)))

    line_items = []
    subtotal = 0.0
    for p in chosen:
        qty = random.randint(1, 4)
        price = float(p["price"])
        line_total = round(price * qty, 2)
        subtotal += line_total
        line_items.append({
            "product_id": p["id"], "price": price,
            "qty": qty, "line_total": line_total,
        })
    subtotal = round(subtotal, 2)

    discount_type = "percent" if random.random() < 0.15 else "fixed"
    if discount_type == "percent":
        pct = random.choice([5, 10, 15])
        discount = round(subtotal * pct / 100, 2)
    else:
        discount = round(random.choice([0, 0, 0, 1, 2, 5]), 2)
        discount = min(discount, subtotal)

    tax_rate = float(os.environ.get("TAX_RATE", 0.0))
    taxable = max(subtotal - discount, 0)
    tax = round(taxable * tax_rate, 2)
    total = round(taxable + tax, 2)

    method = random.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS)[0]
    amount_paid = total if method != "cash" else round(
        total + random.choice([0, 0, 0, 0.5, 1, 2, 5]), 2
    )
    change_due = round(amount_paid - total, 2)

    invoice_no = generate_invoice_no(created_at, used_invoices)

    cur.execute(
        "INSERT INTO sales (invoice_no, user_id, subtotal, discount, "
        "discount_type, tax, total, amount_paid, change_due, payment_method, created_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (invoice_no, cashier_id, subtotal, discount, discount_type, tax,
         total, amount_paid, change_due, method, created_at)
    )
    sale_id = cur.lastrowid

    for li in line_items:
        cur.execute("SELECT name FROM products WHERE id=%s", (li["product_id"],))
        pname = cur.fetchone()["name"]
        cur.execute(
            "INSERT INTO sale_items (sale_id, product_id, product_name, "
            "unit_price, qty, line_total) VALUES (%s,%s,%s,%s,%s,%s)",
            (sale_id, li["product_id"], pname, li["price"], li["qty"], li["line_total"])
        )
        # NOTE: historical demo sales intentionally do not deduct current
        # stock_qty (that would make today's stock numbers meaningless for
        # a demo). Uncomment to also draw down stock as history is written:
        # cur.execute(
        #     "UPDATE products SET stock_qty = GREATEST(stock_qty - %s, 0) WHERE id=%s",
        #     (li["qty"], li["product_id"])
        # )

    cur.execute(
        "INSERT INTO sale_payments (sale_id, method, amount) VALUES (%s,%s,%s)",
        (sale_id, method, amount_paid)
    )
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--min-monthly", type=float, default=30000.0,
                     help="Minimum target revenue for each calendar month")
    ap.add_argument("--max-monthly", type=float, default=90000.0,
                     help="Maximum target revenue for each calendar month")
    ap.add_argument("--wipe", action="store_true",
                     help="Delete existing sales/sale_items/sale_payments first")
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    conn = pymysql.connect(**DB)
    with conn.cursor() as cur:
        cur.execute("SELECT id, price, stock_qty FROM products WHERE is_active=1")
        products = cur.fetchall()
        cur.execute("SELECT id FROM users WHERE is_active=1")
        users = [r["id"] for r in cur.fetchall()]

    if not products:
        print("No active products found — run seed_products.py first.")
        return
    if not users:
        print("No active users found — check your users table.")
        return

    if args.wipe:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sale_payments")
            cur.execute("DELETE FROM sale_items")
            cur.execute("DELETE FROM sales")
        conn.commit()
        print("Existing sales data wiped.")

    used_invoices = set()
    grand_total_sales = 0
    grand_total_revenue = 0.0

    with conn.cursor() as cur:
        for year, month, m_start, m_end in month_range(start, end):
            target_revenue = random.uniform(args.min_monthly, args.max_monthly)

            days = []
            d = m_start
            while d <= m_end:
                days.append(d)
                d += timedelta(days=1)
            weights = [business_day_weight(d) for d in days]
            total_weight = sum(weights) or 1.0

            month_sales = 0
            month_revenue = 0.0

            for day, weight in zip(days, weights):
                day_target = target_revenue * (weight / total_weight)
                day_revenue = 0.0
                # Keep adding sales until this day's slice of the monthly
                # target is met (small overshoot on the last sale is fine —
                # it averages out and keeps the month close to its target).
                guard = 0
                while day_revenue < day_target and guard < 200:
                    guard += 1
                    created_at = random_time_on(day)
                    total = build_one_sale(cur, products, users, created_at, used_invoices)
                    day_revenue += total
                    month_sales += 1
                    month_revenue += total

            grand_total_sales += month_sales
            grand_total_revenue += month_revenue
            print(f"{year}-{month:02d}: {month_sales} sales, "
                  f"~{month_revenue:,.2f} revenue (target {target_revenue:,.2f})")

        conn.commit()

    conn.close()
    print(f"\nSeed complete: {grand_total_sales} sales created from "
          f"{args.start} to {args.end} (~{grand_total_revenue:,.2f} total revenue).")


if __name__ == "__main__":
    main()
