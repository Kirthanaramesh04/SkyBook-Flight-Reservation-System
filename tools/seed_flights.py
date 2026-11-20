"""
SkyBook demo flight seeder
==========================

WHAT IT DOES
  1. Reads your EXISTING `skybook.flights` collection.
  2. Finds every distinct city used in `source` and `destination`.
  3. Builds every directed route between those cities: N x (N - 1) routes.
  4. Checks all 61 dates, 2026-11-01 to 2026-12-31, for every route.
  5. Inserts new flights ONLY for route/date combinations that have no
     available flight yet.

SAFETY RULES (built into this script)
  * It only INSERTS new flight documents. It never updates or deletes.
  * It never touches the `bookings` collection.
  * It runs as a DRY RUN unless you add --apply.
  * Combinations that already have a flight with seats left are skipped,
    so running it again inserts nothing new.
  * New flight numbers are checked against EVERY existing flight number.
  * The connection string is read from the same .env file as app.py.

USAGE (PowerShell, project root, virtual environment active)
    python tools\\seed_flights.py                 # dry run, writes nothing
    python tools\\seed_flights.py --apply         # insert the missing flights
    python tools\\seed_flights.py --verify-only   # just print the coverage report
    python tools\\seed_flights.py --add-cities "Kochi,Kolkata"   # also add cities
"""

import argparse
import os
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import permutations
from pathlib import Path

# ----------------------------------------------------------------------
# SETTINGS
# ----------------------------------------------------------------------

START_DATE = date(2026, 11, 1)
END_DATE = date(2026, 12, 31)

# Other spellings that mean the same city (merged into one city).
CITY_ALIASES = {"bangalore": "bengaluru", "cochin": "kochi"}

# Typical flying time in minutes, used ONLY when your database has no flight
# between a pair yet. If your data already has the pair, the script copies the
# real duration from it, so new flights match your old ones.
_KNOWN_DURATIONS = [
    ("Chennai", "Bengaluru", 70), ("Chennai", "Hyderabad", 80),
    ("Chennai", "Delhi", 170), ("Chennai", "Mumbai", 120),
    ("Chennai", "Kochi", 80), ("Chennai", "Coimbatore", 65),
    ("Chennai", "Kolkata", 140),
    ("Bengaluru", "Hyderabad", 80), ("Bengaluru", "Delhi", 170),
    ("Bengaluru", "Mumbai", 110), ("Bengaluru", "Kochi", 65),
    ("Bengaluru", "Coimbatore", 60), ("Bengaluru", "Kolkata", 150),
    ("Hyderabad", "Delhi", 140), ("Hyderabad", "Mumbai", 90),
    ("Hyderabad", "Kochi", 105), ("Hyderabad", "Coimbatore", 100),
    ("Hyderabad", "Kolkata", 125),
    ("Delhi", "Mumbai", 130), ("Delhi", "Kochi", 200),
    ("Delhi", "Coimbatore", 185), ("Delhi", "Kolkata", 135),
    ("Mumbai", "Kochi", 110), ("Mumbai", "Coimbatore", 105),
    ("Mumbai", "Kolkata", 165),
    ("Kochi", "Coimbatore", 50), ("Kochi", "Kolkata", 180),
    ("Coimbatore", "Kolkata", 170),
]
DEFAULT_DURATION = 120

# Fictional airlines only (name, two-letter code for flight numbers).
AIRLINES = [
    ("SkyWing Airways", "SW"), ("AeroNimbus", "AN"),
    ("BlueHorizon Air", "BH"), ("Zephyr Airlines", "ZP"),
    ("CloudJet", "CJ"), ("Meridian Air", "MA"),
]

# Departure windows (minutes after midnight): morning, afternoon, evening.
SLOTS = [(330, 570), (660, 900), (990, 1170)]
SLOT_PRICE_FACTOR = {0: 1.00, 1: 0.92, 2: 1.08}
LAST_ARRIVAL = 23 * 60 + 55          # arrivals stay on the same date

TIME_RE = re.compile(r"\d{2}:\d{2}")
SEED_BATCH_LABEL = "demo-seed-2026-11-to-12"


# ----------------------------------------------------------------------
# SMALL HELPERS
# ----------------------------------------------------------------------

def city_key(name):
    key = str(name).strip().casefold()
    return CITY_ALIASES.get(key, key)


KNOWN_DURATIONS = {
    frozenset((city_key(a), city_key(b))): minutes
    for a, b, minutes in _KNOWN_DURATIONS
}


def build_dates():
    days = (END_DATE - START_DATE).days + 1
    return [(START_DATE + timedelta(days=i)).isoformat() for i in range(days)]


def to_hhmm(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def to_minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def build_routes(city_keys):
    """All ordered pairs of two different cities: N x (N - 1)."""
    return list(permutations(city_keys, 2))


# ----------------------------------------------------------------------
# READ AND ANALYSE EXISTING DATA
# ----------------------------------------------------------------------

def analyse(existing, extra_cities=()):
    spellings = defaultdict(Counter)
    flight_numbers = Counter()
    covered = Counter()                 # (from, to, date) -> flights with seats
    seen_durations = defaultdict(list)
    bad_time_format = 0

    for doc in existing:
        number = doc.get("flight_number")
        if number:
            flight_numbers[str(number)] += 1

        source, destination = doc.get("source"), doc.get("destination")
        for name in (source, destination):
            if isinstance(name, str) and name.strip():
                spellings[city_key(name)][name.strip()] += 1

        departure, arrival = doc.get("departure_time"), doc.get("arrival_time")
        if not (isinstance(departure, str) and TIME_RE.fullmatch(departure)):
            bad_time_format += 1
        elif (
            isinstance(arrival, str) and TIME_RE.fullmatch(arrival)
            and isinstance(source, str) and isinstance(destination, str)
        ):
            length = to_minutes(arrival) - to_minutes(departure)
            if 20 <= length <= 600:
                pair = frozenset((city_key(source), city_key(destination)))
                seen_durations[pair].append(length)

        seats = doc.get("available_seats")
        travel_date = doc.get("travel_date")
        if (
            isinstance(seats, (int, float)) and not isinstance(seats, bool)
            and seats > 0
            and isinstance(source, str) and isinstance(destination, str)
            and isinstance(travel_date, str)
        ):
            covered[(city_key(source), city_key(destination),
                     travel_date)] += 1

    display = {key: names.most_common(1)[0][0]
               for key, names in spellings.items()}
    multi_spelling = {
        key: dict(names) for key, names in spellings.items() if len(names) > 1
    }

    for raw in extra_cities:
        raw = raw.strip()
        if raw and city_key(raw) not in display:
            display[city_key(raw)] = raw.title()

    return {
        "city_keys": sorted(display),
        "display": display,
        "multi_spelling": multi_spelling,
        "flight_numbers": flight_numbers,
        "covered": covered,
        "seen_durations": seen_durations,
        "bad_time_format": bad_time_format,
    }


def find_missing(city_keys, covered):
    missing = []
    for from_key, to_key in build_routes(city_keys):
        for travel_date in build_dates():
            if covered.get((from_key, to_key, travel_date), 0) == 0:
                missing.append((from_key, to_key, travel_date))
    return missing


def duration_for(pair, seen_durations, defaulted):
    if seen_durations.get(pair):
        return int(statistics.median(seen_durations[pair]))
    if pair in KNOWN_DURATIONS:
        return KNOWN_DURATIONS[pair]
    defaulted.add(pair)
    return DEFAULT_DURATION


# ----------------------------------------------------------------------
# CREATE NEW FLIGHTS
# ----------------------------------------------------------------------

def make_flights(missing, info, per_day, rng):
    display = info["display"]
    used_numbers = set(info["flight_numbers"])
    defaulted = set()
    duration_cache = {}
    new_flights = []

    for from_key, to_key, travel_date in missing:
        pair = frozenset((from_key, to_key))
        if pair not in duration_cache:
            duration_cache[pair] = duration_for(
                pair, info["seen_durations"], defaulted
            )
        duration = duration_cache[pair]

        feasible = [
            index for index, (start, _end) in enumerate(SLOTS)
            if start + duration <= LAST_ARRIVAL
        ] or [0]
        chosen = sorted(rng.sample(feasible, min(per_day, len(feasible))))

        for slot_index in chosen:
            start, end = SLOTS[slot_index]
            end = min(end, LAST_ARRIVAL - duration)
            departure = rng.randrange(start, max(start, end) + 1, 5)
            arrival = departure + duration

            airline, code = rng.choice(AIRLINES)
            number = f"{code}{rng.randint(1000, 9999)}"
            while number in used_numbers:
                number = f"{code}{rng.randint(1000, 9999)}"
            used_numbers.add(number)

            price = (1800 + duration * 20) * SLOT_PRICE_FACTOR[slot_index]
            price = int(round(price * rng.uniform(0.9, 1.2) / 50.0) * 50)

            new_flights.append({
                "flight_number": number,
                "airline": airline,
                "source": display[from_key],
                "destination": display[to_key],
                "travel_date": travel_date,
                "departure_time": to_hhmm(departure),
                "arrival_time": to_hhmm(min(arrival, LAST_ARRIVAL)),
                "available_seats": rng.randint(60, 180),
                "price": price,
                "seed_batch": SEED_BATCH_LABEL,
            })

    return new_flights, defaulted


def insert_in_batches(collection, flights, batch_size=1000):
    from pymongo.errors import BulkWriteError

    inserted = 0
    for i in range(0, len(flights), batch_size):
        batch = flights[i:i + batch_size]
        try:
            result = collection.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
        except BulkWriteError as error:
            inserted += error.details.get("nInserted", 0)
            print("Some inserts failed:",
                  error.details.get("writeErrors", [])[:3])
        print(f"  inserted {inserted} of {len(flights)}...")
    return inserted


# ----------------------------------------------------------------------
# REPORT
# ----------------------------------------------------------------------

def coverage_numbers(city_keys, covered):
    routes = build_routes(city_keys)
    dates = build_dates()
    combos_covered = sum(
        1 for a, b in routes for d in dates if covered.get((a, b, d), 0) > 0
    )
    routes_full = sum(
        1 for a, b in routes
        if all(covered.get((a, b, d), 0) > 0 for d in dates)
    )
    return {
        "routes": len(routes), "routes_full": routes_full,
        "dates": len(dates), "combos": len(routes) * len(dates),
        "combos_covered": combos_covered,
    }


def print_final_report(label, info, before_covered, inserted):
    keys = info["city_keys"]
    before = coverage_numbers(keys, before_covered)
    final = coverage_numbers(keys, info["covered"])
    still_missing = final["combos"] - final["combos_covered"]

    print(f"\n=== {label} ===")
    print(f"Distinct cities found:                 {len(keys)}")
    print("Cities:                                "
          + ", ".join(info["display"][k] for k in keys))
    print(f"Directed routes expected  N x (N-1):   {final['routes']}")
    print(f"Directed routes fully covered:         {final['routes_full']}")
    print(f"Travel dates expected:                 {final['dates']}")
    print(f"Route-date combinations expected:      {final['combos']}")
    print(f"Combinations covered BEFORE:           {before['combos_covered']}")
    print(f"Missing BEFORE insertion:              "
          f"{before['combos'] - before['combos_covered']}")
    print(f"Flight records inserted:               {inserted}")
    print(f"Combinations covered AFTER:            {final['combos_covered']}")
    print(f"Combinations still missing:            {still_missing}")

    if still_missing == 0:
        print(f"\nVERIFIED: all {len(keys)} cities connect to every other city "
              f"in both directions on every date from {START_DATE} to "
              f"{END_DATE}.")
        return True

    print("\nNOT COMPLETE. First few missing combinations:")
    for a, b, d in find_missing(keys, info["covered"])[:10]:
        print(f"  {info['display'][a]} -> {info['display'][b]} on {d}")
    return False


# ----------------------------------------------------------------------
# MAIN LOGIC (takes a collection, so it can be tested without MongoDB)
# ----------------------------------------------------------------------

PROJECTION = {
    "_id": 0, "flight_number": 1, "source": 1, "destination": 1,
    "travel_date": 1, "available_seats": 1,
    "departure_time": 1, "arrival_time": 1,
}


def run(collection, apply_changes, per_day, verify_only=False,
        extra_cities=()):
    existing = list(collection.find({}, PROJECTION))
    info = analyse(existing, extra_cities)

    print("=== WHAT IS ALREADY IN MONGODB ===")
    print(f"Existing flight records:   {len(existing)}")

    if not info["city_keys"]:
        print("No cities found in the flights collection. Nothing to do. "
              "(Use --add-cities to start from a list.)")
        return 1

    if len(info["city_keys"]) < 2:
        print("Only one city found. Use --add-cities to add more.")
        return 1

    if info["multi_spelling"]:
        print("Note: these cities are spelled in more than one way "
              "(treated as one city):", info["multi_spelling"])

    duplicates = [n for n, c in info["flight_numbers"].items() if c > 1]
    print(f"Duplicate flight numbers:  {len(duplicates)}")
    if duplicates:
        print("WARNING: booking finds flights by flight_number, so duplicates "
              "can confuse bookings. Examples:", duplicates[:5])

    if verify_only:
        ok = print_final_report("COVERAGE REPORT", info, info["covered"], 0)
        return 0 if ok else 2

    if info["bad_time_format"]:
        print(f"\nSTOP: {info['bad_time_format']} existing flights do not use "
              "24-hour HH:MM departure times (like 06:30). Nothing was "
              "written. Send me this output so I can match your format.")
        return 1

    missing = find_missing(info["city_keys"], info["covered"])
    routes = build_routes(info["city_keys"])
    print("\n=== PLAN ===")
    print(f"Cities: {len(info['city_keys'])}   Routes: {len(routes)}   "
          f"Dates: {len(build_dates())}")
    print(f"Combinations needed:          {len(routes) * len(build_dates())}")
    print(f"Missing (will be filled):     {len(missing)}")
    print(f"Flights per missing day:      {per_day}")
    print(f"Flight records to insert:     {len(missing) * per_day}")

    if not missing:
        print_final_report("COVERAGE REPORT", info, info["covered"], 0)
        print("\nNothing to insert. Everything is already covered.")
        return 0

    rng = random.Random(2026)
    new_flights, defaulted = make_flights(missing, info, per_day, rng)
    if defaulted:
        print(f"\nNote: {len(defaulted)} city pairs had no known flying time; "
              f"{DEFAULT_DURATION} minutes was used for them.")

    if not apply_changes:
        print("\nDRY RUN: nothing was written to MongoDB.")
        print("Example flight that would be inserted:\n ", new_flights[0])
        print("Run again with --apply to insert the flights.")
        return 0

    print("\nInserting flights...")
    inserted = insert_in_batches(collection, new_flights)

    after = analyse(list(collection.find({}, PROJECTION)), extra_cities)
    ok = print_final_report("FINAL REPORT (re-read from MongoDB)",
                            after, info["covered"], inserted)
    return 0 if ok else 2


def main():
    parser = argparse.ArgumentParser(description="Seed SkyBook demo flights.")
    parser.add_argument("--apply", action="store_true",
                        help="Really insert flights (default is a dry run).")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only print the coverage report.")
    parser.add_argument("--per-day", type=int, choices=(1, 2, 3), default=3,
                        help="Flights to create per missing route/date.")
    parser.add_argument("--add-cities", default="",
                        help='Extra cities, e.g. "Kochi,Kolkata".')
    args = parser.parse_args()
    extra = [c for c in args.add_cities.split(",") if c.strip()]

    from dotenv import load_dotenv
    from pymongo import MongoClient

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    uri = os.getenv("MONGODB_URI")
    if not uri:
        print("MONGODB_URI is missing from the .env file.")
        return 1

    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    try:
        client.admin.command("ping")
        mode = ("VERIFY" if args.verify_only
                else "APPLY" if args.apply else "DRY RUN")
        print(f"Connected to MongoDB Atlas (database: skybook). "
              f"Mode: {mode}\n")
        return run(client["skybook"]["flights"], args.apply, args.per_day,
                   args.verify_only, extra)
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())