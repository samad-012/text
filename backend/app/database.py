from typing import Any


# In-memory reservation store.
# The key is the confirmation ID.
reservations: dict[str, dict[str, Any]] = {}


def get_reservation(confirmation_id: str) -> dict[str, Any] | None:
    """Return a reservation by confirmation ID."""
    return reservations.get(confirmation_id)


def save_reservation(
    confirmation_id: str,
    reservation: dict[str, Any],
) -> None:
    """Save a reservation in the in-memory store."""
    reservations[confirmation_id] = reservation


def delete_reservation(confirmation_id: str) -> bool:
    """Delete a reservation and return whether it existed."""
    if confirmation_id not in reservations:
        return False

    del reservations[confirmation_id]
    return True


def get_reservation_by_phone(phone: str):
    """
    Return the most recent confirmed reservation
    associated with the given phone number.
    """

    for reservation in reversed(list(reservations.values())):
        if (
            reservation["phone"] == phone
            and reservation["status"] == "confirmed"
        ):
            return reservation

    return None