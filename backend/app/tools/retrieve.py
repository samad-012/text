from app.database import (
    get_reservation,
    get_reservation_by_phone,
)


def retrieve_reservation_by_confirmation(
    confirmation_id: str,
) -> dict:
    """
    Retrieve a reservation using its confirmation ID.
    """

    if not confirmation_id or not confirmation_id.strip():
        return {
            "success": False,
            "message": "Confirmation ID is required.",
        }

    reservation = get_reservation(confirmation_id.strip())

    if reservation is None:
        return {
            "success": False,
            "message": "No reservation was found with that confirmation ID.",
        }

    return {
        "success": True,
        "reservation": reservation,
        "message": "Reservation found successfully.",
    }


def retrieve_reservation_by_phone(
    phone: str,
) -> dict:
    """
    Retrieve a reservation using the customer's phone number.
    """

    if not phone or not phone.strip():
        return {
            "success": False,
            "message": "Phone number is required.",
        }

    reservation = get_reservation_by_phone(phone.strip())

    if reservation is None:
        return {
            "success": False,
            "message": "No reservation was found for that phone number.",
        }

    return {
        "success": True,
        "reservation": reservation,
        "message": "Reservation found successfully.",
    }