✈️ SkyBook — Flight Reservation System

SkyBook is a web-based flight reservation application that allows users to search for available flights, compare flight options, book tickets, simulate payments, retrieve booking details, and cancel reservations. The application uses *Flask* for backend development and *MongoDB Atlas* for database management.

Project Overview

SkyBook provides a simple and user-friendly flight booking experience. Users can select departure and destination cities, choose a travel date, view available flights, sort results, book seats, and manage their reservations through a web interface.

This project demonstrates full-stack web development concepts, REST-style API endpoints, database integration, booking management, and transaction-based seat availability updates.

*Note:* This is a demonstration project. Payments are simulated, and tickets are not valid for actual air travel.

Technologies Used

- *Frontend:* HTML5, CSS3, JavaScript
- *Backend:* Python, Flask
- *Database:* MongoDB Atlas
- *Database Driver:* PyMongo
- *Version Control:* Git and GitHub
- *Deployment:* Render

Features

- *Flight Search:* Search flights by departure city, destination, and travel date.
- *Dynamic Dropdowns:* Update available travel options based on the selected route.
- *Flight Sorting:* Sort available flights by price or departure time.
- *Seat Booking:* Reserve seats and update seat availability.
- *Booking Reference:* Generate a unique booking reference for reservations.
- *Demo Payment:* Simulate payment processing without handling real money.
- *My Bookings:* Retrieve booking details using a booking reference and email address.
- *Ticket Details:* View and print a booking confirmation.
- *Cancellation:* Cancel eligible reservations and restore seats.
- *Database Integration:* Store and retrieve flight and booking information using MongoDB Atlas.
- *Deployment:* Access the application through its hosted Render URL.

Live Demo

[Open SkyBook](https://skybook-t264.onrender.com)

*Note: The application may take a little time to start if the hosting service has been idle.*

Project Structure

Air-Reservation-System/
├── backend/
│   ├── app.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── script.js
├── .gitignore
├── README.md
├── requirements.txt
└── Output in MongoDB.json


Installation and Setup

Prerequisites

- Python 3
- pip
- A MongoDB Atlas account and database
- Git

1. Clone the repository

git clone https://github.com/Kirthanaramesh04/Air-Reservation-System.git
cd Air-Reservation-System

2. Create a virtual environment

python -m venv .venv

Activate it on Windows PowerShell:

powershell:    .\.venv\Scripts\Activate.ps1

If PowerShell blocks activation, you can use the virtual environment's Python executable directly.

3. Install dependencies

pip install -r requirements.txt


4. Configure MongoDB

Create a `.env` file in the project root directory and add your MongoDB Atlas connection string:

env
MONGODB_URI=your_mongodb_connection_string

Replace the placeholder with your own connection string. Keep your actual credentials private and **never commit your `.env` file to GitHub**.

5. Run the application

**python backend/app.py**


Open the following URL in your browser:

**http://127.0.0.1:5000**


Database Design

SkyBook uses MongoDB Atlas with two main collections.

1. Flights collection

Stores flight information, including:

- Flight number and airline
- Departure and destination cities
- Travel date
- Departure and arrival times
- Ticket price
- Available seats

2. Bookings collection

Stores reservation information, including:

- Booking reference
- Passenger details
- Associated flight
- Number of seats booked
- Booking status
- Payment status

Booking and cancellation operations update seat availability to help maintain consistent reservation records.

Testing and Validation

The following application workflows have been tested during development:

- Dynamic departure and destination selection
- Flight search by route and date
- Sorting flights by price and departure time
- Booking a flight and generating a booking reference
- Simulated payment processing
- Retrieving booking details
- Cancelling a booking and restoring seat availability
- Preventing repeated cancellation of an already-cancelled booking

Security and Limitations

- Payments are simulated; no real payment gateway is integrated.
- Flight information is sample data and does not represent live airline inventory.
- Authentication, production-grade authorization, and additional security hardening may be required before real-world deployment.
- MongoDB connection strings and other secrets must be stored in environment variables, not committed to the repository.

Future Enhancements

- Integrate a real payment gateway.
- Add user registration, login, and authentication.
- Develop an administrator dashboard for flight management.
- Integrate a live flight information API.
- Add automated unit and integration tests.
- Improve booking history and cancellation management.

Author

**Kirthana R.**

- GitHub: [Kirthanaramesh04](https://github.com/Kirthanaramesh04)

License

No license has been specified yet. A suitable open-source license can be added if the project is intended for reuse or redistribution.