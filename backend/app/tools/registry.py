from app.tools.availability import check_availability
from app.tools.book import book_reservation
from app.tools.retrieve import (
    retrieve_reservation_by_confirmation,
    retrieve_reservation_by_phone,
)
from app.tools.cancel import cancel_reservation
from app.tools.modify import modify_reservation


TOOLS = [
    check_availability,
    book_reservation,
    retrieve_reservation_by_confirmation,
    retrieve_reservation_by_phone,
    cancel_reservation,
    modify_reservation,
]

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Check whether a restaurant table is available "
                "for a specific date, time, and party size."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Reservation date in YYYY-MM-DD format.",
                    },
                    "time": {
                        "type": "string",
                        "description": "Reservation time in HH:MM 24-hour format.",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of guests.",
                    },
                },
                "required": [
                    "date",
                    "time",
                    "party_size",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_reservation",
            "description": (
                "Book a restaurant reservation after confirming "
                "the requested date, time, and party size are available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Customer's full name.",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Customer's phone number.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Reservation date in YYYY-MM-DD format.",
                    },
                    "time": {
                        "type": "string",
                        "description": "Reservation time in HH:MM 24-hour format.",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of guests.",
                    },
                },
                "required": [
                    "name",
                    "phone",
                    "date",
                    "time",
                    "party_size",
                ],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "retrieve_reservation_by_confirmation",
        "description": (
            "Retrieve an existing restaurant reservation using "
            "the reservation confirmation ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "confirmation_id": {
                    "type": "string",
                    "description": "Reservation confirmation ID.",
                },
            },
            "required": [
                "confirmation_id",
            ],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "retrieve_reservation_by_phone",
        "description": (
            "Retrieve an existing restaurant reservation using "
            "the customer's phone number."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": "Phone number used for the reservation.",
                },
            },
            "required": [
                "phone",
            ],
        },
    },
},

    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": (
                "Cancel an existing restaurant reservation using "
                "its confirmation ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation_id": {
                        "type": "string",
                        "description": "Reservation confirmation ID.",
                    },
                },
                "required": [
                    "confirmation_id",
                ],
            },
        },
    },
    {
    "type": "function",
    "function": {
        "name": "modify_reservation",
        "description": (
            "Modify the date, time, or party size of an existing "
            "restaurant reservation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "confirmation_id": {
                    "type": "string",
                    "description": "Reservation confirmation ID.",
                },
                "date": {
                    "type": "string",
                    "description": "New reservation date in YYYY-MM-DD format.",
                },
                "time": {
                    "type": "string",
                    "description": "New reservation time in HH:MM 24-hour format.",
                },
                "party_size": {
                    "type": "integer",
                    "description": "New number of guests.",
                },
            },
            "required": [
                "confirmation_id",
            ],
        },
    },
},
]