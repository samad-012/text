from app.database import get_reservation


def cancel_reservation(confirmation_id: str) -> dict:
    """
    Cancel an existing reservation using its confirmation ID.
    """

    if not confirmation_id.strip():
        return {
            "success": False,
            "message": "Confirmation ID is required.",
        }

    reservation = get_reservation(confirmation_id)

    if reservation is None:
        return {
            "success": False,
            "message": "No reservation was found with that confirmation ID.",
        }

    if reservation["status"] == "cancelled":
        return {
            "success": False,
            "message": "This reservation has already been cancelled.",
        }

    reservation["status"] = "cancelled"

    return {
        "success": True,
        "confirmation_id": confirmation_id,
        "reservation": reservation,
        "message": "Reservation cancelled successfully.",
    }