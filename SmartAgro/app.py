# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
import os
import json
import hashlib
import random
from datetime import datetime

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "replace-this-with-a-secure-key"

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
LEDGER_FILE = os.path.join(DATA_DIR, "ledger.json")

PLATFORM_FEE = 3.0  # fixed platform fee (per unit for demo)

# Ensure data dir and files exist
os.makedirs(DATA_DIR, exist_ok=True)
for path, default in [
    (USERS_FILE, {}),
    (PRODUCTS_FILE, []),
    (ORDERS_FILE, []),
    (LEDGER_FILE, [])
]:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)

# Helpers to load & save JSON
def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Simple dynamic pricing calculation function
def calculate_dynamic_price(masp: float, available_qty: int = 0) -> dict:
    # Very simple market adjustment logic for demo:
    # If available_qty is large -> small negative adjustment (surplus)
    # If available_qty is small -> positive adjustment (scarcity)
    if available_qty <= 20:
        market_adjustment = 2.0
    elif available_qty <= 100:
        market_adjustment = 0.0
    else:
        market_adjustment = -1.0

    # small random jitter to vary demo
    market_adjustment += random.choice([0.0, 0.0, 0.0, 1.0])  # mostly stable, sometimes +1

    final_price = round(masp + PLATFORM_FEE + market_adjustment, 2)

    # enforce farmer protection: ensure final_price >= masp + PLATFORM_FEE
    min_allowed = round(masp + PLATFORM_FEE, 2)
    if final_price < min_allowed:
        final_price = min_allowed
        market_adjustment = round(final_price - masp - PLATFORM_FEE, 2)

    if market_adjustment > 0:
        recommendation = "Buy now — price expected to rise"
    elif market_adjustment < 0:
        recommendation = "You may wait — price expected to drop"
    else:
        recommendation = "Price stable"

    return {
        "masp": masp,
        "platform_fee": PLATFORM_FEE,
        "market_adjustment": market_adjustment,
        "final_price": final_price,
        "recommendation": recommendation
    }

# Simple SHA256 "blockchain" hash for an order dict
def generate_order_hash(order: dict) -> str:
    s = json.dumps(order, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# Routes - pages
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/farmer")
def farmer_page():
    # we render static template; data fetched by JS
    return render_template("farmer_dashboard.html")

@app.route("/buyer")
def buyer_page():
    return render_template("buyer_dashboard.html")

# API: Register
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or request.form
    name = data.get("name") or ""
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "buyer")

    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password required"}), 400

    users = read_json(USERS_FILE)
    if email in users:
        return jsonify({"ok": False, "error": "User already exists"}), 400

    users[email] = {
        "name": name,
        "email": email,
        "password": password,
        "role": role,
        "created_at": datetime.utcnow().isoformat()
    }
    write_json(USERS_FILE, users)
    return jsonify({"ok": True, "message": "User registered"})

# API: Login
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or request.form
    email = data.get("email")
    password = data.get("password")
    users = read_json(USERS_FILE)
    user = users.get(email)
    if not user or user.get("password") != password:
        return jsonify({"ok": False, "error": "Invalid credentials"}), 401
    # create a simple session token for demo (not secure)
    session["email"] = email
    session["role"] = user.get("role")
    return jsonify({"ok": True, "role": user.get("role"), "name": user.get("name", "")})

# API: Logout
@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

# API: Add product (Farmer)
@app.route("/api/products", methods=["POST"])
def api_add_product():
    data = request.json or request.form
    farmer_email = data.get("farmer_email")
    name = data.get("name")
    masp = float(data.get("masp", 0))
    available = int(data.get("available", 0))
    category = data.get("category", "")
    quality = data.get("quality", "")

    if not farmer_email or not name:
        return jsonify({"ok": False, "error": "Missing fields"}), 400

    products = read_json(PRODUCTS_FILE)
    product_id = max([p.get("id", 0) for p in products] + [0]) + 1
    product = {
        "id": product_id,
        "name": name,
        "farmer_email": farmer_email,
        "category": category,
        "quality": quality,
        "masp": masp,
        "available": available,
        "created_at": datetime.utcnow().isoformat()
    }
    products.append(product)
    write_json(PRODUCTS_FILE, products)
    return jsonify({"ok": True, "product": product})

# API: List products (for buyers)
@app.route("/api/products", methods=["GET"])
def api_list_products():
    products = read_json(PRODUCTS_FILE)
    # attach current price via dynamic pricing
    enriched = []
    for p in products:
        dp = calculate_dynamic_price(p.get("masp", 0), p.get("available", 0))
        enriched.append({
            **p,
            "current_price": dp["final_price"],
            "pricing_breakdown": dp
        })
    return jsonify(enriched)

# API: Get farmer's products & orders
@app.route("/api/farmer/<email>/products", methods=["GET"])
def api_farmer_products(email):
    products = read_json(PRODUCTS_FILE)
    farmer_products = [p for p in products if p.get("farmer_email") == email]
    orders = read_json(ORDERS_FILE)
    farmer_orders = [o for o in orders if o.get("farmer_email") == email]
    return jsonify({"products": farmer_products, "orders": farmer_orders})

# API: Place order (Buyer)
@app.route("/api/orders", methods=["POST"])
def api_place_order():
    data = request.json or request.form
    buyer_name = data.get("buyer_name")
    buyer_email = data.get("buyer_email")
    product_id = int(data.get("product_id"))
    qty = int(data.get("qty", 1))

    products = read_json(PRODUCTS_FILE)
    product = next((p for p in products if p.get("id") == product_id), None)
    if not product:
        return jsonify({"ok": False, "error": "Product not found"}), 404

    # compute dynamic price at time of order
    pricing = calculate_dynamic_price(product.get("masp", 0), product.get("available", 0))
    final_price_per_unit = pricing["final_price"]
    total_price = round(final_price_per_unit * qty, 2)

    # reduce available qty (simple)
    if product.get("available", 0) < qty:
        return jsonify({"ok": False, "error": "Not enough stock"}), 400
    product["available"] = product.get("available", 0) - qty
    write_json(PRODUCTS_FILE, products)

    orders = read_json(ORDERS_FILE)
    order_id = max([o.get("id", 0) for o in orders] + [1000]) + 1
    order = {
        "id": order_id,
        "product_id": product_id,
        "product_name": product.get("name"),
        "farmer_email": product.get("farmer_email"),
        "buyer_name": buyer_name,
        "buyer_email": buyer_email,
        "qty": qty,
        "unit_price": final_price_per_unit,
        "total_price": total_price,
        "created_at": datetime.utcnow().isoformat(),
        "status": "placed",
        "pricing_breakdown": pricing
    }
    orders.append(order)
    write_json(ORDERS_FILE, orders)

    # create ledger record (hash)
    ledger = read_json(LEDGER_FILE)
    ledger_entry = {
        "order_id": order_id,
        "order": order,
        "timestamp": datetime.utcnow().isoformat()
    }
    ledger_entry["hash"] = generate_order_hash(ledger_entry)
    ledger.append(ledger_entry)
    write_json(LEDGER_FILE, ledger)

    return jsonify({"ok": True, "order": order, "ledger_entry": ledger_entry})

# API: ledger (for audit)
@app.route("/api/ledger", methods=["GET"])
def api_ledger():
    ledger = read_json(LEDGER_FILE)
    return jsonify(ledger)

# Static file serving (optional)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__== "__main__":
    app.run(debug=True)