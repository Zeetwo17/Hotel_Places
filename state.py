"""Application state management for the Hotel Base-Camp Comparator.

This module provides functions to initialise, load, update, inspect, and
reset the AppState.  Each function mutates the supplied AppState in place
and delegates all calculation/validation work to calculations.py.

Reference: REQUIREMENTS.md (FR-001, FR-010–FR-012, FR-018–FR-021),
           USER_FLOWS.md (both flows)
"""

from __future__ import annotations

import copy

from models import AppState
from calculations import calculate_comparison, validate_scenario
from scenario_data import (
    create_main_scenario,
    DEFAULT_INSPECTED_HOTEL_ID,
)


# ---------------------------------------------------------------------------
# 1. initialize_state  (App Open)
# ---------------------------------------------------------------------------

def initialize_state() -> AppState:
    """Create an empty AppState with default values.

    Called once when the application starts.  No scenario is loaded yet —
    the user must click "Load Scenario" to populate the workspace.
    """
    return AppState()


# ---------------------------------------------------------------------------
# 2. load_scenario  (FR-001, FR-019, FR-020, USER_FLOWS Flow 1)
# ---------------------------------------------------------------------------

def load_scenario(state: AppState) -> None:
    """Load the fixed scenario, validate it, and calculate results.

    Steps (matching USER_FLOWS.md — Flow 1):
      1. Create the deterministic main scenario.
      2. Store a deep-copy as initial_scenario for later reset (FR-018).
      3. Validate the complete scenario (FR-019).
         - Invalid → store errors, clear comparison, stop.
         - Valid   → calculate comparison results.
      4. Set the default inspected hotel (FR-012, FR-018, AC-017).
    """
    scenario = create_main_scenario()

    # Keep an untouched copy for reset (FR-018)
    state.initial_scenario = copy.deepcopy(scenario)
    state.scenario = scenario

    # Validate and calculate (FR-019)
    issues = validate_scenario(scenario)
    if issues:
        state.validation_issues = issues
        state.comparison = None
        state.inspected_hotel_id = None
        state.default_inspected_hotel_id = None
        return

    state.validation_issues = []
    state.comparison = calculate_comparison(scenario)

    # Default inspected hotel = rank-1 (recommended) or configured default
    recommended = state.comparison.recommended_hotel_id
    default_id = recommended if recommended else DEFAULT_INSPECTED_HOTEL_ID
    state.inspected_hotel_id = default_id
    state.default_inspected_hotel_id = default_id


# ---------------------------------------------------------------------------
# 3. update_budget  (FR-010, FR-020, FR-021, USER_FLOWS Flow 2 – Change Budget)
# ---------------------------------------------------------------------------

def update_budget(state: AppState, budget: int) -> None:
    """Change the budget and recalculate affordability and ranking.

    Steps (matching USER_FLOWS.md — Change Budget):
      1. Validate the new budget value (DR-007).
         - Invalid → store error, clear stale comparison, stop.
      2. Update the working scenario's budget.
      3. Recalculate the full comparison.
         Contributions remain unchanged because importance values and
         travel times have not changed (FR-010, EC-016).
    """
    if state.scenario is None:
        return

    # Validate budget (DR-007: integer, 0–1,000,000)
    if not isinstance(budget, int):
        state.validation_issues = [
            f"Budget must be a whole number, got {type(budget).__name__}."
        ]
        state.comparison = None
        return

    if budget < 0 or budget > 1_000_000:
        state.validation_issues = [
            f"Budget must be 0–1,000,000, got {budget}."
        ]
        state.comparison = None
        return

    # Apply the new budget and recalculate (FR-010)
    state.scenario.budget = budget
    state.validation_issues = []
    state.comparison = calculate_comparison(state.scenario)


# ---------------------------------------------------------------------------
# 4. update_importance  (FR-011, FR-020, FR-021,
#                        USER_FLOWS Flow 2 – Change Importance)
# ---------------------------------------------------------------------------

def update_importance(
    state: AppState,
    place_id: str,
    importance: int,
) -> None:
    """Change a place's importance and recalculate all hotel results.

    Steps (matching USER_FLOWS.md — Change Importance):
      1. Validate the new importance value (DR-005).
         - Invalid → store error, clear stale comparison, stop.
      2. Find the place and update its importance.
      3. Recalculate the full comparison — contributions, weighted totals,
         averages, and ranking all change (FR-011).
         Affordability is unchanged (stay costs and budget are unaffected).
    """
    if state.scenario is None:
        return

    # Validate importance (DR-005: integer, 1–5)
    if not isinstance(importance, int):
        state.validation_issues = [
            f"Importance must be a whole number, got {type(importance).__name__}."
        ]
        state.comparison = None
        return

    if importance < 1 or importance > 5:
        state.validation_issues = [
            f"Importance must be 1–5, got {importance}."
        ]
        state.comparison = None
        return

    # Find the place
    place = next(
        (p for p in state.scenario.places if p.place_id == place_id),
        None,
    )
    if place is None:
        state.validation_issues = [
            f"Place '{place_id}' not found in the current scenario."
        ]
        state.comparison = None
        return

    # Apply the new importance and recalculate (FR-011)
    place.importance = importance
    state.validation_issues = []
    state.comparison = calculate_comparison(state.scenario)


# ---------------------------------------------------------------------------
# 5. inspect_hotel  (FR-012, FR-013, FR-015, EC-018,
#                    USER_FLOWS Flow 2 – Inspect Hotel)
# ---------------------------------------------------------------------------

def inspect_hotel(state: AppState, hotel_id: str) -> None:
    """Change the currently inspected hotel.

    This is a view-only action — it does NOT recalculate anything.
    Rankings and recommendation remain unchanged (FR-012, EC-018).
    The UI will use this to show the contribution table and highlight
    the hotel's 15 comparison links on the map (FR-013, FR-015).
    """
    if state.scenario is None:
        return

    # Verify the hotel exists in the current scenario
    hotel_ids = {h.hotel_id for h in state.scenario.hotels}
    if hotel_id in hotel_ids:
        state.inspected_hotel_id = hotel_id


# ---------------------------------------------------------------------------
# 6. reset_scenario  (FR-018, AC-017, USER_FLOWS Flow 2 – Reset)
# ---------------------------------------------------------------------------

def reset_scenario(state: AppState) -> None:
    """Restore the original scenario, its comparison, and default hotel.

    Steps (matching USER_FLOWS.md — Reset):
      1. Deep-copy the saved initial_scenario back into the working scenario
         — restoring original budget, importance values, and all data
         (FR-018, NFR-002, DR-015).
      2. Recalculate to the documented initial state (AC-017).
      3. Restore the default inspected hotel = initial rank-1 (FR-018).
      4. Clear any validation issues.
    """
    if state.initial_scenario is None:
        return

    # Restore the original scenario from the saved snapshot
    state.scenario = copy.deepcopy(state.initial_scenario)

    # Recalculate to initial state (FR-018, AC-017)
    state.validation_issues = []
    state.comparison = calculate_comparison(state.scenario)

    # Restore the default inspected hotel (FR-018, AC-017)
    state.inspected_hotel_id = state.default_inspected_hotel_id
