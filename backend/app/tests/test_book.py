from app.database import get_reservation, reservations
from app.tools.book import book_reservation


def test_book_reservation_success():
    result = book_reservation(
        name="Mohammed",
        phone="9876543210",
        date="2026-08-17",
        time="19:00",
        party_size=4,
    )

    assert result["success"] is True
    assert result["confirmation_id"].startswith("R")

    confirmation_id = result["confirmation_id"]

    reservation = get_reservation(confirmation_id)

    assert reservation is not None
    assert reservation["name"] == "Mohammed"
    assert reservation["phone"] == "9876543210"
    assert reservation["date"] == "2026-08-17"
    assert reservation["time"] == "19:00"
    assert reservation["party_size"] == 4
    assert reservation["status"] == "confirmed"

    # Clean up after the test
    del reservations[confirmation_id]