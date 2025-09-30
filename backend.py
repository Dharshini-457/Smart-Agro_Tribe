# backend.py
from flask import Flask, request, jsonify
import random
import hashlib

app = Flask(__name__)

ledger = []  # simple in-memory ledger

# Calculate dynamic price
def calculate_dynamic_price(masp: float) -> dict:
    platform_fee = 3
    market_adjustment = random.choice([-1, 0, 2])
    final_price = masp + platform_fee + market_adjustment
    if final_price < masp:
        final_price = masp + platform_fee
        market_adjustment = 0
    if market_adjustment > 0:
        recommendation = "Buy now – price expected to rise"
    elif market_adjustment < 0:
        recommendation = "You may wait – price expected to drop"
    else:
        recommendation = "Price stable"
    return {
        "masp": masp,
        "platform_fee": platform_fee,
        "market_adjustment": market_adjustment,
        "final_price": final_price,
        "recommendation": recommendation
    }

# Generate blockchain hash
def generate_hash(order: dict) -> str:
    order_str = str(order)
    return hashlib.sha256(order_str.encode()).hexdigest()

# API endpoint: dynamic price
@app.route("/api/dynamic-price", methods=["POST"])
def dynamic_price():
    data = request.json
    masp = float(data.get("masp", 0))
    product = data.get("product", "Unknown")
    price_info = calculate_dynamic_price(masp)
    order = {
        "product": product,
        "masp": masp,
        "final_price": price_info["final_price"],
        "qty": data.get("qty", 1)
    }
    order["hash"] = generate_hash(order)
    ledger.append(order)
    price_info["order_hash"] = order["hash"]
    return jsonify(price_info)

# API endpoint: ledger
@app.route("/api/ledger", methods=["GET"])
def get_ledger():
    return jsonify(ledger)

if __name__ == "_main_":
    app.run(debug=True)