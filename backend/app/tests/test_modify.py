from app.database import get_reservation
from app.tools.book import book_reservation
from app.tools.modify import modify_reservation


def test_modify_reservation_success():
    booking = book_reservation(
        name="Mohammed",
        phone="9876543210",
        date="2026-08-25",
        time="19:00",
        party_size=4,
    )

    confirmation_id = booking["confirmation_id"]

    result = modify_reservation(
        confirmation_id=confirmation_id,
        date="2026-08-25",
        time="20:00",
        party_size=5,
    )

    assert result["success"] is True
    assert result["reservation"]["date"] == "2026-08-25"
    assert result["reservation"]["time"] == "20:00"
    assert result["reservation"]["party_size"] == 5

    reservation = get_reservation(confirmation_id)

    assert reservation["date"] == "2026-08-25"
    assert reservation["time"] == "20:00"
    assert reservation["party_size"] == 5


def test_modify_reservation_not_found():
    result = modify_reservation(
        confirmation_id="BT-DOES-NOT-EXIST",
        date="2026-08-25",
        time="20:00",
        party_size=4,
    )

    assert result["success"] is False


def test_modify_cancelled_reservation():
    from app.tools.cancel import cancel_reservation

    booking = book_reservation(
        name="Ahmed",
        phone="9123456789",
        date="2026-08-26",
        time="19:00",
        party_size=2,
    )

    confirmation_id = booking["confirmation_id"]

    cancel_reservation(confirmation_id)

    result = modify_reservation(
        confirmation_id=confirmation_id,
        date="2026-08-26",
        time="20:00",
        party_size=2,
    )

    assert result["success"] is False


def test_modify_reservation_unavailable_time():
    booking = book_reservation(
        name="John",
        phone="9000000000",
        date="2026-08-27",
        time="19:00",
        party_size=4,
    )

    confirmation_id = booking["confirmation_id"]

    result = modify_reservation(
        confirmation_id=confirmation_id,
        date="2026-08-27",
        time="23:30",
        party_size=4,
    )

    assert result["success"] is False

    # Original reservation should remain unchanged
    reservation = get_reservation(confirmation_id)

    assert reservation["time"] == "19:00"