"""
Seed the database with realistic categories and 100+ products.

Usage:
    python seed_products.py

Reads the same MYSQL_* / .env settings as the app (see config.py).
Safe to re-run: existing SKUs are skipped (INSERT ... ON DUPLICATE KEY UPDATE
sku=sku), so it won't create duplicates if you run it more than once.
"""
import os
import random

import pymysql
import pymysql.cursors

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

random.seed(42)  # reproducible SKUs/barcodes/prices across runs

DB = dict(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    port=int(os.environ.get("MYSQL_PORT", 3306)),
    user=os.environ.get("MYSQL_USER", "root"),
    password=os.environ.get("MYSQL_PASSWORD", ""),
    database=os.environ.get("MYSQL_DB", "counter_pos"),
    cursorclass=pymysql.cursors.DictCursor,
)

# ------------------------------------------------------------------
# Categories -> (price range, product names)
# ------------------------------------------------------------------
CATALOG = {
    "Beverages": {
        "range": (1.00, 5.50),
        "items": [
            "Cola 500ml", "Diet Cola 500ml", "Lemon Soda 500ml", "Orange Soda 500ml",
            "Sparkling Water 750ml", "Still Water 500ml", "Still Water 1.5L",
            "Iced Tea Peach 500ml", "Iced Tea Lemon 500ml", "Energy Drink 250ml",
            "Sports Drink Blue 600ml", "Sports Drink Orange 600ml", "Apple Juice 1L",
            "Orange Juice 1L", "Mango Juice 1L", "Coffee Instant Jar 200g",
            "Coffee Ground 250g", "Tea Bags Black 100ct", "Tea Bags Green 50ct",
            "Hot Chocolate Mix 400g", "Milkshake Chocolate 350ml", "Milkshake Strawberry 350ml",
        ],
    },
    "Snacks": {
        "range": (0.80, 4.50),
        "items": [
            "Potato Chips Classic 150g", "Potato Chips Salt & Vinegar 150g",
            "Potato Chips BBQ 150g", "Tortilla Chips 200g", "Cheese Puffs 120g",
            "Pretzels 200g", "Popcorn Butter 100g", "Popcorn Caramel 100g",
            "Peanuts Salted 200g", "Cashews Roasted 150g", "Mixed Nuts 200g",
            "Chocolate Bar Milk 100g", "Chocolate Bar Dark 100g", "Chocolate Bar Hazelnut 100g",
            "Granola Bar Oats & Honey", "Granola Bar Chocolate Chip", "Fruit Gummies 100g",
            "Candy Mints 50g", "Crackers Whole Wheat 250g", "Rice Cakes 130g",
            "Beef Jerky 80g", "Trail Mix 200g",
        ],
    },
    "Household": {
        "range": (1.50, 12.00),
        "items": [
            "Dish Soap 500ml", "Laundry Detergent 1L", "Fabric Softener 1L",
            "All-Purpose Cleaner 750ml", "Glass Cleaner 500ml", "Bleach 1L",
            "Paper Towels 2-Pack", "Toilet Paper 12-Pack", "Facial Tissues Box",
            "Trash Bags 30ct", "Aluminum Foil 30m", "Plastic Wrap 30m",
            "Sponges 6-Pack", "Rubber Gloves Medium", "Air Freshener Spray",
            "Candles Scented", "Light Bulbs LED 2-Pack", "Batteries AA 4-Pack",
            "Batteries AAA 4-Pack", "Matches Box", "Sewing Kit", "Clothes Pegs 20ct",
        ],
    },
    "Dairy": {
        "range": (0.90, 6.50),
        "items": [
            "Milk Whole 1L", "Milk Skim 1L", "Milk Chocolate 500ml",
            "Yogurt Plain 500g", "Yogurt Strawberry 150g", "Yogurt Vanilla 150g",
            "Butter Salted 250g", "Butter Unsalted 250g", "Cheddar Cheese 200g",
            "Mozzarella Cheese 200g", "Cream Cheese 200g", "Sour Cream 250ml",
            "Whipping Cream 250ml", "Eggs Dozen Large", "Margarine 500g",
        ],
    },
    "Bakery": {
        "range": (1.00, 6.00),
        "items": [
            "White Bread Loaf", "Whole Wheat Bread Loaf", "Sourdough Bread Loaf",
            "Bagels 6-Pack", "Croissants 4-Pack", "Muffins Blueberry 4-Pack",
            "Donuts Glazed 6-Pack", "Dinner Rolls 8-Pack", "Tortilla Wraps 8-Pack",
            "Pita Bread 6-Pack", "Cake Chocolate Slice", "Cookies Chocolate Chip 300g",
        ],
    },
    "Produce": {
        "range": (0.50, 4.50),
        "items": [
            "Bananas 1kg", "Apples Red 1kg", "Apples Green 1kg", "Oranges 1kg",
            "Grapes Seedless 500g", "Strawberries 250g", "Lemons 500g",
            "Tomatoes 1kg", "Cucumbers 1kg", "Carrots 1kg", "Potatoes 2kg",
            "Onions 1kg", "Garlic 250g", "Bell Peppers 500g", "Lettuce Head",
            "Spinach 250g", "Avocado Each", "Broccoli Head",
        ],
    },
    "Frozen Foods": {
        "range": (2.00, 9.00),
        "items": [
            "Frozen Pizza Margherita", "Frozen Pizza Pepperoni", "Frozen French Fries 1kg",
            "Frozen Mixed Vegetables 1kg", "Frozen Chicken Nuggets 500g",
            "Frozen Fish Fillets 500g", "Ice Cream Vanilla 1L", "Ice Cream Chocolate 1L",
            "Frozen Waffles 8ct", "Frozen Dumplings 500g", "Frozen Berries Mixed 500g",
        ],
    },
    "Personal Care": {
        "range": (1.50, 9.50),
        "items": [
            "Shampoo 400ml", "Conditioner 400ml", "Body Wash 500ml", "Bar Soap 3-Pack",
            "Toothpaste 100ml", "Toothbrush Soft", "Mouthwash 500ml", "Deodorant Spray",
            "Hand Sanitizer 250ml", "Hand Cream 100ml", "Razors Disposable 4-Pack",
            "Shaving Cream 200ml", "Cotton Swabs 100ct", "Facial Wipes 25ct",
            "Sunscreen SPF50 100ml",
        ],
    },
    "Stationery": {
        "range": (0.60, 8.00),
        "items": [
            "Ballpoint Pens 5-Pack", "Pencils HB 10-Pack", "Notebook A5 Ruled",
            "Notebook A4 Ruled", "Sticky Notes Pad", "Highlighters 4-Pack",
            "Stapler Small", "Staples Box", "Scissors", "Glue Stick",
            "Envelopes 20ct", "Printer Paper A4 Ream", "Rubber Bands Pack",
            "Paper Clips Box", "Correction Tape",
        ],
    },
    "Electronics Accessories": {
        "range": (2.50, 25.00),
        "items": [
            "USB-C Charging Cable 1m", "Lightning Cable 1m", "Micro-USB Cable 1m",
            "Wall Charger 20W", "Car Charger Dual Port", "Earphones Wired",
            "Bluetooth Earbuds Basic", "Phone Case Universal", "Screen Protector Glass",
            "Power Bank 10000mAh", "HDMI Cable 2m", "AA Rechargeable Batteries 4-Pack",
            "Memory Card 32GB",
        ],
    },
}


def make_barcode(seen):
    while True:
        code = "".join(random.choices("0123456789", k=13))
        if code not in seen:
            seen.add(code)
            return code


def main():
    conn = pymysql.connect(**DB)
    seen_barcodes = set()
    total_inserted = 0
    total_seen = 0

    with conn.cursor() as cur:
        for cat_name, cat_data in CATALOG.items():
            cur.execute(
                "INSERT INTO categories (name) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE name=name",
                (cat_name,),
            )
            cur.execute("SELECT id FROM categories WHERE name=%s", (cat_name,))
            category_id = cur.fetchone()["id"]

            lo, hi = cat_data["range"]
            prefix = "".join(w[0] for w in cat_name.split())[:3].upper()

            for idx, name in enumerate(cat_data["items"], start=1):
                total_seen += 1
                sku = f"{prefix}-{idx:03d}"
                barcode = make_barcode(seen_barcodes)
                price = round(random.uniform(lo, hi), 2)
                cost_price = round(price * random.uniform(0.55, 0.8), 2)
                stock_qty = random.randint(15, 220)
                low_stock_at = random.choice([5, 8, 10, 15])

                cur.execute(
                    "INSERT INTO products "
                    "(sku, barcode, name, category_id, price, cost_price, stock_qty, low_stock_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON DUPLICATE KEY UPDATE sku=sku",
                    (sku, barcode, name, category_id, price, cost_price, stock_qty, low_stock_at),
                )
                if cur.rowcount == 1:  # 1 = inserted, 0 = duplicate skipped
                    total_inserted += 1

    conn.commit()
    conn.close()
    print(f"Seed complete: {total_inserted} new products inserted "
          f"({total_seen} total defined across {len(CATALOG)} categories).")


if __name__ == "__main__":
    main()
