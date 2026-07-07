import json
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from pymysql.err import IntegrityError

from config import Config
import db as dbh

app = Flask(__name__)
app.config.from_object(Config)
dbh.init_app(app)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("pos"))
        return view(*args, **kwargs)
    return wrapped


def current_cart():
    return session.setdefault("cart", {})  # {product_id_str: qty}


def pos_redirect():
    """Send the cashier back to whichever Register mode (scan/manual) they
    were using, so an error mid-sale doesn't dump them on the mode chooser."""
    ref = request.referrer or ""
    if "/pos/scan" in ref:
        return redirect(url_for("pos_scan"))
    return redirect(url_for("pos_manual"))


def generate_invoice_no():
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(random.choices(string.digits, k=4))
    return f"INV-{stamp}-{rand}"


@app.context_processor
def inject_globals():
    low_stock_count = 0
    if session.get("user_id"):
        row = dbh.query(
            "SELECT COUNT(*) AS cnt FROM products WHERE stock_qty <= low_stock_at AND is_active=1",
            fetchone=True
        )
        low_stock_count = row["cnt"] if row else 0
    return {
        "store_name": app.config["STORE_NAME"],
        "currency": app.config["CURRENCY_SYMBOL"],
        "current_user": {
            "id": session.get("user_id"),
            "name": session.get("full_name"),
            "role": session.get("role"),
        },
        "cart_count": sum(current_cart().values()) if session.get("user_id") else 0,
        "low_stock_count": low_stock_count,
    }


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("pos_manual"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = dbh.query(
            "SELECT * FROM users WHERE username=%s AND is_active=1",
            (username,), fetchone=True
        )
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name']}.", "success")
            nxt = request.args.get("next") or url_for("pos_manual")
            return redirect(nxt)
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    today_sales = dbh.query(
        "SELECT COALESCE(SUM(total),0) AS total, COUNT(*) AS cnt "
        "FROM sales WHERE DATE(created_at) = CURDATE()",
        fetchone=True
    )
    low_stock = dbh.query(
        "SELECT * FROM products WHERE stock_qty <= low_stock_at AND is_active=1 "
        "ORDER BY stock_qty ASC LIMIT 10"
    )
    recent_sales = dbh.query(
        "SELECT s.*, u.full_name FROM sales s "
        "JOIN users u ON u.id = s.user_id "
        "ORDER BY s.created_at DESC LIMIT 8"
    )
    product_count = dbh.query(
        "SELECT COUNT(*) AS cnt FROM products WHERE is_active=1", fetchone=True
    )

    # ---- 7-day revenue trend ----
    trend_rows = dbh.query(
        "SELECT DATE(created_at) AS d, COALESCE(SUM(total),0) AS total "
        "FROM sales WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY) "
        "GROUP BY DATE(created_at)"
    )
    trend_by_day = {str(r["d"]): float(r["total"]) for r in trend_rows}
    trend_labels, trend_values = [], []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).date()
        trend_labels.append(d.strftime("%a"))
        trend_values.append(trend_by_day.get(str(d), 0.0))

    # ---- Top 5 products (last 30 days) ----
    top_products = dbh.query(
        "SELECT product_name, SUM(qty) AS units, SUM(line_total) AS revenue "
        "FROM sale_items si JOIN sales s ON s.id = si.sale_id "
        "WHERE s.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) "
        "GROUP BY product_name ORDER BY revenue DESC LIMIT 5"
    )

    # ---- Payment method mix (last 30 days) ----
    payment_mix = dbh.query(
        "SELECT method, COALESCE(SUM(amount),0) AS total FROM sale_payments sp "
        "JOIN sales s ON s.id = sp.sale_id "
        "WHERE s.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) "
        "GROUP BY method"
    )

    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        low_stock=low_stock,
        recent_sales=recent_sales,
        product_count=product_count,
        trend_labels=json.dumps(trend_labels),
        trend_values=json.dumps(trend_values),
        top_products=top_products,
        top_products_json=json.dumps([
            {"name": p["product_name"], "revenue": float(p["revenue"])} for p in top_products
        ]),
        payment_mix_json=json.dumps([
            {"method": p["method"], "total": float(p["total"])} for p in payment_mix
        ]),
    )


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------
@app.route("/reports")
@admin_required
def reports():
    start = request.args.get("start") or (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")
    end = request.args.get("end") or datetime.now().strftime("%Y-%m-%d")

    summary = dbh.query(
        "SELECT COALESCE(SUM(total),0) AS revenue, COALESCE(SUM(discount),0) AS discounts, "
        "COALESCE(SUM(tax),0) AS tax, COUNT(*) AS cnt, COALESCE(AVG(total),0) AS avg_sale "
        "FROM sales WHERE DATE(created_at) BETWEEN %s AND %s",
        (start, end), fetchone=True
    )
    daily = dbh.query(
        "SELECT DATE(created_at) AS d, COALESCE(SUM(total),0) AS total, COUNT(*) AS cnt "
        "FROM sales WHERE DATE(created_at) BETWEEN %s AND %s "
        "GROUP BY DATE(created_at) ORDER BY d",
        (start, end)
    )
    top_products = dbh.query(
        "SELECT product_name, SUM(qty) AS units, SUM(line_total) AS revenue "
        "FROM sale_items si JOIN sales s ON s.id = si.sale_id "
        "WHERE DATE(s.created_at) BETWEEN %s AND %s "
        "GROUP BY product_name ORDER BY revenue DESC LIMIT 10",
        (start, end)
    )
    by_cashier = dbh.query(
        "SELECT u.full_name, COUNT(*) AS cnt, COALESCE(SUM(s.total),0) AS total "
        "FROM sales s JOIN users u ON u.id = s.user_id "
        "WHERE DATE(s.created_at) BETWEEN %s AND %s "
        "GROUP BY u.full_name ORDER BY total DESC",
        (start, end)
    )
    payment_mix = dbh.query(
        "SELECT sp.method, COALESCE(SUM(sp.amount),0) AS total FROM sale_payments sp "
        "JOIN sales s ON s.id = sp.sale_id "
        "WHERE DATE(s.created_at) BETWEEN %s AND %s GROUP BY sp.method",
        (start, end)
    )

    return render_template(
        "reports.html",
        start=start, end=end,
        summary=summary, daily=daily,
        top_products=top_products, by_cashier=by_cashier,
        payment_mix=payment_mix,
        daily_json=json.dumps([{"d": str(r["d"]), "total": float(r["total"])} for r in daily]),
        payment_mix_json=json.dumps([{"method": p["method"], "total": float(p["total"])} for p in payment_mix]),
    )


# ------------------------------------------------------------------
# Inventory — CRUD
# ------------------------------------------------------------------
@app.route("/products")
@login_required
def products():
    q = request.args.get("q", "").strip()
    if q:
        rows = dbh.query(
            "SELECT p.*, c.name AS category_name FROM products p "
            "LEFT JOIN categories c ON c.id = p.category_id "
            "WHERE p.is_active=1 AND (p.name LIKE %s OR p.sku LIKE %s OR p.barcode LIKE %s) "
            "ORDER BY p.name",
            (f"%{q}%", f"%{q}%", f"%{q}%")
        )
    else:
        rows = dbh.query(
            "SELECT p.*, c.name AS category_name FROM products p "
            "LEFT JOIN categories c ON c.id = p.category_id "
            "WHERE p.is_active=1 ORDER BY p.name"
        )
    return render_template("products.html", products=rows, q=q)


@app.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    categories = dbh.query("SELECT * FROM categories ORDER BY name")
    if request.method == "POST":
        form = request.form
        try:
            dbh.execute(
                "INSERT INTO products (sku, barcode, name, category_id, price, "
                "cost_price, stock_qty, low_stock_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    form["sku"].strip(),
                    form.get("barcode", "").strip() or None,
                    form["name"].strip(),
                    form.get("category_id") or None,
                    float(form.get("price", 0)),
                    float(form.get("cost_price", 0) or 0),
                    int(form.get("stock_qty", 0) or 0),
                    int(form.get("low_stock_at", 5) or 5),
                )
            )
            flash("Product added.", "success")
            return redirect(url_for("products"))
        except IntegrityError:
            flash("SKU or barcode already exists.", "error")
        except (ValueError, KeyError):
            flash("Please check the form values.", "error")

    return render_template("product_form.html", categories=categories, product=None)


@app.route("/products/<int:pid>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(pid):
    product = dbh.query("SELECT * FROM products WHERE id=%s", (pid,), fetchone=True)
    if not product:
        abort(404)
    categories = dbh.query("SELECT * FROM categories ORDER BY name")

    if request.method == "POST":
        form = request.form
        try:
            dbh.execute(
                "UPDATE products SET sku=%s, barcode=%s, name=%s, category_id=%s, "
                "price=%s, cost_price=%s, stock_qty=%s, low_stock_at=%s WHERE id=%s",
                (
                    form["sku"].strip(),
                    form.get("barcode", "").strip() or None,
                    form["name"].strip(),
                    form.get("category_id") or None,
                    float(form.get("price", 0)),
                    float(form.get("cost_price", 0) or 0),
                    int(form.get("stock_qty", 0) or 0),
                    int(form.get("low_stock_at", 5) or 5),
                    pid,
                )
            )
            flash("Product updated.", "success")
            return redirect(url_for("products"))
        except IntegrityError:
            flash("SKU or barcode already exists.", "error")
        except (ValueError, KeyError):
            flash("Please check the form values.", "error")

    return render_template("product_form.html", categories=categories, product=product)


@app.route("/products/<int:pid>/delete", methods=["POST"])
@admin_required
def product_delete(pid):
    # Soft delete so past sale history stays intact
    dbh.execute("UPDATE products SET is_active=0 WHERE id=%s", (pid,))
    flash("Product removed.", "success")
    return redirect(url_for("products"))


# ------------------------------------------------------------------
# POS — search, cart, checkout
# ------------------------------------------------------------------
@app.route("/pos")
@login_required
def pos():
    categories = dbh.query("SELECT * FROM categories ORDER BY name")
    cart = current_cart()
    cart_items, subtotal = _build_cart_items(cart)
    return render_template(
        "pos.html",
        categories=categories,
        cart_items=cart_items,
        subtotal=subtotal,
        tax_rate=app.config["TAX_RATE"],
    )


@app.route("/pos/scan")
@login_required
def pos_scan():
    cart = current_cart()
    cart_items, subtotal = _build_cart_items(cart)
    return render_template(
        "pos_scan.html",
        cart_items=cart_items,
        subtotal=subtotal,
        tax_rate=app.config["TAX_RATE"],
    )


@app.route("/pos/manual")
@login_required
def pos_manual():
    categories = dbh.query("SELECT * FROM categories ORDER BY name")
    cart = current_cart()
    cart_items, subtotal = _build_cart_items(cart)
    return render_template(
        "pos_manual.html",
        categories=categories,
        cart_items=cart_items,
        subtotal=subtotal,
        tax_rate=app.config["TAX_RATE"],
    )


def _build_cart_items(cart):
    items = []
    subtotal = 0.0
    if cart:
        ids = list(cart.keys())
        placeholders = ",".join(["%s"] * len(ids))
        rows = dbh.query(
            f"SELECT * FROM products WHERE id IN ({placeholders})", ids
        )
        rows_by_id = {str(r["id"]): r for r in rows}
        for pid, qty in cart.items():
            p = rows_by_id.get(pid)
            if not p:
                continue
            line_total = float(p["price"]) * qty
            subtotal += line_total
            items.append({
                "id": p["id"], "name": p["name"], "price": float(p["price"]),
                "qty": qty, "line_total": line_total, "stock_qty": p["stock_qty"],
            })
    return items, subtotal


@app.route("/api/products/search")
@login_required
def api_product_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    rows = dbh.query(
        "SELECT id, sku, barcode, name, price, stock_qty FROM products "
        "WHERE is_active=1 AND (name LIKE %s OR sku LIKE %s OR barcode=%s) "
        "ORDER BY name LIMIT 20",
        (f"%{q}%", f"%{q}%", q)
    )
    for r in rows:
        r["price"] = float(r["price"])
    return jsonify(rows)


@app.route("/api/products/grid")
@login_required
def api_products_grid():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", "").strip()

    where = ["is_active=1"]
    params = []
    if q:
        where.append("(name LIKE %s OR sku LIKE %s OR barcode LIKE %s)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if category_id:
        where.append("category_id=%s")
        params.append(category_id)

    rows = dbh.query(
        "SELECT id, sku, barcode, name, price, stock_qty, category_id FROM products "
        f"WHERE {' AND '.join(where)} ORDER BY name LIMIT 300",
        params
    )
    for r in rows:
        r["price"] = float(r["price"])
    return jsonify(rows)


@app.route("/api/cart/add", methods=["POST"])
@login_required
def api_cart_add():
    data = request.get_json(force=True)
    pid = str(data.get("product_id"))
    qty = int(data.get("qty", 1))

    product = dbh.query("SELECT * FROM products WHERE id=%s AND is_active=1",
                         (pid,), fetchone=True)
    if not product:
        return jsonify({"error": "Product not found."}), 404

    cart = current_cart()
    new_qty = cart.get(pid, 0) + qty
    if new_qty > product["stock_qty"]:
        return jsonify({"error": f"Only {product['stock_qty']} in stock."}), 400
    if new_qty <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = new_qty
    session.modified = True

    items, subtotal = _build_cart_items(cart)
    return jsonify({"items": items, "subtotal": subtotal})


@app.route("/api/cart/update", methods=["POST"])
@login_required
def api_cart_update():
    data = request.get_json(force=True)
    pid = str(data.get("product_id"))
    qty = int(data.get("qty", 0))

    cart = current_cart()
    if qty <= 0:
        cart.pop(pid, None)
    else:
        product = dbh.query("SELECT stock_qty FROM products WHERE id=%s",
                             (pid,), fetchone=True)
        if product and qty > product["stock_qty"]:
            return jsonify({"error": f"Only {product['stock_qty']} in stock."}), 400
        cart[pid] = qty
    session.modified = True

    items, subtotal = _build_cart_items(cart)
    return jsonify({"items": items, "subtotal": subtotal})


@app.route("/api/cart/clear", methods=["POST"])
@login_required
def api_cart_clear():
    session["cart"] = {}
    session.modified = True
    return jsonify({"items": [], "subtotal": 0.0})


@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    cart = current_cart()
    if not cart:
        flash("Cart is empty.", "error")
        return pos_redirect()

    items, subtotal = _build_cart_items(cart)
    if not items:
        flash("Cart items are no longer available.", "error")
        session["cart"] = {}
        return pos_redirect()

    discount_raw = float(request.form.get("discount", 0) or 0)
    discount_type = request.form.get("discount_type", "fixed")
    if discount_type not in ("fixed", "percent"):
        discount_type = "fixed"

    # Normalize discount to a currency amount for storage/calculation
    if discount_type == "percent":
        discount_pct = max(0.0, min(discount_raw, 100.0))
        discount = round(subtotal * discount_pct / 100.0, 2)
    else:
        discount = round(min(discount_raw, subtotal), 2)

    # Parse split-tender payment lines, e.g. [{"method":"cash","amount":10}, ...]
    payments_raw = request.form.get("payments_json", "")
    payment_lines = []
    try:
        parsed = json.loads(payments_raw) if payments_raw else []
        for p in parsed:
            method = p.get("method", "cash")
            amt = float(p.get("amount", 0) or 0)
            if method in ("cash", "card", "mobile_wallet", "credit", "other") and amt > 0:
                payment_lines.append({"method": method, "amount": round(amt, 2)})
    except (ValueError, TypeError, AttributeError):
        payment_lines = []

    if not payment_lines:
        # Fallback to the simple single-method flow for backward compatibility
        single_method = request.form.get("payment_method", "cash")
        single_amount = float(request.form.get("amount_paid", 0) or 0)
        if single_amount > 0:
            payment_lines = [{"method": single_method, "amount": single_amount}]

    amount_paid = round(sum(p["amount"] for p in payment_lines), 2)
    payment_method_summary = (
        payment_lines[0]["method"] if len(payment_lines) == 1
        else "split" if len(payment_lines) > 1 else "cash"
    )

    tax_rate = app.config["TAX_RATE"]
    taxable = max(subtotal - discount, 0)
    tax = round(taxable * tax_rate, 2)
    total = round(taxable + tax, 2)

    if amount_paid + 0.005 < total:
        flash(f"Amount received ({app.config['CURRENCY_SYMBOL']}{amount_paid:.2f}) is less than the total due.", "error")
        return pos_redirect()

    change_due = round(amount_paid - total, 2)

    conn = dbh.get_db()
    try:
        with conn.cursor() as cur:
            # Re-check stock atomically before committing the sale
            for item in items:
                cur.execute("SELECT stock_qty FROM products WHERE id=%s FOR UPDATE",
                            (item["id"],))
                row = cur.fetchone()
                if not row or row["stock_qty"] < item["qty"]:
                    conn.rollback()
                    flash(f"Not enough stock for {item['name']}.", "error")
                    return pos_redirect()

            invoice_no = generate_invoice_no()
            cur.execute(
                "INSERT INTO sales (invoice_no, user_id, subtotal, discount, discount_type, "
                "tax, total, amount_paid, change_due, payment_method) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (invoice_no, session["user_id"], subtotal, discount, discount_type, tax,
                 total, amount_paid, change_due, payment_method_summary)
            )
            sale_id = cur.lastrowid

            for item in items:
                cur.execute(
                    "INSERT INTO sale_items (sale_id, product_id, product_name, "
                    "unit_price, qty, line_total) VALUES (%s,%s,%s,%s,%s,%s)",
                    (sale_id, item["id"], item["name"], item["price"],
                     item["qty"], item["line_total"])
                )
                cur.execute(
                    "UPDATE products SET stock_qty = stock_qty - %s WHERE id=%s",
                    (item["qty"], item["id"])
                )

            for p in payment_lines:
                cur.execute(
                    "INSERT INTO sale_payments (sale_id, method, amount) VALUES (%s,%s,%s)",
                    (sale_id, p["method"], p["amount"])
                )
        conn.commit()
    except IntegrityError as e:
        conn.rollback()
        app.logger.exception("Checkout integrity error for cart items=%r", items)
        # A stale session can leave session['user_id'] pointing at a user row
        # that no longer exists (e.g. account removed/recreated, or the users
        # table was reseeded) — that trips the sales.user_id foreign key.
        user_row = dbh.query("SELECT id FROM users WHERE id=%s", (session.get("user_id"),), fetchone=True)
        if not user_row:
            session.clear()
            flash("Your session is out of date — please log in again.", "error")
            return redirect(url_for("login"))
        flash(f"Checkout failed (data conflict): {e}", "error")
        return pos_redirect()
    except Exception as e:
        conn.rollback()
        app.logger.exception("Checkout failed for cart items=%r payment_lines=%r", items, payment_lines)
        flash(f"Checkout failed: {type(e).__name__}: {e}", "error")
        return pos_redirect()

    session["cart"] = {}
    session.modified = True
    flash("Sale completed.", "success")
    return redirect(url_for("receipt", sale_id=sale_id))


@app.route("/receipt/<int:sale_id>")
@login_required
def receipt(sale_id):
    sale = dbh.query(
        "SELECT s.*, u.full_name FROM sales s JOIN users u ON u.id = s.user_id "
        "WHERE s.id=%s", (sale_id,), fetchone=True
    )
    if not sale:
        abort(404)
    items = dbh.query("SELECT * FROM sale_items WHERE sale_id=%s", (sale_id,))
    payments = dbh.query("SELECT * FROM sale_payments WHERE sale_id=%s", (sale_id,))
    return render_template("receipt.html", sale=sale, items=items, payments=payments)


# ------------------------------------------------------------------
# Sales history
# ------------------------------------------------------------------
@app.route("/sales")
@login_required
def sales_history():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    page = max(int(request.args.get("page", 1) or 1), 1)
    per_page = 50
    offset = (page - 1) * per_page

    where = "WHERE 1=1"
    params = []
    if start:
        where += " AND DATE(s.created_at) >= %s"
        params.append(start)
    if end:
        where += " AND DATE(s.created_at) <= %s"
        params.append(end)

    total_row = dbh.query(
        f"SELECT COUNT(*) AS cnt FROM sales s {where}", params, fetchone=True
    )
    total_count = total_row["cnt"] if total_row else 0
    total_pages = max((total_count + per_page - 1) // per_page, 1)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    rows = dbh.query(
        f"SELECT s.*, u.full_name FROM sales s JOIN users u ON u.id = s.user_id "
        f"{where} ORDER BY s.created_at DESC LIMIT %s OFFSET %s",
        params + [per_page, offset]
    )
    range_summary = dbh.query(
        f"SELECT COALESCE(SUM(s.total),0) AS revenue FROM sales s {where}",
        params, fetchone=True
    )

    return render_template(
        "sales_history.html", sales=rows, start=start, end=end,
        page=page, total_pages=total_pages, total_count=total_count,
        range_revenue=range_summary["revenue"] if range_summary else 0,
    )


# ------------------------------------------------------------------
# Users management (admin only)
# ------------------------------------------------------------------
@app.route("/users")
@admin_required
def users_list():
    rows = dbh.query("SELECT * FROM users ORDER BY is_active DESC, full_name")
    return render_template("users.html", users=rows)


@app.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    if request.method == "POST":
        form = request.form
        try:
            dbh.execute(
                "INSERT INTO users (username, password_hash, full_name, role) "
                "VALUES (%s,%s,%s,%s)",
                (
                    form["username"].strip(),
                    generate_password_hash(form["password"]),
                    form["full_name"].strip(),
                    form.get("role", "cashier"),
                )
            )
            flash("User created.", "success")
            return redirect(url_for("users_list"))
        except IntegrityError:
            flash("Username already exists.", "error")
    return render_template("user_form.html", user=None)


@app.route("/users/<int:uid>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(uid):
    user = dbh.query("SELECT * FROM users WHERE id=%s", (uid,), fetchone=True)
    if not user:
        abort(404)

    if request.method == "POST":
        form = request.form
        try:
            if form.get("password"):
                dbh.execute(
                    "UPDATE users SET full_name=%s, role=%s, password_hash=%s WHERE id=%s",
                    (form["full_name"].strip(), form.get("role", "cashier"),
                     generate_password_hash(form["password"]), uid)
                )
            else:
                dbh.execute(
                    "UPDATE users SET full_name=%s, role=%s WHERE id=%s",
                    (form["full_name"].strip(), form.get("role", "cashier"), uid)
                )
            flash("User updated.", "success")
            return redirect(url_for("users_list"))
        except (ValueError, KeyError):
            flash("Please check the form values.", "error")

    return render_template("user_form.html", user=user)


@app.route("/users/<int:uid>/toggle", methods=["POST"])
@admin_required
def user_toggle(uid):
    if uid == session.get("user_id"):
        flash("You can't deactivate your own account.", "error")
        return redirect(url_for("users_list"))
    user = dbh.query("SELECT * FROM users WHERE id=%s", (uid,), fetchone=True)
    if not user:
        abort(404)
    dbh.execute("UPDATE users SET is_active = NOT is_active WHERE id=%s", (uid,))
    flash(f"{user['full_name']} {'deactivated' if user['is_active'] else 'activated'}.", "success")
    return redirect(url_for("users_list"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
