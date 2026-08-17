from app.database import get_reservation
from app.tools.availability import check_availability


def modify_reservation(
    confirmation_id: str,
    date: str | None = None,
    time: str | None = None,
    party_size: int | None = None,
) -> dict:
    """
    Modify an existing reservation's date, time, or party size.
    """

    # Validate confirmation ID
    if not confirmation_id or not confirmation_id.strip():
        return {
            "success": False,
            "message": "Confirmation ID is required.",
        }

    # Make sure something is actually being changed
    if date is None and time is None and party_size is None:
        return {
            "success": False,
            "message": (
                "At least one field must be provided to modify "
                "the reservation."
            ),
        }

    # Validate party size
    if party_size is not None and party_size <= 0:
        return {
            "success": False,
            "message": "Party size must be greater than zero.",
        }

    # Find reservation
    reservation = get_reservation(confirmation_id)

    if reservation is None:
        return {
            "success": False,
            "message": "No reservation was found with that confirmation ID.",
        }

    # Cannot modify cancelled reservation
    if reservation["status"] == "cancelled":
        return {
            "success": False,
            "message": "A cancelled reservation cannot be modified.",
        }

    # Keep existing values for fields that were not changed
    new_date = date if date is not None else reservation["date"]
    new_time = time if time is not None else reservation["time"]
    new_party_size = (
        party_size
        if party_size is not None
        else reservation["party_size"]
    )

    # Check availability while excluding this reservation
    availability = check_availability(
        date=new_date,
        time=new_time,
        party_size=new_party_size,
        exclude_confirmation_id=confirmation_id,
    )

    if not availability["available"]:
        return {
            "success": False,
            "message": availability["message"],
        }

    # Update reservation
    reservation["date"] = new_date
    reservation["time"] = new_time
    reservation["party_size"] = new_party_size

    return {
        "success": True,
        "confirmation_id": confirmation_id,
        "reservation": reservation,
        "message": "Reservation modified successfully.",
    }