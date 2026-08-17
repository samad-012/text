from app.tools.availability import check_availability


def test_check_availability_available():
    result = check_availability(
        date="2026-08-17",
        time="19:00",
        party_size=4,
    )

    assert result["available"] is True
    assert result["date"] == "2026-08-17"
    assert result["time"] == "19:00"
    assert result["party_size"] == 4


def test_check_availability_invalid_party_size():
    result = check_availability(
        date="2026-08-17",
        time="19:00",
        party_size=0,
    )

    assert result["available"] is False


def test_check_availability_party_too_large():
    result = check_availability(
        date="2026-08-17",
        time="19:00",
        party_size=11,
    )

    assert result["available"] is False


def test_check_availability_invalid_date_time():
    result = check_availability(
        date="tomorrow",
        time="seven",
        party_size=4,
    )

    assert result["available"] is False


def test_check_availability_outside_opening_hours():
    result = check_availability(
        date="2026-08-17",
        time="23:30",
        party_size=4,
    )

    assert result["available"] is False