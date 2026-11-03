"""Domain model for the Hotel Base-Camp Comparator.

This module defines the data structures used throughout the application.
It contains only dataclasses and enums — no validation or calculation logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PlaceType(Enum):
    """Type of a wishlist place."""

    ATTRACTION = "attraction"
    FOOD = "food"


class ComparisonOutcome(Enum):
    """Overall outcome of a hotel comparison."""

    RECOMMENDATION_AVAILABLE = "recommendation_available"
    NO_AFFORDABLE_HOTEL = "no_affordable_hotel"


@dataclass
class Place:
    """A wishlist place in the fictional city."""

    place_id: str
    name: str
    place_type: PlaceType
    importance: int
    x: float
    y: float


@dataclass
class Hotel:
    """A hotel candidate in the fictional city."""

    hotel_id: str
    name: str
    stay_cost: int
    round_trip_minutes: dict[str, int]
    x: float
    y: float


@dataclass
class TripScenario:
    """A complete city scenario with hotels, places, and budget."""

    city_name: str
    currency: str
    budget: int
    hotels: list[Hotel]
    places: list[Place]


@dataclass
class HotelComparisonResult:
    """Comparison result for a single hotel."""

    hotel_id: str
    contributions: dict[str, int]
    weighted_travel_total: int
    weighted_average_tenths: int
    is_affordable: bool
    remaining_budget: int
    rank: int | None


@dataclass
class ComparisonResult:
    """Complete comparison result across all hotels."""

    importance_total: int
    hotel_results: dict[str, HotelComparisonResult]
    recommended_hotel_id: str | None
    outcome: ComparisonOutcome


@dataclass
class AppState:
    """Top-level application state."""

    scenario: TripScenario | None = None
    initial_scenario: TripScenario | None = None
    comparison: ComparisonResult | None = None
    validation_issues: list[str] = field(default_factory=list)
    inspected_hotel_id: str | None = None
    default_inspected_hotel_id: str | None = None
