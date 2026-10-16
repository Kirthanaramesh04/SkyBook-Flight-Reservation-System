
const flightForm = document.getElementById("flightForm");
const message = document.getElementById("message");

flightForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const from = document.getElementById("from").value.trim();
    const to = document.getElementById("to").value.trim();
    const date = document.getElementById("date").value;

    if (!from || !to || !date) {
        message.textContent = "Please fill in all flight search fields.";
        return;
    }

    if (from.toLowerCase() === to.toLowerCase()) {
        message.textContent =
            "Departure and destination must be different.";
        return;
    }

    message.textContent = "Sending search request...";

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
        message.textContent = result.message;

    } catch (error) {
        message.textContent =
            "Unable to connect to the server. Please try again.";
    }
});
