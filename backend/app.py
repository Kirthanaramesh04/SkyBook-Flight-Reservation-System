import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError

app = Flask(__name__)

# ========================================
# CONFIGURATION
# ========================================

project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

mongodb_uri = os.getenv("MONGODB_URI")

if not mongodb_uri:
    raise ValueError("MONGODB_URI is missing from the .env file.")

client = MongoClient(
    mongodb_uri,
    serverSelectionTimeoutMS=5000
)

db = client["skybook"]
flights_collection = db["flights"]
bookings_collection = db["bookings"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def email_filter(email):
    return {
        "$regex": "^" + re.escape(email) + "$",
        "$options": "i"
    }


# Create an index so booking references cannot be duplicated.
try:
    bookings_collection.create_index(
        [("booking_reference", 1)],
        unique=True,
        name="unique_booking_reference"
    )
except PyMongoError:
    app.logger.exception(
        "Could not create the booking reference index."
    )


# ========================================
# HOME PAGE
# ========================================

@app.route("/")
def home():
    return render_template("index.html")


# ========================================
# HEALTH CHECK
# ========================================

@app.route("/healthz")
def health_check():
    return jsonify({"status": "ok"})


# ========================================
# TEST MONGODB CONNECTION
# ========================================

@app.route("/test-db")
def test_db():
    try:
        client.admin.command("ping")

        return jsonify({
            "status": "success",
            "message": "SkyBook is connected to MongoDB Atlas!"
        })

    except PyMongoError:
        app.logger.exception(
            "MongoDB connection test failed."
        )

        return jsonify({
            "status": "error",
            "message": "Could not connect to MongoDB Atlas."
        }), 500


# ========================================
# GET DYNAMIC FLIGHT SEARCH OPTIONS
# ========================================

@app.route("/flight-options", methods=["GET"])
def flight_options():
    """
    Return cities and travel dates based on the flights
    currently available in MongoDB Atlas.

    Optional query parameters:
      from: selected departure city
      to: selected destination city
    """

    selected_from = request.args.get("from", "").strip()
    selected_to = request.args.get("to", "").strip()

    try:
        # Only consider flights with seats still available.
        available_filter = {
            "available_seats": {"$gt": 0}
        }

        departure_cities = flights_collection.distinct(
            "source",
            available_filter
        )

        destination_cities = flights_collection.distinct(
            "destination",
            available_filter
        )

        # Show only destinations served from the selected
        # departure city.
        available_destinations = []

        if selected_from:
            route_filter = {
                **available_filter,
                "source": {
                    "$regex": "^" + re.escape(selected_from) + "$",
                    "$options": "i"
                }
            }

            available_destinations = flights_collection.distinct(
                "destination",
                route_filter
            )

        # Show dates for the selected route, where provided.
        date_filter = dict(available_filter)

        if selected_from:
            date_filter["source"] = {
                "$regex": "^" + re.escape(selected_from) + "$",
                "$options": "i"
            }

        if selected_to:
            date_filter["destination"] = {
                "$regex": "^" + re.escape(selected_to) + "$",
                "$options": "i"
            }

        travel_dates = flights_collection.distinct(
            "travel_date",
            date_filter
        )

        return jsonify({
            "status": "success",
            "departure_cities": sorted(departure_cities),
            "destination_cities": sorted(destination_cities),
            "available_destinations": sorted(
                available_destinations
            ),
            "travel_dates": sorted(travel_dates)
        })

    except PyMongoError:
        app.logger.exception(
            "Could not retrieve flight search options."
        )

        return jsonify({
            "status": "error",
            "message": "Unable to load flight options right now."
        }), 500


# ========================================
# SEARCH FLIGHTS
# ========================================

@app.route("/search-flights", methods=["POST"])
def search_flights():
    data = request.get_json(silent=True) or {}

    from_city = data.get("from", "")
    to_city = data.get("to", "")
    departure_date = data.get("date", "")

    if not all(
        isinstance(value, str)
        for value in (from_city, to_city, departure_date)
    ):
        return jsonify({
            "status": "error",
            "message": "Invalid flight search details."
        }), 400

    from_city = from_city.strip()
    to_city = to_city.strip()
    departure_date = departure_date.strip()

    if not from_city or not to_city or not departure_date:
        return jsonify({
            "status": "error",
            "message": "Please provide all flight search details."
        }), 400

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", departure_date):
        return jsonify({
            "status": "error",
            "message": "Please use the date format YYYY-MM-DD."
        }), 400

    try:
        datetime.strptime(departure_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Please provide a valid calendar date."
        }), 400

    if from_city.casefold() == to_city.casefold():
        return jsonify({
            "status": "error",
            "message": "Departure and destination must be different."
        }), 400

    try:
        flights = list(flights_collection.find(
            {
                "source": {
                    "$regex": "^" + re.escape(from_city) + "$",
                    "$options": "i"
                },
                "destination": {
                    "$regex": "^" + re.escape(to_city) + "$",
                    "$options": "i"
                },
                "travel_date": departure_date,
                "available_seats": {"$gt": 0}
            },
            {"_id": 0}
        ))

        return jsonify({
            "status": "success",
            "count": len(flights),
            "flights": flights,
            "message": (
                "Flights found."
                if flights else "No flights found for your search."
            )
        })

    except PyMongoError:
        app.logger.exception("Flight search failed.")

        return jsonify({
            "status": "error",
            "message": "Unable to search flights right now."
        }), 500
    # ========================================
# BOOK A FLIGHT — TRANSACTIONAL
# ========================================

@app.route("/book-flight", methods=["POST"])
def book_flight():
    data = request.get_json(silent=True) or {}

    flight_number = data.get("flight_number")
    passenger_name = data.get("passenger_name")
    passenger_email = data.get("passenger_email")
    passenger_phone = data.get("passenger_phone")
    seats = data.get("seats")

    if not all(isinstance(value, str) for value in (
        flight_number,
        passenger_name,
        passenger_email,
        passenger_phone
    )):
        return jsonify({
            "status": "error",
            "message": "Please provide valid passenger and flight details."
        }), 400

    if isinstance(seats, bool) or not isinstance(seats, int):
        return jsonify({
            "status": "error",
            "message": "Number of seats must be a whole number."
        }), 400

    flight_number = flight_number.strip()
    passenger_name = passenger_name.strip()
    passenger_email = passenger_email.strip()
    passenger_phone = passenger_phone.strip()

    if not all((
        flight_number,
        passenger_name,
        passenger_email,
        passenger_phone
    )):
        return jsonify({
            "status": "error",
            "message": "Please fill in all passenger details."
        }), 400

    if len(passenger_name) > 100:
        return jsonify({
            "status": "error",
            "message": "Passenger name is too long."
        }), 400

    if not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        passenger_email
    ):
        return jsonify({
            "status": "error",
            "message": "Please enter a valid email address."
        }), 400

    if not re.fullmatch(r"[0-9+() -]{7,20}", passenger_phone):
        return jsonify({
            "status": "error",
            "message": "Please enter a valid phone number."
        }), 400

    if not 1 <= seats <= 6:
        return jsonify({
            "status": "error",
            "message": "You can book between 1 and 6 seats."
        }), 400

    booking_reference = "SKY-" + uuid.uuid4().hex[:8].upper()
    booking_result = {}

    def create_booking_transaction(session):
        flight = flights_collection.find_one_and_update(
            {
                "flight_number": flight_number,
                "available_seats": {"$gte": seats}
            },
            {"$inc": {"available_seats": -seats}},
            return_document=ReturnDocument.BEFORE,
            session=session
        )

        if flight is None:
            raise ValueError("FLIGHT_UNAVAILABLE")

        total_price = float(flight["price"]) * seats

        booking = {
            "booking_reference": booking_reference,
            "flight_id": flight["_id"],
            "flight_number": flight["flight_number"],
            "airline": flight["airline"],
            "source": flight["source"],
            "destination": flight["destination"],
            "travel_date": flight["travel_date"],
            "departure_time": flight["departure_time"],
            "arrival_time": flight["arrival_time"],
            "passenger_name": passenger_name,
            "passenger_email": passenger_email,
            "passenger_phone": passenger_phone,
            "seats": seats,
            "price_per_seat": flight["price"],
            "total_price": total_price,
            "booking_status": "CONFIRMED",
            "payment_status": "NOT_PAID",
            "created_at": utc_now()
        }

        bookings_collection.insert_one(
            booking,
            session=session
        )

        booking_result.update({
            "booking_reference": booking_reference,
            "flight_number": flight["flight_number"],
            "airline": flight["airline"],
            "source": flight["source"],
            "destination": flight["destination"],
            "travel_date": flight["travel_date"],
            "departure_time": flight["departure_time"],
            "arrival_time": flight["arrival_time"],
            "passenger_name": passenger_name,
            "seats": seats,
            "price_per_seat": flight["price"],
            "total_price": total_price,
            "booking_status": "CONFIRMED",
            "payment_status": "NOT_PAID"
        })

    try:
        with client.start_session() as session:
            session.with_transaction(create_booking_transaction)

        return jsonify({
            "status": "success",
            "message": "Demo booking confirmed successfully!",
            "booking": booking_result
        }), 201

    except ValueError as exc:
        if str(exc) == "FLIGHT_UNAVAILABLE":
            return jsonify({
                "status": "error",
                "message": (
                    "This flight is unavailable or does not have "
                    "enough seats remaining."
                )
            }), 409

        app.logger.exception("Unexpected booking validation error.")

        return jsonify({
            "status": "error",
            "message": "Unable to complete this booking."
        }), 500

    except PyMongoError:
        app.logger.exception("Transactional flight booking failed.")

        return jsonify({
            "status": "error",
            "message": (
                "We could not confirm the booking. Check your booking "
                "status before trying again."
            )
        }), 500


# ========================================
# LOOK UP AN EXISTING BOOKING
# ========================================

@app.route("/my-booking", methods=["POST"])
def my_booking():
    data = request.get_json(silent=True) or {}

    booking_reference = data.get("booking_reference")
    passenger_email = data.get("passenger_email")

    if not isinstance(booking_reference, str) or not isinstance(
        passenger_email, str
    ):
        return jsonify({
            "status": "error",
            "message": "Please provide your booking reference and email."
        }), 400

    booking_reference = booking_reference.strip().upper()
    passenger_email = passenger_email.strip()

    if not booking_reference or not passenger_email:
        return jsonify({
            "status": "error",
            "message": "Both fields are required."
        }), 400

    try:
        booking = bookings_collection.find_one(
            {
                "booking_reference": booking_reference,
                "passenger_email": email_filter(passenger_email)
            },
            {
                "_id": 0,
                "flight_id": 0,
                "passenger_phone": 0
            }
        )

        if booking is None:
            return jsonify({
                "status": "error",
                "message": (
                    "No booking matched those details. "
                    "Check your reference and email."
                )
            }), 404

        return jsonify({
            "status": "success",
            "message": "Booking found.",
            "booking": booking
        })

    except PyMongoError:
        app.logger.exception("Booking lookup failed.")

        return jsonify({
            "status": "error",
            "message": "Unable to retrieve the booking right now."
        }), 500
    # ========================================
# SAFE DEMO PAYMENT
# ========================================

@app.route("/demo-payment", methods=["POST"])
def demo_payment():
    data = request.get_json(silent=True) or {}

    booking_reference = data.get("booking_reference")
    passenger_email = data.get("passenger_email")

    if not isinstance(booking_reference, str) or not isinstance(
        passenger_email, str
    ):
        return jsonify({
            "status": "error",
            "message": "Please provide your booking reference and email."
        }), 400

    booking_reference = booking_reference.strip().upper()
    passenger_email = passenger_email.strip()

    if not booking_reference or not passenger_email:
        return jsonify({
            "status": "error",
            "message": "Both booking reference and email are required."
        }), 400

    booking_filter = {
        "booking_reference": booking_reference,
        "passenger_email": email_filter(passenger_email)
    }

    try:
        booking = bookings_collection.find_one(booking_filter)

        if booking is None:
            return jsonify({
                "status": "error",
                "message": "No booking matched those details."
            }), 404

        if booking.get("booking_status") != "CONFIRMED":
            return jsonify({
                "status": "error",
                "message": "Only confirmed bookings can use demo payment."
            }), 409

        if booking.get("payment_status") == "DEMO_PAID":
            return jsonify({
                "status": "success",
                "message": "This demo booking has already been marked paid.",
                "payment_status": "DEMO_PAID",
                "booking_reference": booking_reference,
                "total_price": booking.get("total_price")
            })

        if booking.get("payment_status") != "NOT_PAID":
            return jsonify({
                "status": "error",
                "message": "This booking is not eligible for demo payment."
            }), 409

        updated = bookings_collection.find_one_and_update(
            {
                **booking_filter,
                "booking_status": "CONFIRMED",
                "payment_status": "NOT_PAID"
            },
            {
                "$set": {
                    "payment_status": "DEMO_PAID",
                    "demo_payment_at": utc_now()
                }
            },
            projection={
                "_id": 0,
                "booking_reference": 1,
                "payment_status": 1,
                "total_price": 1
            },
            return_document=ReturnDocument.AFTER
        )

        if updated is None:
            latest = bookings_collection.find_one(booking_filter)

            if latest and latest.get("booking_status") != "CONFIRMED":
                return jsonify({
                    "status": "error",
                    "message": (
                        "Only confirmed bookings can use demo payment."
                    )
                }), 409

            if latest and latest.get("payment_status") == "DEMO_PAID":
                return jsonify({
                    "status": "success",
                    "message": (
                        "This demo booking has already been marked paid."
                    ),
                    "payment_status": "DEMO_PAID",
                    "booking_reference": booking_reference,
                    "total_price": latest.get("total_price")
                })

            return jsonify({
                "status": "error",
                "message": (
                    "The booking could not be updated. Check its status."
                )
            }), 409

        return jsonify({
            "status": "success",
            "message": (
                "Demo payment completed successfully. "
                "No real money was charged."
            ),
            "payment_status": updated["payment_status"],
            "booking_reference": updated["booking_reference"],
            "total_price": updated.get("total_price")
        })

    except PyMongoError:
        app.logger.exception("Demo payment update failed.")

        return jsonify({
            "status": "error",
            "message": "Unable to update the demo payment right now."
        }), 500
    # ========================================
# CANCEL A TICKET — TRANSACTIONAL
# ========================================

@app.route("/cancel-booking", methods=["POST"])
def cancel_booking():
    data = request.get_json(silent=True) or {}

    booking_reference = data.get("booking_reference")
    passenger_email = data.get("passenger_email")

    if not isinstance(booking_reference, str) or not isinstance(
        passenger_email, str
    ):
        return jsonify({
            "status": "error",
            "message": "Please provide your booking reference and email."
        }), 400

    booking_reference = booking_reference.strip().upper()
    passenger_email = passenger_email.strip()

    if not booking_reference or not passenger_email:
        return jsonify({
            "status": "error",
            "message": "Both booking reference and email are required."
        }), 400

    booking_filter = {
        "booking_reference": booking_reference,
        "passenger_email": email_filter(passenger_email)
    }

    result = {}

    def cancel_transaction(session):
        booking = bookings_collection.find_one(
            booking_filter,
            session=session
        )

        if booking is None:
            raise ValueError("BOOKING_NOT_FOUND")

        if booking.get("booking_status") == "CANCELLED":
            raise ValueError("ALREADY_CANCELLED")

        if booking.get("booking_status") != "CONFIRMED":
            raise ValueError("BOOKING_NOT_CANCELLABLE")

        flight_id = booking.get("flight_id")

        if flight_id is not None:
            flight_filter = {"_id": flight_id}
        else:
            # For older bookings without flight_id, proceed only
            # if exactly one matching flight exists.
            matching_flights = list(
                flights_collection.find(
                    {"flight_number": booking.get("flight_number")},
                    {"_id": 1},
                    session=session
                ).limit(2)
            )

            if len(matching_flights) != 1:
                raise ValueError("LEGACY_FLIGHT_AMBIGUOUS")

            flight_filter = {
                "_id": matching_flights[0]["_id"]
            }

        old_payment_status = booking.get(
            "payment_status",
            "NOT_PAID"
        )

        updated_booking = bookings_collection.find_one_and_update(
            {
                "_id": booking["_id"],
                "booking_status": "CONFIRMED"
            },
            {
                "$set": {
                    "booking_status": "CANCELLED",
                    "cancelled_at": utc_now(),
                    "payment_status": (
                        "DEMO_REFUNDED"
                        if old_payment_status == "DEMO_PAID"
                        else old_payment_status
                    ),
                    "demo_refund_note": (
                        "Simulated only; no real payment or refund occurred."
                        if old_payment_status == "DEMO_PAID"
                        else None
                    )
                }
            },
            return_document=ReturnDocument.AFTER,
            session=session
        )

        if updated_booking is None:
            raise ValueError("ALREADY_CANCELLED")

        restored = flights_collection.update_one(
            flight_filter,
            {"$inc": {"available_seats": booking["seats"]}},
            session=session
        )

        if restored.matched_count != 1:
            raise ValueError("FLIGHT_NOT_FOUND")

        result.update({
            "booking_reference": booking_reference,
            "booking_status": "CANCELLED",
            "payment_status": updated_booking.get("payment_status"),
            "seats_restored": booking["seats"]
        })

    try:
        with client.start_session() as session:
            session.with_transaction(cancel_transaction)

        return jsonify({
            "status": "success",
            "message": (
                "Ticket cancelled successfully. "
                "The reserved seats have been restored."
            ),
            "booking": result
        })

    except ValueError as exc:
        error = str(exc)

        responses = {
            "BOOKING_NOT_FOUND": (
                "No booking matched those details.", 404
            ),
            "ALREADY_CANCELLED": (
                "This booking has already been cancelled.", 409
            ),
            "BOOKING_NOT_CANCELLABLE": (
                "This booking cannot be cancelled in its current state.",
                409
            ),
            "LEGACY_FLIGHT_AMBIGUOUS": (
                "This older booking cannot be safely cancelled automatically. "
                "Please contact the demo administrator.",
                409
            ),
            "FLIGHT_NOT_FOUND": (
                "The associated flight could not be found. "
                "No changes were saved.",
                409
            )
        }

        message_text, status_code = responses.get(
            error,
            ("Unable to cancel this booking.", 409)
        )

        return jsonify({
            "status": "error",
            "message": message_text
        }), status_code

    except PyMongoError:
        app.logger.exception(
            "Transactional ticket cancellation failed."
        )

        return jsonify({
            "status": "error",
            "message": (
                "Unable to cancel the ticket right now. "
                "Please check the booking status before retrying."
            )
        }), 500


# ========================================
# RUN APPLICATION
# ========================================

if __name__ == "__main__":
    app.run(debug=True)