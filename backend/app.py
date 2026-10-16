
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# Load the .env file from the project root
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

# Read the MongoDB connection string
mongodb_uri = os.getenv("MONGODB_URI")

if not mongodb_uri:
    raise ValueError("MONGODB_URI is missing from the .env file.")

# Create the MongoDB client and select our database
client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
db = client["skybook"]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/test-db")
def test_db():
    try:
        client.admin.command("ping")
        return jsonify({
            "status": "success",
            "message": "SkyBook is connected to MongoDB Atlas!"
        })
    except Exception:
        app.logger.exception("MongoDB connection test failed.")
        return jsonify({
            "status": "error",
            "message": "Could not connect to MongoDB Atlas. Check the connection and network."
        }), 500


@app.route("/search-flights", methods=["POST"])
def search_flights():
    data = request.get_json() or {}

    from_city = data.get("from", "").strip()
    to_city = data.get("to", "").strip()
    departure_date = data.get("date", "")

    if not from_city or not to_city or not departure_date:
        return jsonify({
            "message": "Please provide all flight search details."
        }), 400

    if from_city.lower() == to_city.lower():
        return jsonify({
            "message": "Departure and destination must be different."
        }), 400

    return jsonify({
        "message": (
            f"Flight search received: {from_city} to "
            f"{to_city} on {departure_date}."
        )
    })


if __name__ == "__main__":
    app.run(debug=True)
