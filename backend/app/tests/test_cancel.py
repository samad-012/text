from app.database import get_reservation
from app.tools.book import book_reservation
from app.tools.cancel import cancel_reservation


def test_cancel_reservation_success():
    booking = book_reservation(
        name="Mohammed",
        phone="9876543210",
        date="2026-08-20",
        time="19:00",
        party_size=4,
    )

    confirmation_id = booking["confirmation_id"]

    result = cancel_reservation(confirmation_id)

    assert result["success"] is True
    assert result["confirmation_id"] == confirmation_id
    assert result["reservation"]["status"] == "cancelled"

    reservation = get_reservation(confirmation_id)

    assert reservation["status"] == "cancelled"


def test_cancel_reservation_not_found():
    result = cancel_reservation(
        "BT-DOES-NOT-EXIST",
    )

    assert result["success"] is False


def test_cancel_reservation_already_cancelled():
    booking = book_reservation(
        name="Ahmed",
        phone="9123456789",
        date="2026-08-21",
        time="20:00",
        party_size=2,
    )

    confirmation_id = booking["confirmation_id"]

    first_cancel = cancel_reservation(confirmation_id)

    assert first_cancel["success"] is True

    second_cancel = cancel_reservation(confirmation_id)

    assert second_cancel["success"] is False
    assert "already been cancelled" in second_cancel["message"]


def test_cancel_reservation_empty_confirmation_id():
    result = cancel_reservation("")

    assert result["success"] is False