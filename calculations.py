"""Calculation and validation engine for the Hotel Base-Camp Comparator.

This module contains all business logic: scenario validation, contribution
arithmetic, weighted totals/averages, affordability, ranking, and
recommendation. It is independent of any UI framework.

Reference: REQUIREMENTS.md (FR-002 through FR-009, FR-019 through FR-021,
           DR-001 through DR-012)
"""

from __future__ import annotations

import re

from models import (
    ComparisonOutcome,
    ComparisonResult,
    Hotel,
    HotelComparisonResult,
    Place,
    PlaceType,
    TripScenario,
)

_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]{0,15}$")


# ---------------------------------------------------------------------------
# Validation  (FR-019, FR-020, FR-021, DR-001 – DR-012)
# ---------------------------------------------------------------------------

def validate_scenario(scenario: TripScenario) -> list[str]:
    """Validate a complete TripScenario against all data constraints.

    Returns an empty list when the scenario is valid, or a list of
    field-specific error messages describing every problem found.
    Validation is exhaustive — all issues are reported, not just the first.
    """
    errors: list[str] = []

    # -- DR-001: hotel count 2–10 -----------------------------------------
    hotel_count = len(scenario.hotels)
    if hotel_count < 2 or hotel_count > 10:
        errors.append(
            f"Hotel count must be 2–10, got {hotel_count}."
        )

    # -- DR-001: place count 3–15 -----------------------------------------
    place_count = len(scenario.places)
    if place_count < 3 or place_count > 15:
        errors.append(
            f"Place count must be 3–15, got {place_count}."
        )

    # -- DR-007: budget must be a whole number 0–1,000,000 ----------------
    if not isinstance(scenario.budget, int):
        errors.append(
            f"Budget must be a whole number, got {type(scenario.budget).__name__}."
        )
    elif scenario.budget < 0 or scenario.budget > 1_000_000:
        errors.append(
            f"Budget must be 0–1,000,000, got {scenario.budget}."
        )

    # -- Collect all IDs for cross-entity uniqueness (DR-009) -------------
    all_ids: list[str] = []

    # -- Validate each place ----------------------------------------------
    place_ids: set[str] = set()
    for place in scenario.places:
        _validate_place(place, place_ids, all_ids, errors)

    # -- Validate each hotel ----------------------------------------------
    hotel_ids: set[str] = set()
    expected_place_ids = {p.place_id for p in scenario.places}
    for hotel in scenario.hotels:
        _validate_hotel(hotel, hotel_ids, all_ids, expected_place_ids, errors)

    # -- DR-009: cross-entity ID uniqueness (hotel ID = place ID) ---------
    seen: set[str] = set()
    for entity_id in all_ids:
        if entity_id in seen:
            errors.append(
                f"ID '{entity_id}' is used by both a hotel and a place."
            )
        seen.add(entity_id)

    return errors


def _validate_place(
    place: Place,
    seen_ids: set[str],
    all_ids: list[str],
    errors: list[str],
) -> None:
    """Validate a single Place and accumulate errors."""
    # -- DR-009: ID format ------------------------------------------------
    if not _ID_PATTERN.match(place.place_id):
        errors.append(
            f"Place ID '{place.place_id}' does not match [A-Z][A-Z0-9_-]{{0,15}}."
        )

    # -- DR-009: duplicate place ID ---------------------------------------
    if place.place_id in seen_ids:
        errors.append(f"Duplicate place ID '{place.place_id}'.")
    seen_ids.add(place.place_id)
    all_ids.append(place.place_id)

    # -- DR-010: non-empty name -------------------------------------------
    if not place.name or not place.name.strip():
        errors.append(
            f"Place '{place.place_id}' has an empty or whitespace-only name."
        )

    # -- DR-005: place type -----------------------------------------------
    if not isinstance(place.place_type, PlaceType):
        errors.append(
            f"Place '{place.place_id}' has unsupported type '{place.place_type}'."
        )

    # -- DR-005: importance must be int 1–5 -------------------------------
    if not isinstance(place.importance, int):
        errors.append(
            f"Place '{place.place_id}' importance must be a whole number, "
            f"got {type(place.importance).__name__}."
        )
    elif place.importance < 1 or place.importance > 5:
        errors.append(
            f"Place '{place.place_id}' importance must be 1–5, "
            f"got {place.importance}."
        )


def _validate_hotel(
    hotel: Hotel,
    seen_ids: set[str],
    all_ids: list[str],
    expected_place_ids: set[str],
    errors: list[str],
) -> None:
    """Validate a single Hotel and accumulate errors."""
    # -- DR-009: ID format ------------------------------------------------
    if not _ID_PATTERN.match(hotel.hotel_id):
        errors.append(
            f"Hotel ID '{hotel.hotel_id}' does not match [A-Z][A-Z0-9_-]{{0,15}}."
        )

    # -- DR-009: duplicate hotel ID ---------------------------------------
    if hotel.hotel_id in seen_ids:
        errors.append(f"Duplicate hotel ID '{hotel.hotel_id}'.")
    seen_ids.add(hotel.hotel_id)
    all_ids.append(hotel.hotel_id)

    # -- DR-010: non-empty name -------------------------------------------
    if not hotel.name or not hotel.name.strip():
        errors.append(
            f"Hotel '{hotel.hotel_id}' has an empty or whitespace-only name."
        )

    # -- DR-006: stay_cost must be int 1–1,000,000 ------------------------
    if not isinstance(hotel.stay_cost, int):
        errors.append(
            f"Hotel '{hotel.hotel_id}' stay_cost must be a whole number, "
            f"got {type(hotel.stay_cost).__name__}."
        )
    elif hotel.stay_cost < 1 or hotel.stay_cost > 1_000_000:
        errors.append(
            f"Hotel '{hotel.hotel_id}' stay_cost must be 1–1,000,000, "
            f"got {hotel.stay_cost}."
        )

    # -- DR-011: round_trip_minutes keys must match place IDs exactly -----
    mapping_keys = set(hotel.round_trip_minutes.keys())
    missing = expected_place_ids - mapping_keys
    extra = mapping_keys - expected_place_ids

    if missing:
        errors.append(
            f"Hotel '{hotel.hotel_id}' is missing travel times for: "
            f"{', '.join(sorted(missing))}."
        )
    if extra:
        errors.append(
            f"Hotel '{hotel.hotel_id}' has unknown place IDs in travel times: "
            f"{', '.join(sorted(extra))}."
        )

    # -- DR-012: each travel time must be int 1–600 -----------------------
    for place_id, time_val in hotel.round_trip_minutes.items():
        if not isinstance(time_val, int):
            errors.append(
                f"Hotel '{hotel.hotel_id}' travel time for '{place_id}' "
                f"must be a whole number, got {type(time_val).__name__}."
            )
        elif time_val < 1 or time_val > 600:
            errors.append(
                f"Hotel '{hotel.hotel_id}' travel time for '{place_id}' "
                f"must be 1–600, got {time_val}."
            )


# ---------------------------------------------------------------------------
# Core calculations  (FR-002, FR-003, FR-004, FR-005)
# ---------------------------------------------------------------------------

def calculate_contribution(importance: int, travel_time: int) -> int:
    """Calculate the weighted contribution for one hotel–place pair.

    contribution = importance × round_trip_minutes  (FR-002)
    """
    return importance * travel_time


def calculate_weighted_average_tenths(
    weighted_total: int,
    importance_total: int,
) -> int:
    """Calculate the display-ready weighted average as integer tenths.

    Uses the integer-only round-half-up formula from FR-004:
        rounded_tenths = floor((20 × weighted_total + importance_total)
                               / (2 × importance_total))

    Display the result as  rounded_tenths / 10  to show one decimal place.
    """
    return (20 * weighted_total + importance_total) // (2 * importance_total)


def calculate_hotel_result(
    hotel: Hotel,
    places: list[Place],
    budget: int,
    importance_total: int,
) -> HotelComparisonResult:
    """Calculate the full comparison result for a single hotel.

    Computes per-place contributions, weighted total, weighted average,
    affordability, and remaining budget.  Rank is left as None — it is
    assigned later during the ranking step.
    """
    # FR-002: contribution per place
    contributions: dict[str, int] = {}
    for place in places:
        time = hotel.round_trip_minutes[place.place_id]
        contributions[place.place_id] = calculate_contribution(
            place.importance, time
        )

    # FR-003: weighted travel total
    weighted_total = sum(contributions.values())

    # FR-004: weighted average in tenths (round-half-up)
    avg_tenths = calculate_weighted_average_tenths(
        weighted_total, importance_total
    )

    # FR-005: affordability (stay_cost ≤ budget)
    is_affordable = hotel.stay_cost <= budget

    # FR-008: remaining budget (negative = over budget)
    remaining = budget - hotel.stay_cost

    return HotelComparisonResult(
        hotel_id=hotel.hotel_id,
        contributions=contributions,
        weighted_travel_total=weighted_total,
        weighted_average_tenths=avg_tenths,
        is_affordable=is_affordable,
        remaining_budget=remaining,
        rank=None,
    )


# ---------------------------------------------------------------------------
# Full comparison with ranking  (FR-006, FR-007, FR-008, FR-009, FR-019)
# ---------------------------------------------------------------------------

def calculate_comparison(scenario: TripScenario) -> ComparisonResult:
    """Validate the scenario, calculate results, rank, and recommend.

    1. Validate the complete scenario (FR-019).  If invalid, raise
       ValueError with the joined error messages so the caller can
       surface them and clear stale results (FR-020).
    2. Calculate each hotel's result (FR-002 – FR-005).
    3. Rank only affordable hotels by the three-level sort key (FR-006):
       (weighted_travel_total ASC, stay_cost ASC, hotel_id ASC).
    4. Assign consecutive ranks starting at 1 (FR-007).
    5. Determine the outcome and recommendation (FR-007, FR-009).
    """
    # Step 1: validate (FR-019 — must not produce partial ranking)
    issues = validate_scenario(scenario)
    if issues:
        raise ValueError("\n".join(issues))

    # importance_total = sum of all place importance values (FR-004)
    importance_total = sum(p.importance for p in scenario.places)

    # Step 2: calculate every hotel's result
    hotel_results: dict[str, HotelComparisonResult] = {}
    for hotel in scenario.hotels:
        result = calculate_hotel_result(
            hotel, scenario.places, scenario.budget, importance_total
        )
        hotel_results[hotel.hotel_id] = result

    # Step 3: sort affordable hotels by the three-level key (FR-006)
    # (1) weighted_travel_total ASC, (2) stay_cost ASC, (3) hotel_id ASC
    affordable = [r for r in hotel_results.values() if r.is_affordable]
    hotel_cost_map = {h.hotel_id: h.stay_cost for h in scenario.hotels}
    affordable.sort(
        key=lambda r: (
            r.weighted_travel_total,
            hotel_cost_map[r.hotel_id],
            r.hotel_id,
        )
    )

    # Step 4: assign consecutive ranks starting at 1 (FR-007)
    for rank, result in enumerate(affordable, start=1):
        result.rank = rank

    # Step 5: determine outcome (FR-007, FR-009)
    if affordable:
        recommended_id = affordable[0].hotel_id
        outcome = ComparisonOutcome.RECOMMENDATION_AVAILABLE
    else:
        recommended_id = None
        outcome = ComparisonOutcome.NO_AFFORDABLE_HOTEL

    return ComparisonResult(
        importance_total=importance_total,
        hotel_results=hotel_results,
        recommended_hotel_id=recommended_id,
        outcome=outcome,
    )
