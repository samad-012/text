from app.tools.book import book_reservation
from app.tools.cancel import cancel_reservation
from app.tools.retrieve import (
    retrieve_reservation_by_confirmation,
    retrieve_reservation_by_phone,
)


def test_retrieve_reservation_by_confirmation_id():
    booking = book_reservation(
        name="Mohammed",
        phone="9876543210",
        date="2026-08-17",
        time="19:00",
        party_size=4,
    )

    confirmation_id = booking["confirmation_id"]

    result = retrieve_reservation_by_confirmation(
        confirmation_id=confirmation_id,
    )

    assert result["success"] is True
    assert result["reservation"]["name"] == "Mohammed"
    assert result["reservation"]["phone"] == "9876543210"


def test_retrieve_reservation_by_phone():
    booking = book_reservation(
        name="Ahmed",
        phone="9123456789",
        date="2026-08-18",
        time="20:00",
        party_size=2,
    )

    result = retrieve_reservation_by_phone(
        phone="9123456789",
    )

    assert result["success"] is True
    assert result["reservation"]["name"] == "Ahmed"
    assert result["reservation"]["phone"] == "9123456789"


def test_retrieve_reservation_by_confirmation_id_not_found():
    result = retrieve_reservation_by_confirmation(
        confirmation_id="BT-DOES-NOT-EXIST",
    )

    assert result["success"] is False


def test_retrieve_reservation_by_phone_not_found():
    result = retrieve_reservation_by_phone(
        phone="0000000000",
    )

    assert result["success"] is False


def test_retrieve_reservation_by_confirmation_id_empty():
    result = retrieve_reservation_by_confirmation(
        confirmation_id="",
    )

    assert result["success"] is False


def test_retrieve_reservation_by_phone_empty():
    result = retrieve_reservation_by_phone(
        phone="",
    )

    assert result["success"] is False


def test_retrieve_reservation_by_phone_ignores_cancelled():
    booking = book_reservation(
        name="Cancelled User",
        phone="9999999999",
        date="2026-08-19",
        time="19:00",
        party_size=2,
    )

    confirmation_id = booking["confirmation_id"]

    cancel_result = cancel_reservation(
        confirmation_id=confirmation_id,
    )

    assert cancel_result["success"] is True

    result = retrieve_reservation_by_phone(
        phone="9999999999",
    )

    assert result["success"] is False