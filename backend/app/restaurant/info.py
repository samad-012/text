from dataclasses import dataclass


@dataclass(frozen=True)
class RestaurantInfo:
    name: str
    cuisine: str
    address: str
    phone: str
    max_capacity: int
    max_party_size: int
    opening_hours: dict[str, tuple[str, str]]


RESTAURANT = RestaurantInfo(
    name="saffron",
    cuisine="Italian",
    address="123 Main Street",
    phone="+1-555-0100",
    max_capacity=40,
    max_party_size=10,
    opening_hours={
        "monday": ("11:00", "22:00"),
        "tuesday": ("11:00", "22:00"),
        "wednesday": ("11:00", "22:00"),
        "thursday": ("11:00", "22:00"),
        "friday": ("11:00", "23:00"),
        "saturday": ("11:00", "23:00"),
        "sunday": ("11:00", "21:00"),
    },
)