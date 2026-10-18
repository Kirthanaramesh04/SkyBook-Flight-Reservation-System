# SkyBook — Flight Reservation System

SkyBook is a web-based flight reservation application that allows users to search for available flights, compare flight options, book tickets, simulate payments, retrieve booking details, and cancel reservations. It uses **Flask** for backend development and **MongoDB Atlas** for database management.

## Project Overview

SkyBook provides a simple flight booking experience through a web interface. Users can select departure and destination cities, choose a travel date, view available flights, sort results, book seats, and manage their reservations.

This project demonstrates full-stack web development, API development, database integration, booking management, and transaction-based seat availability updates.

**Note:** This is a demonstration project. Payments are simulated, and tickets are not valid for actual air travel.

## Technologies Used

- **Frontend:** HTML5, CSS3, JavaScript
- **Backend:** Python, Flask
- **Database:** MongoDB Atlas
- **Database Driver:** PyMongo
- **Version Control:** Git and GitHub
- **Deployment:** Render

## Features

- **Flight Search:** Search flights by departure city, destination, and travel date.
- **Dynamic Dropdowns:** Update available travel options based on the selected route.
- **Flight Sorting:** Sort flights by price or departure time.
- **Seat Booking:** Reserve seats and update seat availability.
- **Booking Reference:** Generate a unique booking reference.
- **Demo Payment:** Simulate payment processing without real transactions.
- **My Bookings:** Retrieve booking details using a booking reference and email address.
- **Ticket Details:** View and print booking confirmations.
- **Cancellation:** Cancel reservations and restore seat availability.
- **Database Integration:** Store and retrieve flight and booking information using MongoDB Atlas.

## Live Demo

[Open SkyBook](https://skybook-t264.onrender.com/)

*Note: The application may take some time to start if the hosting service has been idle.*

## Project Structure

```text
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
```

## Installation and Setup

### Prerequisites

- Python 3
- pip
- MongoDB Atlas account
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Kirthanaramesh04/Air-Reservation-System.git
cd Air-Reservation-System
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the virtual environment's Python executable directly.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MongoDB

Create a `.env` file in the project root and add your MongoDB Atlas connection string:

```env
MONGODB_URI=your_mongodb_connection_string
```

Replace the placeholder with your own connection string. **Never commit your `.env` file or database credentials to GitHub.**

### 5. Run the Application

```bash
python backend/app.py
```

Open the application in your browser:

[http://127.0.0.1:5000](http://127.0.0.1:5000)

## Database Design

SkyBook uses MongoDB Atlas with two main collections.

### Flights Collection

Stores flight information, including:

- Flight number and airline
- Departure and destination cities
- Travel date
- Departure and arrival times
- Ticket price
- Available seats

### Bookings Collection

Stores reservation information, including:

- Booking reference
- Passenger details
- Associated flight
- Number of seats booked
- Booking status
- Payment status

Booking and cancellation operations update seat availability to maintain consistent reservation records.

## Testing and Validation

The following workflows have been tested during development:

- Dynamic departure and destination selection
- Flight search by route and date
- Sorting by price and departure time
- Flight booking and booking reference generation
- Simulated payment processing
- Retrieving booking details
- Cancellation and seat restoration
- Preventing repeated cancellation of an already-cancelled booking

## Security and Limitations

- Payments are simulated; no real payment gateway is integrated.
- Flight information is sample data and does not represent live airline inventory.
- Production use would require additional authentication, authorization, and security hardening.
- Database credentials must be stored securely in environment variables.

## Future Enhancements

- Integrate a real payment gateway.
- Add user registration and login.
- Develop an administrator dashboard for flight management.
- Integrate a live flight information API.
- Add automated unit and integration tests.
- Improve booking history and cancellation management.

## Author

**Kirthana R.**

- GitHub: [Kirthanaramesh04](https://github.com/Kirthanaramesh04)

## License

No license has been specified yet. A suitable open-source license can be added if the project is intended for reuse or redistribution.