from datetime import datetime

from app.database import reservations
from app.restaurant.info import RESTAURANT


def check_availability(
    date: str,
    time: str,
    party_size: int,
    exclude_confirmation_id: str | None = None,
) -> dict:
    """
    Check whether a table is available for the requested
    date, time, and party size.
    """

    # Validate party size
    if party_size < 1:
        return {
            "available": False,
            "message": "Party size must be at least 1.",
        }

    if party_size > RESTAURANT.max_party_size:
        return {
            "available": False,
            "message": (
                f"We can accommodate a maximum of "
                f"{RESTAURANT.max_party_size} people per reservation."
            ),
        }

    # Validate date and time format
    try:
        requested_datetime = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        return {
            "available": False,
            "message": "Invalid date or time format. Use YYYY-MM-DD and HH:MM.",
        }

    # Get the day of the week
    day = requested_datetime.strftime("%A").lower()

    # Check whether the restaurant is open that day
    if day not in RESTAURANT.opening_hours:
        return {
            "available": False,
            "message": f"We are closed on {day.capitalize()}.",
        }

    opening_time, closing_time = RESTAURANT.opening_hours[day]
    requested_time = requested_datetime.strftime("%H:%M")

    # Check restaurant hours
    if not opening_time <= requested_time <= closing_time:
        return {
            "available": False,
            "date": date,
            "time": time,
            "party_size": party_size,
            "message": (
                f"We are open from {opening_time} to {closing_time} "
                f"on {day.capitalize()}."
            ),
        }

    # Calculate how many people are already booked
    existing_party_size = sum(
    reservation["party_size"]
    for confirmation_id, reservation in reservations.items()
    if (
        confirmation_id != exclude_confirmation_id
        and reservation["date"] == date
        and reservation["time"] == time
        and reservation["status"] == "confirmed"
    )
)

    # Check against restaurant capacity
    if existing_party_size + party_size > RESTAURANT.max_capacity:
        return {
            "available": False,
            "date": date,
            "time": time,
            "party_size": party_size,
            "message": "Sorry, we don't have enough availability at that time.",
        }

    return {
        "available": True,
        "date": date,
        "time": time,
        "party_size": party_size,
        "message": "A table is available.",
    }