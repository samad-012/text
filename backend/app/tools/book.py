import random, string

from app.database import save_reservation
from app.tools.availability import check_availability


def book_reservation(
    name: str,
    phone: str,
    date: str,
    time: str,
    party_size: int,
) -> dict:
    """
    Book a restaurant reservation.

    Returns a confirmation ID when the reservation
    is successfully created.
    """

    # Basic input validation
    if not name.strip():
        return {
            "success": False,
            "message": "Name is required.",
        }

    if not phone.strip():
        return {
            "success": False,
            "message": "Phone number is required.",
        }

    # Check availability before creating the reservation
    availability = check_availability(
        date=date,
        time=time,
        party_size=party_size,
    )

    if not availability["available"]:
        return {
            "success": False,
            "message": availability["message"],
        }

    # Generate a unique confirmation ID
    conf_id = "R" + "".join(random.choices(string.digits, k=4))

    # Create reservation data
    reservation = {
        "confirmation_id": conf_id,
        "name": name.strip(),
        "phone": phone.strip(),
        "date": date,
        "time": time,
        "party_size": party_size,
        "status": "confirmed",
    }

    # Save reservation
    save_reservation(
        confirmation_id=conf_id,
        reservation=reservation,
    )

    return {
        "success": True,
        "confirmation_id": conf_id,
        "reservation": reservation,
        "message": "Reservation booked successfully.",
    }