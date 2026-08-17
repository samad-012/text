from app.tools.registry import TOOLS, TOOL_SCHEMAS


def test_tool_registry():
    tool_names = [tool.__name__ for tool in TOOLS]

    assert len(TOOLS) == 6

    assert tool_names == [
        "check_availability",
        "book_reservation",
        "retrieve_reservation_by_confirmation",
        "retrieve_reservation_by_phone",
        "cancel_reservation",
        "modify_reservation",
    ]


def test_tool_schemas():
    assert len(TOOL_SCHEMAS) == 6

    schema_names = [
        schema["function"]["name"]
        for schema in TOOL_SCHEMAS
    ]

    assert schema_names == [
        "check_availability",
        "book_reservation",
        "retrieve_reservation_by_confirmation",
        "retrieve_reservation_by_phone",
        "cancel_reservation",
        "modify_reservation",
    ]