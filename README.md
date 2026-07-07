# Counter — Point of Sale System

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-black)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange)

A full point-of-sale system built with **Flask** and **MySQL**: complete CRUD for
inventory, a cart-and-checkout flow, sales analytics, and an interface designed
to be usable under real store conditions (bright light, quick glances, gloved
or hurried hands).

## Features

- **Auth & roles** — session-based login, admin vs. cashier permissions, full user
  management (create, edit, reset password, activate/deactivate)
- **Inventory CRUD** — add, edit, soft-delete products; categories; SKU/barcode;
  stock levels and low-stock alerts (with a live badge in the nav bar)
- **Register (POS) — two dedicated modes**, chosen from a landing screen at `/pos`:
  - **Scan Mode** (`/pos/scan`) — camera only. The camera starts automatically
    and continuously reads barcodes (`BarcodeDetector` API); each recognized
    item is looked up and added to the cart at qty 1 automatically, with a
    big on-screen confirmation of the name and price. There is no search box
    or clickable list on this screen — it's built for "I don't know the
    price, just scan it."
  - **Manual Mode** (`/pos/manual`) — mouse & keyboard only, no camera. Type a
    name/SKU/barcode into the search box (with a type-ahead dropdown you can
    navigate with arrow keys + Enter), or just click a tile in the scrollable
    product grid below, filterable by category chip. Either action adds the
    item to the cart.
  - Both modes share the same running cart, discount/tax summary, and
    checkout modal, so you can switch between them mid-sale from the link at
    the top of each screen — nothing in the cart is lost.
- **Keyboard-only item entry (Manual Mode)** — cashiers can drive the whole
  register without a mouse: `F2` jumps to search, arrow keys move through
  results, `Enter` adds the highlighted item, a `3*sku` style prefix adds a
  quantity in one go, `+`/`-` adjust the last item added, `F8` clears the
  cart, and `F9` (or `Ctrl+Enter`) opens the charge screen. Full list in the
  "Keyboard shortcuts" panel under the search box.
- **Split payments** — pay a single sale with any mix of cash, card, mobile
  wallet, store credit, or other tender, with live "remaining to collect" and
  change-due calculation
- **Checkout** — atomic stock deduction with row locking (`SELECT ... FOR UPDATE`),
  sale + line-item + payment-line persistence, printable receipt
- **Sales analytics dashboard** — today's totals, 7-day revenue trend chart,
  top-products chart, low-stock list, recent transactions
- **Reports** — date-range revenue/discount/tax summary, daily revenue chart,
  payment-mix chart, top products, and per-cashier breakdown
- **Sales history** — date-range filtering, per-range revenue/transaction
  totals, and pagination so years of transactions stay fast to browse
- **Dark mode** — toggle in the nav bar, preference remembered per browser
- **Accessible, modern UI** — large touch targets (44px+ minimum), high-contrast
  colors, visible focus rings, skip-to-content link, `aria-live` flash messages,
  keyboard-operable cart and modals, responsive layout with a mobile nav

## Tech stack

- Backend: Flask (Python), raw SQL via PyMySQL (no ORM — easy to read and adapt)
- Database: MySQL
- Frontend: server-rendered Jinja2 templates + vanilla JS (no build step, no
  framework); [Chart.js](https://www.chartjs.org/) via CDN for the dashboard
  and reports charts

## Project structure

```
counter/
├── app.py                  # Routes: auth, inventory CRUD, POS, checkout,
│                            # sales, reports, user management
├── config.py                # Reads settings from environment variables
├── db.py                    # PyMySQL connection helper (request-scoped)
├── schema.sql                # Full MySQL schema + seed data + migration notes
├── seed_products.py          # Adds 165 demo products across 10 categories
├── seed_sales.py             # Generates demo sales history from 2021 -> today
│                              # (targets 30k-90k revenue per calendar month)
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html            # Nav, dark-mode toggle, flash messages
│   ├── login.html
│   ├── dashboard.html        # Stat cards + charts
│   ├── reports.html          # Date-range reports + charts
│   ├── products.html
│   ├── product_form.html
│   ├── pos.html              # Register landing page — choose Scan or Manual mode
│   ├── pos_scan.html         # Scan Mode — camera-only barcode scanning
│   ├── pos_manual.html       # Manual Mode — search + clickable product grid
│   ├── _pos_cart.html        # Shared cart pane + checkout modal (included by both)
│   ├── receipt.html
│   ├── sales_history.html
│   ├── users.html            # Admin user list with activate/deactivate
│   └── user_form.html        # Create/edit user
└── static/
    ├── css/style.css         # Full theme (light + dark), animations
    └── js/
        ├── main.js           # Dark mode, mobile nav, flash auto-dismiss
        ├── pos_cart.js        # Shared: cart rendering, totals, checkout modal,
        │                      # split payments, keyboard shortcuts
        ├── pos_scan.js         # Scan Mode: continuous camera barcode detection
        └── pos_manual.js       # Manual Mode: type-ahead search + product grid
```

## Setup

### 1. Create the database

```bash
mysql -u root -p < schema.sql
```

This creates the `counter_pos` database, all tables (including the new
`sale_payments` table for split tender), a default admin user, and a few
starter categories.

**Already have the previous version's database?** Don't re-run the whole file —
just run the three migration statements at the bottom of `schema.sql` to add
`discount_type`, widen `payment_method`, and create `sale_payments`.

**Default login:** `admin` / `admin123` — change this immediately in a real deployment.

### 2. Configure environment variables

```bash
cp .env.example .env
# edit .env with your MySQL credentials
```

Then export them (or use `python-dotenv` / your process manager) before running the app.

### 3. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run

```bash
python app.py
```

Visit `http://localhost:5000`, sign in, and go to **Register** to start ringing up sales,
or **Inventory** to add products first. Signing in takes you straight into
**Manual Mode**; from there (or from the **Register** nav link) you can jump
to **Scan Mode** whenever a price needs to be looked up by camera.

## Demo data (165 products & sales history since 2021)

Two standalone scripts populate the app with realistic demo data. Run them
with the same environment variables as the app (`.env` is picked up
automatically if `python-dotenv` is installed; otherwise export the vars first).

```bash
# 1. Add 165 products across 10 categories (Beverages, Snacks, Household,
#    Dairy, Bakery, Produce, Frozen Foods, Personal Care, Stationery,
#    Electronics Accessories). Safe to re-run — duplicates are skipped.
python seed_products.py

# 2. Generate demo sales transactions from 2021-01-01 up to today, spread
#    across your active products/cashiers, with realistic payment-method mix
#    and weekend/month-end bumps in volume. Each calendar month's total
#    revenue is targeted to land between 30,000 and 90,000 (your currency).
python seed_sales.py

# Options:
python seed_sales.py --start 2021-01-01 --end 2023-12-31 --min-monthly 40000 --max-monthly 70000
python seed_sales.py --wipe          # clear existing sales first, then regenerate
```

This will insert several tens of thousands of transactions (roughly
500-1,500 per month, times ~5.5 years), so the first run can take a few
minutes depending on your MySQL server — that's expected. Use `--start`/`--end`
to generate a shorter window first if you just want to check it works.

Where to see the result once seeded:
- **Register (`/pos/manual`)** — search or click across all 165 seeded products
- **Sales history (`/sales`)** — every generated transaction, filterable by
  date range (defaults show the most recent 50; older ones going back to
  2021 are a few page-flips away)
- **Reports (`/reports`)** — pick any date range from 2021 onward for
  revenue/discount/tax summaries, daily chart, top products, per-cashier totals
- **Dashboard (`/`)** — today's stats and the 7-day trend chart will reflect
  whatever's most recent in the generated data

Real sales recorded through actual checkouts on the Register screen (not the
seed script) work exactly the same way and show up in all of the same places
immediately — the seed script is only there to backfill history for testing
and demos.

## Using the new features

- **Scan Mode camera scanning**: open **Register &rarr; Scan Mode**. The camera
  starts automatically and requests permission; it uses the browser's native
  `BarcodeDetector` API (supported in Chrome/Edge on desktop and Android).
  Browsers without it (e.g. Safari, Firefox) show a message pointing the
  cashier to Manual Mode instead. This screen intentionally has no search box
  or clickable list — it only adds items via camera, which is the point when
  the cashier doesn't know a product's price and needs to scan it to find out.
- **Manual Mode product grid**: open **Register &rarr; Manual Mode** for a
  mouse/keyboard-driven sale — click category chips to filter, click any tile
  to add it at qty 1, or use the search box/keyboard shortcuts above it.
- **Split payments**: in the checkout modal, click **+ Add payment method** to
  add more tender lines (e.g. part cash, part card). The "Remaining" line
  turns green once the sale is fully covered; **Confirm payment** stays
  disabled until it is.
- **Discounts**: use the unit selector next to the discount field on the
  Register screen to switch between a flat amount and a percentage.
- **Reports**: available to admins from the nav bar; pick a date range to see
  revenue, discounts, tax, a daily chart, payment mix, top products, and
  per-cashier totals.
- **User management**: admins can open **Users** from the nav bar to add
  cashiers/admins, edit names/roles/passwords, or toggle an account
  active/inactive without deleting sales history tied to it.
- **Dark mode**: click the sun/moon icon in the top bar (or on the login
  screen). The choice is remembered in the browser via `localStorage`.

## Design notes

- **Stock safety**: checkout re-checks and locks each product row (`FOR UPDATE`)
  inside a transaction before committing a sale, so two cashiers can't oversell
  the same last unit.
- **Sale line items snapshot the product name and price** at time of sale, so
  editing or renaming a product later doesn't rewrite historical receipts.
- **Soft deletes** on products (`is_active` flag) and users keep old sales
  reports intact even after an item is discontinued or a staff member leaves.
- **Cart lives in the Flask session**, not the database — it's ephemeral by
  design and clears automatically after checkout or logout.
- **Split payments** are stored as individual rows in `sale_payments`, while
  `sales.payment_method` stores a quick summary (`"split"` when more than one
  tender was used, or the single method name otherwise) for fast filtering.
- **Currency and tax rate** are configurable via environment variables
  (`CURRENCY_SYMBOL`, `TAX_RATE`) so the same codebase adapts to different stores.

## Extending it further

Ideas for a next iteration: multi-till support with till reconciliation, receipt
printer (ESC/POS) integration, per-product images, customer accounts/loyalty
points, refunds/returns workflow, CSV/PDF export for reports, and email/SMS
low-stock alerts.

## License

This project is licensed under the [MIT License](LICENSE) — free to use,
modify, and distribute, with attribution.

