import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime

try:
    from flask_pymongo import PyMongo
    from bson import ObjectId
    mongo_available = True
except ImportError:
    mongo_available = False

load_dotenv()

app = Flask(__name__)

# Config
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["MONGO_URI"] = os.getenv("MONGO_URI")

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# MongoDB client (if available)
db = None
if mongo_available and app.config.get("MONGO_URI"):
    try:
        mongodb_client = PyMongo(app)
        db = mongodb_client.db
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")
        db = None

# Fallback fake DB (only in-memory, resets on restart)
fake_db = {"items": [], "consents": []}


# ---------------- Routes ---------------- #

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to Flask backend!"})


@app.route("/api/hello", methods=["GET"])
def hello():
    return jsonify({"message": "Hello from Flask!"})


@app.route("/api/items", methods=["POST"])
def add_item():
    data = request.json
    if db:
        item_id = db.items.insert_one(data).inserted_id
        return jsonify({"_id": str(item_id), **data}), 201
    else:
        data["_id"] = str(len(fake_db["items"]) + 1)
        fake_db["items"].append(data)
        return jsonify(data), 201


@app.route("/api/items", methods=["GET"])
def get_items():
    if db:
        items = list(db.items.find())
        for item in items:
            item["_id"] = str(item["_id"])
        return jsonify(items)
    else:
        return jsonify(fake_db["items"])


@app.route("/api/items/<id>", methods=["DELETE"])
def delete_item(id):
    if db:
        db.items.delete_one({"_id": ObjectId(id)})
        return jsonify({"message": "Item deleted"})
    else:
        fake_db["items"] = [i for i in fake_db["items"] if i["_id"] != id]
        return jsonify({"message": "Item deleted"})


# ----------- Setu AA Consent Flow ----------- #
@app.route("/api/initiate-consent", methods=["POST"])
def initiate_consent():
    try:
        url = f"{os.getenv('SETU_BASE_URL')}/consents"

        headers = {
            "x-client-id": os.getenv("SETU_CLIENT_ID"),
            "x-client-secret": os.getenv("SETU_CLIENT_SECRET"),
            "x-product-instance-id": os.getenv("SETU_PRODUCT_ID"),
            "Content-Type": "application/json"
        }

        payload = {
            "consentDuration": {"unit": "MONTH", "value": "4"},
            "vua": "999999999@onemoney",  # sandbox handle
            "dataRange": {
                "from": "2024-01-01T00:00:00Z",
                "to": "2025-09-04T00:00:00Z"
            },
            "context": [],
            "redirectUrl": os.getenv("SETU_CALLBACK_URL"),
            "additionalParams": {
                "tags": ["Loan_Tracking", "Spending_Analysis"]
            }
        }

        print("➡️ Sending request to:", url)
        print("➡️ Headers:", {k: ("****" if "secret" in k else v) for k, v in headers.items()})
        print("➡️ Payload:", payload)

        resp = requests.post(url, headers=headers, json=payload)

        print("➡️ Response status:", resp.status_code)
        print("➡️ Response text:", resp.text)

        try:
            data = resp.json()
        except Exception:
            data = {"error": "Invalid JSON from Setu", "raw": resp.text}

        if resp.status_code == 200 and "id" in data:
            consent_record = {
                "consent_id": data["id"],
                "status": data.get("status", "PENDING"),
                "url": data.get("url"),
                "created_at": datetime.utcnow()
            }
            if db:
                db.consents.insert_one(consent_record)
            else:
                fake_db["consents"].append(consent_record)

        return jsonify(data), resp.status_code

    except Exception as e:
        print("❌ Error in initiate-consent:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/api/consent-status/<consent_id>", methods=["GET"])
def consent_status(consent_id):
    if db:
        consent = db.consents.find_one({"consent_id": consent_id})
        if not consent:
            return jsonify({"error": "Consent not found"}), 404
        consent["_id"] = str(consent["_id"])
        return jsonify(consent)
    else:
        for consent in fake_db["consents"]:
            if consent["consent_id"] == consent_id:
                return jsonify(consent)
        return jsonify({"error": "Consent not found"}), 404


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
    return response


# ---------------- Run ---------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
