
document.addEventListener("DOMContentLoaded", function () {
    // ------------------------------------
    // 1. GET HTML ELEMENTS
    // ------------------------------------

    const flightForm = document.getElementById("flightForm");
    const message = document.getElementById("message");
    const flightCount = document.getElementById("flightCount");
    const sortDropdown = document.getElementById("sortFlights");

    const fromInput = document.getElementById("from");
    const toInput = document.getElementById("to");
    const dateInput = document.getElementById("date");
    
    // ------------------------------------
    // DYNAMIC FLIGHT SEARCH DROPDOWNS
    // ------------------------------------

    function resetDropdown(dropdown, placeholder) {
        dropdown.replaceChildren();

        const option = document.createElement("option");
        option.value = "";
        option.textContent = placeholder;

        dropdown.appendChild(option);
        dropdown.value = "";
    }

    function populateDropdown(dropdown, values, placeholder) {
        resetDropdown(dropdown, placeholder);

        values.forEach(function (value) {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            dropdown.appendChild(option);
        });

        dropdown.disabled = values.length === 0;
    }

    async function fetchFlightOptions(from = "", to = "") {
        const params = new URLSearchParams();

        if (from) {
            params.set("from", from);
        }

        if (to) {
            params.set("to", to);
        }

        const query = params.toString();
        const url = query
            ? `/flight-options?${query}`
            : "/flight-options";

        const response = await fetch(url);
        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            throw new Error(
                result.message || "Unable to load flight options."
            );
        }

        return result;
    }

    // Load departure cities when the page opens.
    async function loadDepartureCities() {
        fromInput.disabled = true;
        toInput.disabled = true;
        dateInput.disabled = true;

        resetDropdown(fromInput, "Loading departure cities...");
        resetDropdown(toInput, "Select departure city first");
        resetDropdown(dateInput, "Select route first");

        try {
            const result = await fetchFlightOptions();

            populateDropdown(
                fromInput,
                result.departure_cities || [],
                "Select departure city"
            );

            showMessage(message, "");

        } catch (error) {
            console.error("Departure city loading error:", error);

            resetDropdown(fromInput, "Could not load cities");
            fromInput.disabled = true;

            showMessage(
                message,
                "Unable to load flight options. Please refresh the page."
            );
        }
    }

    // When a departure city is selected, load its destinations.
    fromInput.addEventListener("change", async function () {
        const from = fromInput.value;

        resetDropdown(toInput, "Loading destinations...");
        toInput.disabled = true;

        resetDropdown(dateInput, "Select route first");
        dateInput.disabled = true;

        availableFlights = [];
        selectedFlight = null;
        resultsContainer.replaceChildren();
        flightCount.textContent =
            "Choose a route and date to search for flights.";
        bookingFormSection.hidden = true;
        showMessage(message, "");

        if (!from) {
            resetDropdown(toInput, "Select departure city first");
            return;
        }

        try {
            const result = await fetchFlightOptions(from);

            populateDropdown(
                toInput,
                result.destination_cities || [],
                "Select destination city"
            );

        } catch (error) {
            console.error("Destination loading error:", error);

            resetDropdown(toInput, "Could not load destinations");
            toInput.disabled = true;

            showMessage(
                message,
                "Unable to load destinations. Please try again."
            );
        }
    });

    // When a destination is selected, load dates for that route.
    toInput.addEventListener("change", async function () {
        const from = fromInput.value;
        const to = toInput.value;

        resetDropdown(dateInput, "Loading travel dates...");
        dateInput.disabled = true;

        availableFlights = [];
        selectedFlight = null;
        resultsContainer.replaceChildren();
        flightCount.textContent =
            "Choose a travel date to search for flights.";
        bookingFormSection.hidden = true;
        showMessage(message, "");

        if (!from || !to) {
            resetDropdown(dateInput, "Select route first");
            return;
        }

        try {
            const result = await fetchFlightOptions(from, to);

            populateDropdown(
                dateInput,
                result.travel_dates || [],
                "Select travel date"
            );

        } catch (error) {
            console.error("Travel date loading error:", error);

            resetDropdown(dateInput, "Could not load dates");
            dateInput.disabled = true;

            showMessage(
                message,
                "Unable to load travel dates. Please try again."
            );
        }
    });

    // Start loading the dropdowns.
    loadDepartureCities();


    const lookupBookingForm =
        document.getElementById("lookupBookingForm");
    const lookupMessage =
        document.getElementById("lookupMessage");
    const bookingDetails =
        document.getElementById("bookingDetails");

    let resultsContainer = document.getElementById("flightResults");

    if (!resultsContainer && flightForm) {
        resultsContainer = document.createElement("div");
        resultsContainer.id = "flightResults";
        flightForm.insertAdjacentElement("afterend", resultsContainer);
    }

    let bookingFormSection =
        document.getElementById("bookingFormSection");

    if (!bookingFormSection) {
        bookingFormSection = document.createElement("section");
        bookingFormSection.id = "bookingFormSection";
        bookingFormSection.hidden = true;

        if (resultsContainer) {
            resultsContainer.insertAdjacentElement(
                "afterend",
                bookingFormSection
            );
        } else if (flightForm) {
            flightForm.insertAdjacentElement(
                "afterend",
                bookingFormSection
            );
        }
    }

    // ------------------------------------
    // 2. STORE SEARCH RESULTS
    // ------------------------------------

    let availableFlights = [];
    let selectedFlight = null;

    // ------------------------------------
    // 3. HELPER FUNCTIONS
    // ------------------------------------

    function formatPrice(amount) {
        const number = Number(amount);
        return (Number.isFinite(number) ? number : 0)
            .toLocaleString("en-IN", {
                maximumFractionDigits: 2
            });
    }

    function createElement(tag, text, className) {
        const element = document.createElement(tag);

        if (text !== undefined && text !== null) {
            element.textContent = text;
        }

        if (className) {
            element.className = className;
        }

        return element;
    }

    function addDetail(parent, label, value) {
        const paragraph = document.createElement("p");
        paragraph.textContent = `${label}: ${value ?? "N/A"}`;
        parent.appendChild(paragraph);
    }

    function showMessage(element, text) {
        if (element) {
            element.textContent = text;
        }
    }

    // ------------------------------------
    // 4. PRINTABLE DEMO TICKET STYLES
    // ------------------------------------

    function addTicketPrintStyles() {
        if (document.getElementById("skybookPrintStyles")) {
            return;
        }

        const style = document.createElement("style");
        style.id = "skybookPrintStyles";

        style.textContent = `
            .skybook-ticket {
                max-width: 760px;
                margin: 20px auto;
                padding: 24px;
                border: 2px solid #153e75;
                border-radius: 14px;
                background: #ffffff;
                color: #172033;
                font-family: Arial, sans-serif;
                box-sizing: border-box;
            }

            .skybook-ticket-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
                padding-bottom: 16px;
                border-bottom: 2px dashed #cbd5e1;
            }

            .skybook-ticket-header h2 {
                margin: 0 0 6px;
                color: #153e75;
            }

            .skybook-ticket-label {
                margin: 0;
                color: #475569;
                font-size: 13px;
            }

            .skybook-ticket-status {
                display: inline-block;
                padding: 6px 10px;
                border-radius: 20px;
                background: #dcfce7;
                color: #166534;
                font-weight: bold;
                font-size: 12px;
            }

            .skybook-ticket-route {
                display: grid;
                grid-template-columns: 1fr auto 1fr;
                align-items: center;
                gap: 14px;
                padding: 22px 0;
                text-align: center;
            }

            .skybook-ticket-route strong {
                display: block;
                font-size: 20px;
                overflow-wrap: anywhere;
            }

            .skybook-ticket-route small {
                color: #64748b;
            }

            .skybook-ticket-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
                padding: 16px 0;
                border-top: 1px solid #e2e8f0;
            }

            .skybook-ticket-field span {
                display: block;
                margin-bottom: 4px;
                color: #64748b;
                font-size: 12px;
            }

            .skybook-ticket-field strong {
                overflow-wrap: anywhere;
            }

            .skybook-ticket-total {
                display: flex;
                justify-content: space-between;
                gap: 16px;
                padding: 16px;
                border-radius: 10px;
                background: #eff6ff;
                color: #153e75;
                font-size: 18px;
                font-weight: bold;
            }

            .skybook-ticket-note {
                margin-top: 16px;
                color: #64748b;
                font-size: 12px;
                line-height: 1.5;
            }

            .skybook-print-button {
                margin-top: 16px;
            }

            @media (max-width: 520px) {
                .skybook-ticket {
                    padding: 16px;
                }

                .skybook-ticket-route strong {
                    font-size: 16px;
                }

                .skybook-ticket-grid {
                    grid-template-columns: 1fr;
                }
            }

            @media print {
                body.skybook-printing-ticket * {
                    visibility: hidden !important;
                }

                body.skybook-printing-ticket .skybook-ticket,
                body.skybook-printing-ticket .skybook-ticket * {
                    visibility: visible !important;
                }

                body.skybook-printing-ticket .skybook-ticket {
                    position: absolute !important;
                    left: 0 !important;
                    top: 0 !important;
                    width: 100% !important;
                    max-width: none !important;
                    margin: 0 !important;
                    border: 1px solid #333 !important;
                    box-shadow: none !important;
                }

                body.skybook-printing-ticket .skybook-print-button {
                    display: none !important;
                }

                @page {
                    size: auto;
                    margin: 12mm;
                }
            }
        `;

        document.head.appendChild(style);
    }

    function ticketField(label, value) {
        const field = createElement(
            "div",
            null,
            "skybook-ticket-field"
        );

        field.appendChild(createElement("span", label));
        field.appendChild(
            createElement(
                "strong",
                String(
                    value === undefined ||
                    value === null ||
                    value === ""
                        ? "N/A"
                        : value
                )
            )
        );

        return field;
    }

    // ------------------------------------
    // 5. CREATE PRINTABLE TICKET
    // ------------------------------------

    function createPrintableTicket(booking) {
        addTicketPrintStyles();

        const ticket = createElement(
            "section",
            null,
            "skybook-ticket"
        );

        ticket.setAttribute("aria-label", "SkyBook demo ticket");

        const header = createElement(
            "div",
            null,
            "skybook-ticket-header"
        );

        const brandBlock = document.createElement("div");
        brandBlock.appendChild(createElement("h2", "SkyBook"));
        brandBlock.appendChild(
            createElement(
                "p",
                "Flight Booking Confirmation",
                "skybook-ticket-label"
            )
        );

        const status = createElement(
            "span",
            booking.booking_status || "CONFIRMED",
            "skybook-ticket-status"
        );

        header.append(brandBlock, status);

        const route = createElement(
            "div",
            null,
            "skybook-ticket-route"
        );

        const sourceBlock = document.createElement("div");
        sourceBlock.appendChild(
            createElement("strong", booking.source || "N/A")
        );
        sourceBlock.appendChild(createElement("small", "FROM"));

        const routeMiddle = createElement(
            "div",
            "✈",
            "skybook-ticket-label"
        );

        const destinationBlock = document.createElement("div");
        destinationBlock.appendChild(
            createElement("strong", booking.destination || "N/A")
        );
        destinationBlock.appendChild(createElement("small", "TO"));

        route.append(sourceBlock, routeMiddle, destinationBlock);

        const grid = createElement(
            "div",
            null,
            "skybook-ticket-grid"
        );

        const fields = [
            ["Booking Reference", booking.booking_reference],
            ["Passenger Name", booking.passenger_name],
            ["Airline", booking.airline],
            ["Flight Number", booking.flight_number],
            ["Travel Date", booking.travel_date],
            ["Departure Time", booking.departure_time],
            ["Arrival Time", booking.arrival_time],
            ["Number of Passengers", booking.seats],
            [
                "Price per Passenger",
                `₹${formatPrice(booking.price_per_seat)}`
            ],
            ["Payment Status", booking.payment_status || "NOT_PAID"]
        ];

        fields.forEach(([label, value]) => {
            grid.appendChild(ticketField(label, value));
        });

        const total = createElement(
            "div",
            null,
            "skybook-ticket-total"
        );

        total.appendChild(createElement("span", "Total Price"));
        total.appendChild(
            createElement("span", `₹${formatPrice(booking.total_price)}`)
        );

        const noteText =
            booking.payment_status === "DEMO_PAID"
                ? "DEMO TICKET ONLY — Demo payment was simulated. No real money was charged. This is not a real airline ticket."
                : "DEMO TICKET ONLY — This is a portfolio demonstration. It is not a real airline ticket and no payment has been collected.";

        const note = createElement(
            "p",
            noteText,
            "skybook-ticket-note"
        );

        const printButton = createElement(
            "button",
            "Print Ticket",
            "skybook-print-button"
        );

        printButton.type = "button";

        printButton.addEventListener("click", function () {
            document.body.classList.add("skybook-printing-ticket");

            const cleanup = function () {
                document.body.classList.remove(
                    "skybook-printing-ticket"
                );
                window.removeEventListener("afterprint", cleanup);
            };

            window.addEventListener("afterprint", cleanup);
            window.print();
            window.setTimeout(cleanup, 1500);
        });

        ticket.append(
            header,
            route,
            grid,
            total,
            note,
            printButton
        );

        return ticket;
    }

    // ------------------------------------
    // 6. DEMO PAYMENT INTERFACE
    // ------------------------------------

    function createDemoPaymentSection(booking, passengerEmail, onPaymentComplete) {
        const section = createElement(
            "section",
            null,
            "flight-card"
        );

        section.appendChild(createElement("h3", "Demo Payment"));

        addDetail(
            section,
            "Booking Reference",
            booking.booking_reference
        );

        addDetail(
            section,
            "Amount",
            `₹${formatPrice(booking.total_price)}`
        );

        const status = createElement(
            "p",
            `Payment Status: ${booking.payment_status || "NOT_PAID"}`
        );

        section.appendChild(status);

        const paymentMessage = createElement("p", "");
        paymentMessage.setAttribute("role", "status");
        paymentMessage.setAttribute("aria-live", "polite");
        section.appendChild(paymentMessage);

        if (booking.payment_status === "DEMO_PAID") {
            showMessage(
                paymentMessage,
                "Demo payment has already been completed. No real money was charged."
            );

            return section;
        }

        if (
            booking.booking_status !== "CONFIRMED" ||
            booking.payment_status !== "NOT_PAID"
        ) {
            showMessage(
                paymentMessage,
                "This booking is not eligible for demo payment."
            );

            return section;
        }

        section.appendChild(
            createElement(
                "p",
                "This is a payment simulation only. No real money will be charged."
            )
        );

        const payButton = createElement(
            "button",
            "Pay Now (Demo)"
        );

        payButton.type = "button";

        payButton.addEventListener("click", async function () {
            payButton.disabled = true;
            payButton.textContent = "Processing demo payment...";

            showMessage(
                paymentMessage,
                "Updating demo payment status..."
            );

            try {
                const response = await fetch("/demo-payment", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        booking_reference: booking.booking_reference,
                        passenger_email: passengerEmail
                    })
                });

                const result = await response.json();

                if (
                    !response.ok ||
                    result.status !== "success"
                ) {
                    showMessage(
                        paymentMessage,
                        result.message ||
                            "Demo payment could not be completed."
                    );
                    return;
                }

                booking.payment_status = result.payment_status;

                status.textContent =
                    `Payment Status: ${result.payment_status}`;

                showMessage(
                    paymentMessage,
                    "Demo payment completed successfully. No real money was charged."
                );

                payButton.remove();

                if (typeof onPaymentComplete === "function") {
                    onPaymentComplete(booking);
                }

            } catch (error) {
                console.error("Demo payment error:", error);

                showMessage(
                    paymentMessage,
                    "Unable to connect to the server. Check My Bookings before retrying."
                );

            } finally {
                if (payButton.isConnected) {
                    payButton.disabled = false;
                    payButton.textContent = "Pay Now (Demo)";
                }
            }
        });

        section.appendChild(payButton);

        return section;
    }

    // ------------------------------------
    // 7. SORT FLIGHTS
    // ------------------------------------

    function getSortedFlights() {
        const flights = [...availableFlights];

        const sortValue = sortDropdown
            ? sortDropdown.value
            : "recommended";

        switch (sortValue) {
            case "price-asc":
                flights.sort(
                    (a, b) => Number(a.price) - Number(b.price)
                );
                break;

            case "price-desc":
                flights.sort(
                    (a, b) => Number(b.price) - Number(a.price)
                );
                break;

            case "departure-asc":
                flights.sort((a, b) =>
                    String(a.departure_time).localeCompare(
                        String(b.departure_time)
                    )
                );
                break;

            case "departure-desc":
                flights.sort((a, b) =>
                    String(b.departure_time).localeCompare(
                        String(a.departure_time)
                    )
                );
                break;

            case "recommended":
            default:
                // Keep the order returned by the backend.
                break;
        }

        return flights;
    }

    // ------------------------------------
    // 8. DISPLAY FLIGHT RESULTS
    // ------------------------------------

    function displayFlights() {
        if (!resultsContainer) {
            return;
        }

        resultsContainer.replaceChildren();

        if (availableFlights.length === 0) {
            if (flightCount) {
                flightCount.textContent =
                    "Search for flights to see available options.";
            }

            return;
        }

        if (flightCount) {
            flightCount.textContent =
                `${availableFlights.length} flight(s) found`;
        }

        getSortedFlights().forEach(function (flight) {
            const card = createElement("div", null, "flight-card");

            const heading = createElement(
                "h3",
                `${flight.airline} - ${flight.flight_number}`
            );

            const route = createElement(
                "p",
                `${flight.source} → ${flight.destination}`
            );

            const times = createElement(
                "p",
                `Departure: ${flight.departure_time} | Arrival: ${flight.arrival_time}`
            );

            const travelDate = createElement(
                "p",
                `Travel date: ${flight.travel_date}`
            );

            const price = createElement(
                "p",
                `Ticket price: ₹${formatPrice(flight.price)}`
            );

            const seats = createElement(
                "p",
                `Available seats: ${flight.available_seats}`
            );

            const bookButton = createElement("button", "Book Flight");
            bookButton.type = "button";

            bookButton.addEventListener("click", function () {
                openBookingForm(flight);
            });

            card.append(
                heading,
                route,
                times,
                travelDate,
                price,
                seats,
                bookButton
            );

            resultsContainer.appendChild(card);
        });
    }

    if (sortDropdown) {
        sortDropdown.addEventListener("change", displayFlights);
    }

    // ------------------------------------
    // 9. SEARCH FLIGHTS
    // ------------------------------------

    if (flightForm) {
        flightForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const from = fromInput.value.trim();
            const to = toInput.value.trim();
            const date = dateInput.value;

            availableFlights = [];
            selectedFlight = null;

            if (resultsContainer) {
                resultsContainer.replaceChildren();
            }

            bookingFormSection.hidden = true;

            if (!from || !to || !date) {
                showMessage(
                    message,
                    "Please fill in all flight search fields."
                );
                return;
            }

            if (from.toLowerCase() === to.toLowerCase()) {
                showMessage(
                    message,
                    "Departure and destination must be different."
                );
                return;
            }

            showMessage(message, "Searching for flights...");

            if (flightCount) {
                flightCount.textContent = "Searching...";
            }

            try {
                const response = await fetch("/search-flights", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        from: from,
                        to: to,
                        date: date
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    showMessage(
                        message,
                        result.message || "Unable to search for flights."
                    );

                    if (flightCount) {
                        flightCount.textContent =
                            "No flight results available.";
                    }

                    return;
                }

                availableFlights = Array.isArray(result.flights)
                    ? result.flights
                    : [];

                showMessage(
                    message,
                    result.message || "Search completed."
                );

                displayFlights();

                if (availableFlights.length === 0 && flightCount) {
                    flightCount.textContent =
                        "No flights found. Try another route or date.";
                }

            } catch (error) {
                console.error("Flight search error:", error);

                showMessage(
                    message,
                    "Unable to connect to the server. Please try again."
                );

                if (flightCount) {
                    flightCount.textContent =
                        "Could not load flight results.";
                }
            }
        });
    }

    // ------------------------------------
    // 10. OPEN THE BOOKING FORM
    // ------------------------------------

    function openBookingForm(flight) {
        selectedFlight = flight;
        bookingFormSection.replaceChildren();

        const heading = createElement("h3", "Complete Your Booking");

        const flightSummary = createElement(
            "p",
            `${flight.airline} | ${flight.flight_number} | ` +
            `${flight.source} → ${flight.destination} | ` +
            `${flight.departure_time}–${flight.arrival_time}`
        );

        const form = document.createElement("form");
        form.id = "bookingForm";

        const passengerName = document.createElement("input");
        passengerName.id = "passengerName";
        passengerName.name = "passenger_name";
        passengerName.type = "text";
        passengerName.placeholder = "Enter passenger name";
        passengerName.maxLength = 100;
        passengerName.required = true;

        const passengerEmail = document.createElement("input");
        passengerEmail.id = "passengerEmail";
        passengerEmail.name = "passenger_email";
        passengerEmail.type = "email";
        passengerEmail.placeholder = "Enter email address";
        passengerEmail.required = true;

        const passengerPhone = document.createElement("input");
        passengerPhone.id = "passengerPhone";
        passengerPhone.name = "passenger_phone";
        passengerPhone.type = "tel";
        passengerPhone.placeholder = "Enter phone number";
        passengerPhone.required = true;

        const numberOfSeats = document.createElement("input");
        numberOfSeats.id = "numberOfSeats";
        numberOfSeats.name = "seats";
        numberOfSeats.type = "number";
        numberOfSeats.min = "1";
        numberOfSeats.max = String(
            Math.min(6, Number(flight.available_seats))
        );
        numberOfSeats.value = "1";
        numberOfSeats.required = true;

        const nameLabel = createElement("label", "Passenger Name:");
        nameLabel.htmlFor = passengerName.id;

        const emailLabel = createElement("label", "Email:");
        emailLabel.htmlFor = passengerEmail.id;

        const phoneLabel = createElement("label", "Phone Number:");
        phoneLabel.htmlFor = passengerPhone.id;

        const seatsLabel = createElement("label", "Number of Seats:");
        seatsLabel.htmlFor = numberOfSeats.id;

        const pricePerPassenger = createElement(
            "p",
            `Price per passenger: ₹${formatPrice(flight.price)}`
        );

        const totalAmount = createElement(
            "p",
            `Total for 1 passenger: ₹${formatPrice(flight.price)}`
        );

        const bookingMessage = createElement("p", "");
        bookingMessage.id = "bookingMessage";
        bookingMessage.setAttribute("role", "status");
        bookingMessage.setAttribute("aria-live", "polite");

        const confirmButton = createElement("button", "Confirm Booking");
        confirmButton.type = "submit";

        const cancelButton = createElement("button", "Cancel");
        cancelButton.type = "button";

        cancelButton.addEventListener("click", function () {
            bookingFormSection.hidden = true;
            selectedFlight = null;
        });

        function updateTotal() {
            const maxSeats = Math.min(
                6,
                Number(flight.available_seats)
            );

            let seats = Number(numberOfSeats.value);

            if (!Number.isFinite(seats) || seats < 1) {
                seats = 1;
            }

            if (seats > maxSeats) {
                seats = maxSeats;
                numberOfSeats.value = String(maxSeats);
            }

            const total = Number(flight.price) * seats;
            const passengerWord =
                seats === 1 ? "passenger" : "passengers";

            totalAmount.textContent =
                `Total for ${seats} ${passengerWord}: ₹${formatPrice(total)}`;
        }

        numberOfSeats.addEventListener("input", updateTotal);
        numberOfSeats.addEventListener("change", updateTotal);

        form.append(
            nameLabel,
            passengerName,
            emailLabel,
            passengerEmail,
            phoneLabel,
            passengerPhone,
            seatsLabel,
            numberOfSeats,
            pricePerPassenger,
            totalAmount,
            bookingMessage,
            confirmButton,
            cancelButton
        );

        form.addEventListener("submit", submitBooking);

        bookingFormSection.append(
            heading,
            flightSummary,
            form
        );

        bookingFormSection.hidden = false;

        bookingFormSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }

    // ------------------------------------
    // 11. SUBMIT A BOOKING
    // ------------------------------------

    async function submitBooking(event) {
        event.preventDefault();

        if (!selectedFlight) {
            return;
        }

        const form = event.currentTarget;

        const passengerName =
            document.getElementById("passengerName").value.trim();

        const passengerEmail =
            document.getElementById("passengerEmail").value.trim();

        const passengerPhone =
            document.getElementById("passengerPhone").value.trim();

        const seats = Number(
            document.getElementById("numberOfSeats").value
        );

        const bookingMessage =
            document.getElementById("bookingMessage");

        const confirmButton =
            form.querySelector('button[type="submit"]');

        if (!passengerName || !passengerEmail || !passengerPhone) {
            showMessage(
                bookingMessage,
                "Please fill in all passenger details."
            );
            return;
        }

        if (
            !Number.isInteger(seats) ||
            seats < 1 ||
            seats > 6 ||
            seats > Number(selectedFlight.available_seats)
        ) {
            showMessage(
                bookingMessage,
                "Please select a valid number of available seats (1–6)."
            );
            return;
        }

        confirmButton.disabled = true;
        confirmButton.textContent = "Processing...";

        try {
            const response = await fetch("/book-flight", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    flight_number: selectedFlight.flight_number,
                    passenger_name: passengerName,
                    passenger_email: passengerEmail,
                    passenger_phone: passengerPhone,
                    seats: seats
                })
            });

            const result = await response.json();

            if (!response.ok || result.status !== "success") {
                showMessage(
                    bookingMessage,
                    result.message || "Booking could not be completed."
                );
                return;
            }

            const booking = result.booking;

            // Keep the email locally for the demo-payment request.
            // The backend should still verify the reference and email.
            booking.passenger_email = passengerEmail;

            bookingFormSection.replaceChildren();

            const heading = createElement("h3", "Booking Confirmed!");

            const confirmationText = createElement(
                "p",
                result.message || "Your demo booking was confirmed."
            );

            let ticket = createPrintableTicket(booking);

            const paymentSection = createDemoPaymentSection(
                booking,
                passengerEmail,
                function (updatedBooking) {
                    const updatedTicket =
                        createPrintableTicket(updatedBooking);

                    ticket.replaceWith(updatedTicket);
                    ticket = updatedTicket;
                }
            );

            bookingFormSection.append(
                heading,
                confirmationText,
                paymentSection,
                ticket
            );

            // Update the displayed seat count after successful booking.
            const flightInResults = availableFlights.find(
                item =>
                    item.flight_number === booking.flight_number
            );

            if (flightInResults) {
                flightInResults.available_seats = Math.max(
                    0,
                    Number(flightInResults.available_seats) -
                        Number(booking.seats)
                );
            }

            displayFlights();

        } catch (error) {
            console.error("Booking error:", error);

            showMessage(
                bookingMessage,
                "Unable to confirm the booking. Check My Bookings before retrying."
            );

        } finally {
            if (confirmButton.isConnected) {
                confirmButton.disabled = false;
                confirmButton.textContent = "Confirm Booking";
            }
        }
    }

    // ------------------------------------
    // 12. LOOK UP AN EXISTING BOOKING
    // ------------------------------------

    if (lookupBookingForm) {
        lookupBookingForm.addEventListener(
            "submit",
            async function (event) {
                event.preventDefault();

                const referenceInput =
                    document.getElementById("bookingReference");

                const emailInput =
                    document.getElementById("lookupEmail");

                const bookingReference = referenceInput
                    ? referenceInput.value.trim()
                    : "";

                const passengerEmail = emailInput
                    ? emailInput.value.trim()
                    : "";

                if (!bookingReference || !passengerEmail) {
                    showMessage(
                        lookupMessage,
                        "Please enter your booking reference and email."
                    );
                    return;
                }

                if (bookingDetails) {
                    bookingDetails.replaceChildren();
                }

                showMessage(
                    lookupMessage,
                    "Looking up your booking..."
                );

                try {
                    const response = await fetch("/my-booking", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            booking_reference: bookingReference,
                            passenger_email: passengerEmail
                        })
                    });

                    const result = await response.json();

                    if (
                        !response.ok ||
                        result.status !== "success"
                    ) {
                        showMessage(
                            lookupMessage,
                            result.message ||
                                "Unable to find your booking."
                        );
                        return;
                    }

                    const booking = result.booking;

                    // Use the email supplied for this lookup when
                    // requesting a demo payment.
                    booking.passenger_email = passengerEmail;

                    showMessage(
                        lookupMessage,
                        result.message || "Booking found."
                    );

                    const card = createElement(
                        "div",
                        null,
                        "flight-card"
                    );

                    card.appendChild(
                        createElement("h3", "Your Booking Details")
                    );

                    addDetail(
                        card,
                        "Booking Reference",
                        booking.booking_reference
                    );

                    addDetail(
                        card,
                        "Booking Status",
                        booking.booking_status
                    );

                    addDetail(
                        card,
                        "Passenger",
                        booking.passenger_name
                    );

                    addDetail(
                        card,
                        "Flight",
                        `${booking.airline} - ${booking.flight_number}`
                    );

                    addDetail(
                        card,
                        "Route",
                        `${booking.source} → ${booking.destination}`
                    );

                    addDetail(
                        card,
                        "Travel Date",
                        booking.travel_date
                    );

                    addDetail(
                        card,
                        "Departure / Arrival",
                        `${booking.departure_time} / ${booking.arrival_time}`
                    );

                    addDetail(card, "Seats", booking.seats);

                    addDetail(
                        card,
                        "Price per Seat",
                        `₹${formatPrice(booking.price_per_seat)}`
                    );

                    addDetail(
                        card,
                        "Total Price",
                        `₹${formatPrice(booking.total_price)}`
                    );

                    const paymentStatusParagraph = createElement(
                        "p",
                        `Payment Status: ${booking.payment_status || "NOT_PAID"}`
                    );

                    card.appendChild(paymentStatusParagraph);

                    let ticket = createPrintableTicket(booking);

                    const paymentSection = createDemoPaymentSection(
                        booking,
                        passengerEmail,
                        function (updatedBooking) {
                            // Refresh the visible payment status.
                            paymentStatusParagraph.textContent =
                                `Payment Status: ${updatedBooking.payment_status}`;

                            // Refresh the printable ticket too.
                            const updatedTicket =
                                createPrintableTicket(updatedBooking);

                            ticket.replaceWith(updatedTicket);
                            ticket = updatedTicket;
                        }
                    );

                    if (bookingDetails) {
                        bookingDetails.append(
                            card,
                            paymentSection,
                            ticket
                        );
                    }

                } catch (error) {
                    console.error(
                        "Booking lookup error:",
                        error
                    );

                    showMessage(
                        lookupMessage,
                        "Unable to connect to the server. Please try again."
                    );
                }
            }
        );
    }
});
