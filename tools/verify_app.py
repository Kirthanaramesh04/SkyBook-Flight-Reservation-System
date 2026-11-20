"""
SkyBook verification script
===========================

Checks your REAL Flask app against your REAL MongoDB data, using Flask's
built-in test client. Nothing is deployed and no web server has to be running.

What it checks
  1. /flight-options: every city lists every other city as a destination.
  2. /flight-options: every route (both directions) lists all 61 dates.
  3. /search-flights: returns flights with seats for the dates it checks.
  4. Response times of /flight-options (helps with the dropdown speed work).
  5. Optional --booking-test: one booking, demo payment, lookup and
     cancellation, then checks the seat count came back to where it started.

USAGE (PowerShell, project root, virtual environment active)
    python tools\\verify_app.py                  # quick check (5 sample dates)
    python tools\\verify_app.py --full           # every route on every date
    python tools\\verify_app.py --booking-test   # also test booking/cancel

The booking test leaves ONE booking in your database with status CANCELLED
(bookings are never deleted). Its email is skybook.test@example.com.
"""

import argparse
import statistics
import sys
import time
from datetime import date, timedelta
from itertools import permutations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app import (  # noqa: E402
    app, flights_collection, DEMO_START_DATE, DEMO_END_DATE,
)

SAMPLE_DATES = ["2026-11-01", "2026-11-15", "2026-12-01",
                "2026-12-15", "2026-12-31"]
TEST_EMAIL = "skybook.test@example.com"

timings = []


def all_dates():
    start = date.fromisoformat(DEMO_START_DATE)
    end = date.fromisoformat(DEMO_END_DATE)
    return [(start + timedelta(days=i)).isoformat()
            for i in range((end - start).days + 1)]


def get_json(client, url):
    started = time.perf_counter()
    response = client.get(url)
    timings.append((time.perf_counter() - started) * 1000)
    return response.status_code, (response.get_json(silent=True) or {})


def check_options(client, dates):
    problems = []
    status, data = get_json(client, "/flight-options")
    cities = data.get("departure_cities", [])
    print(f"Departure cities from /flight-options: {len(cities)} -> "
          f"{', '.join(cities)}")
    if status != 200 or len(cities) < 2:
        return cities, ["/flight-options did not return enough cities"]

    for city in cities:
        status, data = get_json(client, f"/flight-options?from={city}")
        got = set(data.get("available_destinations", []))
        expected = set(cities) - {city}
        if status != 200 or not expected <= got:
            problems.append(
                f"{city}: missing destinations {sorted(expected - got)}")
        if city in got:
            problems.append(f"{city} appears as its own destination")

    for source, destination in permutations(cities, 2):
        status, data = get_json(
            client, f"/flight-options?from={source}&to={destination}")
        got = set(data.get("travel_dates", []))
        missing = [d for d in dates if d not in got]
        if status != 200 or missing:
            problems.append(
                f"{source} -> {destination}: {len(missing)} dates missing "
                f"(first: {missing[:3]})")

    return cities, problems


def check_search(client, cities, dates_to_check):
    problems = []
    checks = 0
    total = len(list(permutations(cities, 2))) * len(dates_to_check)

    for source, destination in permutations(cities, 2):
        for travel_date in dates_to_check:
            response = client.post("/search-flights", json={
                "from": source, "to": destination, "date": travel_date})
            data = response.get_json(silent=True) or {}
            flights = data.get("flights", [])
            checks += 1

            if response.status_code != 200 or data.get("status") != "success":
                problems.append(f"{source}->{destination} {travel_date}: "
                                f"HTTP {response.status_code}")
            elif not flights:
                problems.append(f"{source}->{destination} {travel_date}: "
                                "no flights returned")
            elif any(
                f.get("source", "").casefold() != source.casefold()
                or f.get("destination", "").casefold()
                != destination.casefold()
                or f.get("travel_date") != travel_date
                or not f.get("available_seats", 0) > 0
                for f in flights
            ):
                problems.append(f"{source}->{destination} {travel_date}: "
                                "a returned flight does not match the search")

            if checks % 500 == 0:
                print(f"  ...{checks} of {total} searches done")

    return checks, problems


def booking_test(client):
    print("\n=== BOOKING / PAYMENT / LOOKUP / CANCELLATION TEST ===")
    flight = flights_collection.find_one({
        "available_seats": {"$gte": 3},
        "travel_date": {"$gte": DEMO_START_DATE, "$lte": DEMO_END_DATE},
    })
    if flight is None:
        print("FAIL: could not find a flight with at least 3 seats.")
        return False

    flight_id = flight["_id"]
    number = flight["flight_number"]
    before = flights_collection.find_one({"_id": flight_id})["available_seats"]
    print(f"Test flight {number} "
          f"({flight['source']} -> {flight['destination']}, "
          f"{flight['travel_date']}), seats before: {before}")

    def post(url, body):
        response = client.post(url, json=body)
        return response.status_code, (response.get_json(silent=True) or {})

    status, data = post("/book-flight", {
        "flight_number": number, "passenger_name": "SkyBook Test",
        "passenger_email": TEST_EMAIL, "passenger_phone": "9999999999",
        "seats": 2})
    if status != 201:
        print("FAIL: booking returned", status, data.get("message"))
        return False
    reference = data["booking"]["booking_reference"]
    after_booking = flights_collection.find_one(
        {"_id": flight_id})["available_seats"]
    print(f"1. Booked {reference}; seats now {after_booking} "
          f"(expected {before - 2})")
    ok = after_booking == before - 2

    credentials = {"booking_reference": reference,
                   "passenger_email": TEST_EMAIL}

    status, data = post("/demo-payment", credentials)
    paid = status == 200 and data.get("payment_status") == "DEMO_PAID"
    print(f"2. Demo payment: {data.get('payment_status')}")
    ok = ok and paid

    status, data = post("/my-booking", credentials)
    found = (status == 200 and data.get("booking", {})
             .get("booking_reference") == reference)
    print(f"3. Booking lookup: {'found' if found else 'NOT found'}")
    ok = ok and found

    status, data = post("/cancel-booking", credentials)
    cancelled = (status == 200 and data.get("booking", {})
                 .get("booking_status") == "CANCELLED")
    print(f"4. Cancellation: {data.get('message')}")
    ok = ok and cancelled

    final = flights_collection.find_one({"_id": flight_id})["available_seats"]
    print(f"5. Seats after cancellation: {final} (expected {before})")
    ok = ok and final == before

    status, data = post("/cancel-booking", credentials)
    twice = status == 409
    print(f"6. Cancelling twice is refused: {'yes' if twice else 'NO'}")
    ok = ok and twice

    print("Booking test:", "PASS" if ok else "FAIL")
    return ok


def main():
    parser = argparse.ArgumentParser(description="Verify the SkyBook app.")
    parser.add_argument("--full", action="store_true",
                        help="Search every route on every date (slower).")
    parser.add_argument("--booking-test", action="store_true",
                        help="Also test booking, payment and cancellation.")
    args = parser.parse_args()

    dates = all_dates()
    dates_to_check = dates if args.full else SAMPLE_DATES
    client = app.test_client()

    print(f"Dates expected: {len(dates)} "
          f"({DEMO_START_DATE} to {DEMO_END_DATE})\n")

    print("=== /flight-options ===")
    cities, option_problems = check_options(client, dates)
    routes = len(list(permutations(cities, 2)))
    print(f"Routes checked: {routes}   Problems: {len(option_problems)}")
    for problem in option_problems[:15]:
        print("  -", problem)

    print("\n=== /search-flights ===")
    searches, search_problems = check_search(client, cities, dates_to_check)
    print(f"Searches run: {searches}   Problems: {len(search_problems)}")
    for problem in search_problems[:15]:
        print("  -", problem)

    if timings:
        print("\n=== /flight-options RESPONSE TIME (server side, in ms) ===")
        print(f"Calls: {len(timings)}   average: "
              f"{statistics.mean(timings):.0f}   "
              f"slowest: {max(timings):.0f}")

    passed = not option_problems and not search_problems
    if args.booking_test:
        answer = input("\nThe booking test changes seat counts and leaves one "
                       "CANCELLED test booking. Type YES to run it: ")
        if answer.strip() == "YES":
            passed = booking_test(client) and passed
        else:
            print("Booking test skipped.")

    print("\nRESULT:", "ALL CHECKS PASSED" if passed else "SOME CHECKS FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())