"""Tests for scenario validation (validate_scenario).

Covers: DR-001 through DR-012, FR-019, EC-001 through EC-009.
Tests use small, independent fixtures — not the main scenario data.
"""

from __future__ import annotations

import copy
import pytest

from models import Hotel, Place, PlaceType, TripScenario
from calculations import validate_scenario, calculate_comparison


# ---------------------------------------------------------------------------
# Helper: minimal valid scenario (2 hotels, 3 places — minimum allowed)
# ---------------------------------------------------------------------------

def _make_places(count: int = 3) -> list[Place]:
    """Return `count` valid places with IDs P1, P2, ..., Pn."""
    types = [PlaceType.ATTRACTION, PlaceType.FOOD]
    return [
        Place(
            place_id=f"P{i}",
            name=f"Place {i}",
            place_type=types[i % 2],
            importance=(i % 5) + 1,
            x=float(i * 10),
            y=float(i * 10),
        )
        for i in range(1, count + 1)
    ]


def _make_hotels(
    place_ids: list[str],
    count: int = 2,
    *,
    prefix: str = "H",
) -> list[Hotel]:
    """Return `count` valid hotels whose travel-time maps cover `place_ids`."""
    return [
        Hotel(
            hotel_id=f"{prefix}{i}",
            name=f"Hotel {i}",
            stay_cost=1000 * i,
            round_trip_minutes={pid: 30 for pid in place_ids},
            x=float(i * 100),
            y=float(i * 100),
        )
        for i in range(1, count + 1)
    ]


def _make_scenario(
    hotel_count: int = 2,
    place_count: int = 3,
    budget: int = 5000,
) -> TripScenario:
    """Return a minimal valid TripScenario."""
    places = _make_places(place_count)
    place_ids = [p.place_id for p in places]
    hotels = _make_hotels(place_ids, hotel_count)
    return TripScenario(
        city_name="Test City",
        currency="$",
        budget=budget,
        hotels=hotels,
        places=places,
    )


# =========================================================================
# Baseline: valid scenarios produce no errors
# =========================================================================

class TestValidBaseline:
    """Confirm that well-formed scenarios pass validation."""

    def test_minimal_valid_scenario(self):
        """2 hotels, 3 places — lower bound of DR-001."""
        scenario = _make_scenario(hotel_count=2, place_count=3)
        assert validate_scenario(scenario) == []

    def test_maximum_valid_scenario(self):
        """10 hotels, 15 places — upper bound of DR-001."""
        scenario = _make_scenario(hotel_count=10, place_count=15)
        assert validate_scenario(scenario) == []

    def test_main_scenario_is_valid(self):
        """The main Starfall Bay scenario must pass validation."""
        from scenario_data import create_main_scenario
        scenario = create_main_scenario()
        assert validate_scenario(scenario) == []


# =========================================================================
# DR-001: hotel and place count constraints
# =========================================================================

class TestCountConstraints:
    """EC-001: reject hotel count outside 2–10, place count outside 3–15."""

    def test_one_hotel_rejected(self):
        scenario = _make_scenario(hotel_count=1, place_count=3)
        # Manually patch: _make_scenario creates 1 hotel which is < 2
        errors = validate_scenario(scenario)
        assert any("Hotel count" in e and "1" in e for e in errors)

    def test_eleven_hotels_rejected(self):
        scenario = _make_scenario(hotel_count=11, place_count=3)
        errors = validate_scenario(scenario)
        assert any("Hotel count" in e and "11" in e for e in errors)

    def test_two_places_rejected(self):
        scenario = _make_scenario(hotel_count=2, place_count=2)
        errors = validate_scenario(scenario)
        assert any("Place count" in e and "2" in e for e in errors)

    def test_sixteen_places_rejected(self):
        scenario = _make_scenario(hotel_count=2, place_count=16)
        errors = validate_scenario(scenario)
        assert any("Place count" in e and "16" in e for e in errors)

    def test_zero_hotels_rejected(self):
        places = _make_places(3)
        scenario = TripScenario("C", "$", 1000, [], places)
        errors = validate_scenario(scenario)
        assert any("Hotel count" in e for e in errors)

    def test_zero_places_rejected(self):
        scenario = TripScenario("C", "$", 1000, [], [])
        errors = validate_scenario(scenario)
        assert any("Place count" in e for e in errors)


# =========================================================================
# DR-007: budget validation
# =========================================================================

class TestBudgetValidation:
    """Budget must be int 0–1,000,000. (DR-007, EC-007)"""

    def test_budget_zero_valid(self):
        scenario = _make_scenario(budget=0)
        errors = validate_scenario(scenario)
        # zero is within range — no budget error expected
        assert not any("Budget" in e for e in errors)

    def test_budget_one_million_valid(self):
        scenario = _make_scenario(budget=1_000_000)
        errors = validate_scenario(scenario)
        assert not any("Budget" in e for e in errors)

    def test_budget_negative_rejected(self):
        scenario = _make_scenario(budget=-1)
        errors = validate_scenario(scenario)
        assert any("Budget" in e for e in errors)

    def test_budget_over_million_rejected(self):
        scenario = _make_scenario(budget=1_000_001)
        errors = validate_scenario(scenario)
        assert any("Budget" in e for e in errors)

    def test_budget_float_rejected(self):
        """A float like 500.0 is not a whole number. (DR-007)"""
        scenario = _make_scenario()
        scenario.budget = 500.0  # type: ignore[assignment]
        errors = validate_scenario(scenario)
        assert any("Budget" in e and "whole number" in e for e in errors)

    def test_budget_string_rejected(self):
        scenario = _make_scenario()
        scenario.budget = "5000"  # type: ignore[assignment]
        errors = validate_scenario(scenario)
        assert any("Budget" in e for e in errors)


# =========================================================================
# DR-009: ID validation
# =========================================================================

class TestIdValidation:
    """IDs must match [A-Z][A-Z0-9_-]{0,15} and be unique. (DR-009, EC-003)"""

    def test_lowercase_place_id_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].place_id = "crystal"
        errors = validate_scenario(scenario)
        assert any("crystal" in e for e in errors)

    def test_starts_with_digit_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].hotel_id = "1HOTEL"
        errors = validate_scenario(scenario)
        assert any("1HOTEL" in e for e in errors)

    def test_id_too_long_rejected(self):
        """Max length is 16 total chars: [A-Z] + up to 15 more."""
        scenario = _make_scenario()
        long_id = "A" * 17  # 17 chars → exceeds [A-Z][...]{0,15}
        scenario.places[0].place_id = long_id
        errors = validate_scenario(scenario)
        assert any(long_id in e for e in errors)

    def test_id_exactly_16_chars_valid(self):
        scenario = _make_scenario()
        valid_id = "A" * 16  # [A-Z] + 15 more
        scenario.places[0].place_id = valid_id
        # Update hotel travel-time maps to include the new place ID
        for hotel in scenario.hotels:
            old_id = "P1"
            times = hotel.round_trip_minutes
            times[valid_id] = times.pop(old_id)
        errors = validate_scenario(scenario)
        assert not any(valid_id in e for e in errors)

    def test_duplicate_place_id_rejected(self):
        scenario = _make_scenario()
        scenario.places[1].place_id = scenario.places[0].place_id
        errors = validate_scenario(scenario)
        assert any("Duplicate place ID" in e for e in errors)

    def test_duplicate_hotel_id_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[1].hotel_id = scenario.hotels[0].hotel_id
        errors = validate_scenario(scenario)
        assert any("Duplicate hotel ID" in e for e in errors)

    def test_hotel_place_id_collision_rejected(self):
        """A hotel and a place sharing the same ID must be rejected. (EC-003)"""
        scenario = _make_scenario()
        shared_id = scenario.places[0].place_id  # "P1"
        scenario.hotels[0].hotel_id = shared_id
        errors = validate_scenario(scenario)
        assert any("both a hotel and a place" in e for e in errors)

    def test_empty_id_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].place_id = ""
        errors = validate_scenario(scenario)
        assert any("does not match" in e for e in errors)


# =========================================================================
# DR-010: name validation
# =========================================================================

class TestNameValidation:
    """Names must be non-empty after stripping. (DR-010, EC-004)"""

    def test_empty_place_name_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].name = ""
        errors = validate_scenario(scenario)
        assert any("empty" in e.lower() for e in errors)

    def test_whitespace_place_name_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].name = "   "
        errors = validate_scenario(scenario)
        assert any("whitespace" in e.lower() for e in errors)

    def test_empty_hotel_name_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].name = ""
        errors = validate_scenario(scenario)
        assert any("empty" in e.lower() for e in errors)

    def test_whitespace_hotel_name_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].name = "  \t "
        errors = validate_scenario(scenario)
        assert any("whitespace" in e.lower() for e in errors)


# =========================================================================
# DR-005: place importance validation
# =========================================================================

class TestImportanceValidation:
    """Importance must be int 1–5. (DR-005, EC-005)"""

    def test_importance_one_valid(self):
        scenario = _make_scenario()
        scenario.places[0].importance = 1
        errors = validate_scenario(scenario)
        assert not any("importance" in e.lower() for e in errors)

    def test_importance_five_valid(self):
        scenario = _make_scenario()
        scenario.places[0].importance = 5
        errors = validate_scenario(scenario)
        assert not any("importance" in e.lower() for e in errors)

    def test_importance_zero_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].importance = 0
        errors = validate_scenario(scenario)
        assert any("importance" in e.lower() and "0" in e for e in errors)

    def test_importance_six_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].importance = 6
        errors = validate_scenario(scenario)
        assert any("importance" in e.lower() and "6" in e for e in errors)

    def test_importance_float_rejected(self):
        """3.0 is not int. (DR-005)"""
        scenario = _make_scenario()
        scenario.places[0].importance = 3.0  # type: ignore[assignment]
        errors = validate_scenario(scenario)
        assert any("importance" in e.lower() and "whole number" in e for e in errors)

    def test_importance_negative_rejected(self):
        scenario = _make_scenario()
        scenario.places[0].importance = -1
        errors = validate_scenario(scenario)
        assert any("importance" in e.lower() for e in errors)


# =========================================================================
# DR-006: stay_cost validation
# =========================================================================

class TestStayCostValidation:
    """stay_cost must be int 1–1,000,000. (DR-006, EC-006)"""

    def test_cost_one_valid(self):
        scenario = _make_scenario()
        scenario.hotels[0].stay_cost = 1
        errors = validate_scenario(scenario)
        assert not any("stay_cost" in e for e in errors)

    def test_cost_one_million_valid(self):
        scenario = _make_scenario()
        scenario.hotels[0].stay_cost = 1_000_000
        errors = validate_scenario(scenario)
        assert not any("stay_cost" in e for e in errors)

    def test_cost_zero_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].stay_cost = 0
        errors = validate_scenario(scenario)
        assert any("stay_cost" in e for e in errors)

    def test_cost_over_million_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].stay_cost = 1_000_001
        errors = validate_scenario(scenario)
        assert any("stay_cost" in e for e in errors)

    def test_cost_float_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].stay_cost = 500.0  # type: ignore[assignment]
        errors = validate_scenario(scenario)
        assert any("stay_cost" in e and "whole number" in e for e in errors)

    def test_cost_negative_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].stay_cost = -100
        errors = validate_scenario(scenario)
        assert any("stay_cost" in e for e in errors)


# =========================================================================
# DR-011: travel-time mapping completeness
# =========================================================================

class TestTravelTimeMappingValidation:
    """Keys must match exactly all place IDs. (DR-011, EC-008)"""

    def test_missing_place_in_mapping_rejected(self):
        scenario = _make_scenario()
        del scenario.hotels[0].round_trip_minutes["P1"]
        errors = validate_scenario(scenario)
        assert any("missing" in e.lower() and "P1" in e for e in errors)

    def test_extra_place_in_mapping_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["UNKNOWN"] = 30
        errors = validate_scenario(scenario)
        assert any("unknown" in e.lower() and "UNKNOWN" in e for e in errors)

    def test_missing_and_extra_both_reported(self):
        """Both missing and extra keys should be surfaced."""
        scenario = _make_scenario()
        del scenario.hotels[0].round_trip_minutes["P1"]
        scenario.hotels[0].round_trip_minutes["GHOST"] = 15
        errors = validate_scenario(scenario)
        assert any("missing" in e.lower() and "P1" in e for e in errors)
        assert any("unknown" in e.lower() and "GHOST" in e for e in errors)


# =========================================================================
# DR-012: travel-time value validation
# =========================================================================

class TestTravelTimeValueValidation:
    """Each travel time must be int 1–600. (DR-012, EC-009)"""

    def test_time_one_valid(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["P1"] = 1
        errors = validate_scenario(scenario)
        assert not any("travel time" in e and "P1" in e for e in errors)

    def test_time_600_valid(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["P1"] = 600
        errors = validate_scenario(scenario)
        assert not any("travel time" in e and "P1" in e for e in errors)

    def test_time_zero_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["P1"] = 0
        errors = validate_scenario(scenario)
        assert any("travel time" in e and "P1" in e for e in errors)

    def test_time_601_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["P1"] = 601
        errors = validate_scenario(scenario)
        assert any("travel time" in e and "P1" in e for e in errors)

    def test_time_float_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["P1"] = 30.0  # type: ignore[assignment]
        errors = validate_scenario(scenario)
        assert any("travel time" in e and "whole number" in e for e in errors)

    def test_time_negative_rejected(self):
        scenario = _make_scenario()
        scenario.hotels[0].round_trip_minutes["P1"] = -5
        errors = validate_scenario(scenario)
        assert any("travel time" in e and "P1" in e for e in errors)


# =========================================================================
# Exhaustive error reporting
# =========================================================================

class TestExhaustiveReporting:
    """Validation must report ALL issues, not just the first. (FR-019)"""

    def test_multiple_errors_all_reported(self):
        """Introduce several different violations — all should appear."""
        scenario = _make_scenario()
        scenario.budget = -1                         # DR-007
        scenario.places[0].importance = 0            # DR-005
        scenario.hotels[0].stay_cost = 0             # DR-006
        scenario.hotels[0].round_trip_minutes["P1"] = 0  # DR-012

        errors = validate_scenario(scenario)
        assert len(errors) >= 4, f"Expected ≥4 errors, got {len(errors)}: {errors}"
        # Check that each category is represented
        assert any("Budget" in e for e in errors)
        assert any("importance" in e.lower() for e in errors)
        assert any("stay_cost" in e for e in errors)
        assert any("travel time" in e for e in errors)


# =========================================================================
# FR-019: calculate_comparison raises on invalid scenario
# =========================================================================

class TestCalculateComparisonRejectsInvalid:
    """calculate_comparison must raise ValueError on invalid data."""

    def test_raises_on_invalid_scenario(self):
        scenario = _make_scenario()
        scenario.budget = -1  # Invalid
        with pytest.raises(ValueError):
            calculate_comparison(scenario)

    def test_raises_on_duplicate_id(self):
        scenario = _make_scenario()
        scenario.places[1].place_id = scenario.places[0].place_id
        with pytest.raises(ValueError):
            calculate_comparison(scenario)

    def test_raises_on_missing_travel_time(self):
        scenario = _make_scenario()
        del scenario.hotels[0].round_trip_minutes["P1"]
        with pytest.raises(ValueError):
            calculate_comparison(scenario)

    def test_error_message_contains_details(self):
        """The ValueError message should contain the specific validation errors."""
        scenario = _make_scenario()
        scenario.budget = -1
        scenario.hotels[0].stay_cost = 0
        with pytest.raises(ValueError, match="Budget"):
            calculate_comparison(scenario)
