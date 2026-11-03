"""Tests for application state management (state.py).

Covers: initialize_state, load_scenario, update_budget, update_importance,
        inspect_hotel, reset_scenario.

Tests verify: initial state defaults, scenario loading and validation,
budget/importance changes and their effects on ranking, hotel inspection
without recalculation, invalid-input clearing of stale results, reset
restoring the exact original state, and deepcopy isolation between the
working scenario and the saved snapshot.

All expected values are independently calculated — not derived from
function outputs.  (NFR-006)
"""

from __future__ import annotations

import pytest

from models import AppState, ComparisonOutcome
from state import (
    initialize_state,
    load_scenario,
    update_budget,
    update_importance,
    inspect_hotel,
    reset_scenario,
)


# ---------------------------------------------------------------------------
# Independently documented expected values (from verified calculations)
# ---------------------------------------------------------------------------

INITIAL_BUDGET = 5000
INITIAL_RECOMMENDED = "BREEZE"
INITIAL_DEFAULT_INSPECTED = "BREEZE"
INITIAL_IMPORTANCE_TOTAL = 48
INITIAL_HOTEL_COUNT = 10
INITIAL_PLACE_COUNT = 15

# Initial ranks (independently verified)
INITIAL_RANKS = {
    "AURORA": None, "FROST": None, "GALE": None, "IVORY": None,
    "BREEZE": 1, "EMBER": 2, "CLIFF": 3,
    "DUSK": 4, "JADE": 5, "HAVEN": 6,
}

# Initial affordability (independently verified)
INITIAL_AFFORDABILITY = {
    "AURORA": False, "FROST": False, "GALE": False, "IVORY": False,
    "BREEZE": True, "EMBER": True, "CLIFF": True,
    "DUSK": True, "JADE": True, "HAVEN": True,
}

# Initial weighted totals (independently verified)
INITIAL_TOTALS = {
    "AURORA": 1349, "BREEZE": 1704, "CLIFF": 1912, "DUSK": 2046,
    "EMBER": 1740, "FROST": 1500, "GALE": 1579, "HAVEN": 2486,
    "IVORY": 1695, "JADE": 2120,
}

# TIDE_POOLS: original importance = 3, what-if importance = 4 → EMBER recommended
WHATIF_PLACE_ID = "TIDE_POOLS"
WHATIF_ORIGINAL_IMPORTANCE = 3
WHATIF_CHANGED_IMPORTANCE = 4
WHATIF_NEW_RECOMMENDED = "EMBER"


# ---------------------------------------------------------------------------
# Helper: create a loaded state (shortcut for tests that start post-load)
# ---------------------------------------------------------------------------

def _loaded_state() -> AppState:
    """Return an AppState with the main scenario already loaded."""
    state = initialize_state()
    load_scenario(state)
    return state


# =========================================================================
# 1. initialize_state
# =========================================================================

class TestInitializeState:
    """App starts with an empty workspace — no data loaded."""

    def test_returns_app_state(self):
        state = initialize_state()
        assert isinstance(state, AppState)

    def test_scenario_is_none(self):
        state = initialize_state()
        assert state.scenario is None

    def test_initial_scenario_is_none(self):
        state = initialize_state()
        assert state.initial_scenario is None

    def test_comparison_is_none(self):
        state = initialize_state()
        assert state.comparison is None

    def test_validation_issues_empty(self):
        state = initialize_state()
        assert state.validation_issues == []

    def test_inspected_hotel_is_none(self):
        state = initialize_state()
        assert state.inspected_hotel_id is None

    def test_default_inspected_hotel_is_none(self):
        state = initialize_state()
        assert state.default_inspected_hotel_id is None


# =========================================================================
# 2. load_scenario
# =========================================================================

class TestLoadScenario:
    """Loading must populate all state fields with the correct initial data."""

    def test_scenario_is_populated(self):
        state = _loaded_state()
        assert state.scenario is not None

    def test_initial_scenario_stored(self):
        """A separate snapshot must be saved for reset. (FR-018)"""
        state = _loaded_state()
        assert state.initial_scenario is not None

    def test_scenario_and_initial_are_different_objects(self):
        """Working copy and snapshot must be independent objects. (deepcopy)"""
        state = _loaded_state()
        assert state.scenario is not state.initial_scenario

    def test_hotel_count(self):
        state = _loaded_state()
        assert len(state.scenario.hotels) == INITIAL_HOTEL_COUNT

    def test_place_count(self):
        state = _loaded_state()
        assert len(state.scenario.places) == INITIAL_PLACE_COUNT

    def test_initial_budget(self):
        state = _loaded_state()
        assert state.scenario.budget == INITIAL_BUDGET

    def test_comparison_calculated(self):
        state = _loaded_state()
        assert state.comparison is not None

    def test_recommended_hotel(self):
        """Initial recommendation = BREEZE. (AC-004)"""
        state = _loaded_state()
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

    def test_outcome_is_recommendation_available(self):
        state = _loaded_state()
        assert state.comparison.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE

    def test_importance_total(self):
        state = _loaded_state()
        assert state.comparison.importance_total == INITIAL_IMPORTANCE_TOTAL

    def test_validation_issues_empty(self):
        state = _loaded_state()
        assert state.validation_issues == []

    def test_inspected_hotel_set_to_recommended(self):
        """Default inspected hotel = rank-1 (recommended). (FR-012, AC-017)"""
        state = _loaded_state()
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED

    def test_default_inspected_hotel_set(self):
        state = _loaded_state()
        assert state.default_inspected_hotel_id == INITIAL_DEFAULT_INSPECTED

    def test_all_ten_hotel_results_present(self):
        state = _loaded_state()
        assert len(state.comparison.hotel_results) == INITIAL_HOTEL_COUNT

    def test_initial_ranks(self):
        """Independently verified ranks for all 10 hotels."""
        state = _loaded_state()
        for hotel_id, expected_rank in INITIAL_RANKS.items():
            actual = state.comparison.hotel_results[hotel_id].rank
            assert actual == expected_rank, (
                f"{hotel_id}: expected rank={expected_rank}, got {actual}"
            )

    def test_initial_affordability(self):
        """Independently verified affordability for all 10 hotels."""
        state = _loaded_state()
        for hotel_id, expected_aff in INITIAL_AFFORDABILITY.items():
            actual = state.comparison.hotel_results[hotel_id].is_affordable
            assert actual == expected_aff, (
                f"{hotel_id}: expected affordable={expected_aff}, got {actual}"
            )

    def test_initial_weighted_totals(self):
        """Independently verified weighted totals for all 10 hotels."""
        state = _loaded_state()
        for hotel_id, expected_total in INITIAL_TOTALS.items():
            actual = state.comparison.hotel_results[hotel_id].weighted_travel_total
            assert actual == expected_total, (
                f"{hotel_id}: expected total={expected_total}, got {actual}"
            )


# =========================================================================
# 2b. load_scenario — re-loading resets everything
# =========================================================================

class TestLoadScenarioReload:
    """Loading again after changes must give a fresh initial state."""

    def test_reload_after_budget_change(self):
        state = _loaded_state()
        update_budget(state, 7500)
        assert state.comparison.recommended_hotel_id == "AURORA"

        load_scenario(state)
        assert state.scenario.budget == INITIAL_BUDGET
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

    def test_reload_after_importance_change(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)
        assert state.comparison.recommended_hotel_id == WHATIF_NEW_RECOMMENDED

        load_scenario(state)
        tp = next(p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID)
        assert tp.importance == WHATIF_ORIGINAL_IMPORTANCE
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

    def test_reload_clears_validation_issues(self):
        state = _loaded_state()
        update_budget(state, -1)
        assert len(state.validation_issues) > 0

        load_scenario(state)
        assert state.validation_issues == []

    def test_reload_restores_inspected_hotel(self):
        state = _loaded_state()
        inspect_hotel(state, "HAVEN")
        assert state.inspected_hotel_id == "HAVEN"

        load_scenario(state)
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED


# =========================================================================
# 3. update_budget — valid values
# =========================================================================

class TestUpdateBudgetValid:
    """Valid budget changes must recalculate affordability and ranking."""

    def test_budget_updates_scenario(self):
        state = _loaded_state()
        update_budget(state, 7500)
        assert state.scenario.budget == 7500

    def test_ac006_budget_7500_aurora_recommended(self):
        """AC-006: raising budget to $7,500 makes AURORA rank-1."""
        state = _loaded_state()
        update_budget(state, 7500)
        assert state.comparison.recommended_hotel_id == "AURORA"
        assert state.comparison.hotel_results["AURORA"].is_affordable is True
        assert state.comparison.hotel_results["AURORA"].rank == 1

    def test_budget_zero_no_affordable(self):
        """Budget=0 → all hotels over budget (cheapest=HAVEN at $3,500)."""
        state = _loaded_state()
        update_budget(state, 0)
        assert state.comparison.outcome == ComparisonOutcome.NO_AFFORDABLE_HOTEL
        assert state.comparison.recommended_hotel_id is None
        for r in state.comparison.hotel_results.values():
            assert r.rank is None

    def test_budget_3500_only_haven_affordable(self):
        """Budget exactly at HAVEN's cost ($3,500) → only HAVEN affordable."""
        state = _loaded_state()
        update_budget(state, 3500)
        assert state.comparison.hotel_results["HAVEN"].is_affordable is True
        assert state.comparison.hotel_results["HAVEN"].rank == 1
        assert state.comparison.recommended_hotel_id == "HAVEN"
        # All others are over budget
        for hid, r in state.comparison.hotel_results.items():
            if hid != "HAVEN":
                assert r.is_affordable is False
                assert r.rank is None

    def test_contributions_unchanged_after_budget_change(self):
        """FR-010: contributions must NOT change when only budget changes."""
        state = _loaded_state()
        original_contribs = {
            hid: dict(r.contributions)
            for hid, r in state.comparison.hotel_results.items()
        }

        update_budget(state, 8000)

        for hid, r in state.comparison.hotel_results.items():
            assert r.contributions == original_contribs[hid], (
                f"{hid}: contributions changed after budget update"
            )

    def test_totals_unchanged_after_budget_change(self):
        """FR-010: weighted totals must NOT change when only budget changes."""
        state = _loaded_state()
        original_totals = {
            hid: r.weighted_travel_total
            for hid, r in state.comparison.hotel_results.items()
        }

        update_budget(state, 3000)

        for hid, r in state.comparison.hotel_results.items():
            assert r.weighted_travel_total == original_totals[hid], (
                f"{hid}: weighted total changed after budget update"
            )

    def test_validation_issues_cleared_on_valid_budget(self):
        state = _loaded_state()
        update_budget(state, -1)  # invalid first
        assert len(state.validation_issues) > 0

        update_budget(state, 5000)  # valid now
        assert state.validation_issues == []

    def test_budget_boundary_zero(self):
        """DR-007: budget=0 is valid (lower boundary)."""
        state = _loaded_state()
        update_budget(state, 0)
        assert state.comparison is not None
        assert state.validation_issues == []

    def test_budget_boundary_one_million(self):
        """DR-007: budget=1,000,000 is valid (upper boundary)."""
        state = _loaded_state()
        update_budget(state, 1_000_000)
        assert state.comparison is not None
        assert state.validation_issues == []
        # All hotels should be affordable at $1M
        for r in state.comparison.hotel_results.values():
            assert r.is_affordable is True


# =========================================================================
# 3b. update_budget — invalid values
# =========================================================================

class TestUpdateBudgetInvalid:
    """Invalid budget must clear stale comparison and store errors. (FR-020)"""

    def test_negative_budget_clears_comparison(self):
        state = _loaded_state()
        assert state.comparison is not None  # pre-condition
        update_budget(state, -1)
        assert state.comparison is None
        assert len(state.validation_issues) > 0

    def test_over_million_clears_comparison(self):
        state = _loaded_state()
        update_budget(state, 1_000_001)
        assert state.comparison is None
        assert len(state.validation_issues) > 0

    def test_float_budget_clears_comparison(self):
        """DR-007: float is not int → rejected."""
        state = _loaded_state()
        update_budget(state, 5000.0)  # type: ignore[arg-type]
        assert state.comparison is None
        assert any("whole number" in e for e in state.validation_issues)

    def test_string_budget_clears_comparison(self):
        state = _loaded_state()
        update_budget(state, "5000")  # type: ignore[arg-type]
        assert state.comparison is None
        assert len(state.validation_issues) > 0

    def test_stale_results_cleared_completely(self):
        """FR-020: after valid result, invalid input must clear it."""
        state = _loaded_state()
        # Confirm valid result exists
        assert state.comparison is not None
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

        # Invalid budget
        update_budget(state, -50)
        assert state.comparison is None

    def test_scenario_unchanged_after_invalid_budget(self):
        """The scenario itself should remain intact for retries."""
        state = _loaded_state()
        update_budget(state, -1)
        assert state.scenario is not None
        assert state.scenario.budget == INITIAL_BUDGET  # budget wasn't applied

    def test_no_op_without_scenario(self):
        """update_budget on an empty state does nothing."""
        state = initialize_state()
        update_budget(state, 5000)
        assert state.comparison is None
        assert state.validation_issues == []


# =========================================================================
# 4. update_importance — valid values
# =========================================================================

class TestUpdateImportanceValid:
    """Valid importance changes must recalculate contributions and ranking."""

    def test_ac007_tide_pools_flips_recommendation(self):
        """AC-007: TIDE_POOLS 3→4 changes recommendation BREEZE→EMBER."""
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)
        assert state.comparison.recommended_hotel_id == WHATIF_NEW_RECOMMENDED

    def test_importance_updates_place(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 5)
        tp = next(p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID)
        assert tp.importance == 5

    def test_contributions_recalculated(self):
        """FR-011: contributions must change when importance changes."""
        state = _loaded_state()
        original_breeze_total = state.comparison.hotel_results["BREEZE"].weighted_travel_total

        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)

        new_breeze_total = state.comparison.hotel_results["BREEZE"].weighted_travel_total
        assert new_breeze_total != original_breeze_total

    def test_importance_total_changes(self):
        """FR-004: importance_total should reflect the new importance."""
        state = _loaded_state()
        assert state.comparison.importance_total == INITIAL_IMPORTANCE_TOTAL

        # TIDE_POOLS imp 3→4: importance_total goes from 48 to 49
        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)
        assert state.comparison.importance_total == INITIAL_IMPORTANCE_TOTAL + 1

    def test_affordability_unchanged_after_importance_change(self):
        """Importance doesn't affect stay cost or budget → affordability same."""
        state = _loaded_state()
        original_aff = {
            hid: r.is_affordable
            for hid, r in state.comparison.hotel_results.items()
        }

        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)

        for hid, r in state.comparison.hotel_results.items():
            assert r.is_affordable == original_aff[hid], (
                f"{hid}: affordability changed after importance update"
            )

    def test_remaining_budget_unchanged_after_importance_change(self):
        """Remaining budget is budget − stay_cost; unaffected by importance."""
        state = _loaded_state()
        original_remaining = {
            hid: r.remaining_budget
            for hid, r in state.comparison.hotel_results.items()
        }

        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)

        for hid, r in state.comparison.hotel_results.items():
            assert r.remaining_budget == original_remaining[hid], (
                f"{hid}: remaining_budget changed after importance update"
            )

    def test_validation_issues_cleared(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 0)  # invalid first
        assert len(state.validation_issues) > 0

        update_importance(state, WHATIF_PLACE_ID, 3)  # valid now
        assert state.validation_issues == []

    def test_importance_boundary_one(self):
        """DR-005: importance=1 is valid (lower bound)."""
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 1)
        assert state.comparison is not None
        assert state.validation_issues == []

    def test_importance_boundary_five(self):
        """DR-005: importance=5 is valid (upper bound)."""
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 5)
        assert state.comparison is not None
        assert state.validation_issues == []


# =========================================================================
# 4b. update_importance — invalid values
# =========================================================================

class TestUpdateImportanceInvalid:
    """Invalid importance must clear stale comparison. (FR-020, FR-021)"""

    def test_zero_importance_clears_comparison(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 0)
        assert state.comparison is None
        assert len(state.validation_issues) > 0

    def test_six_importance_clears_comparison(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 6)
        assert state.comparison is None
        assert len(state.validation_issues) > 0

    def test_negative_importance_clears_comparison(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, -1)
        assert state.comparison is None
        assert len(state.validation_issues) > 0

    def test_float_importance_clears_comparison(self):
        """DR-005: float is not int → rejected."""
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 3.0)  # type: ignore[arg-type]
        assert state.comparison is None
        assert any("whole number" in e for e in state.validation_issues)

    def test_nonexistent_place_clears_comparison(self):
        """Unknown place_id → validation error, comparison cleared."""
        state = _loaded_state()
        update_importance(state, "NONEXISTENT", 3)
        assert state.comparison is None
        assert any("not found" in e for e in state.validation_issues)

    def test_stale_results_cleared_after_valid_then_invalid(self):
        """FR-020: a valid comparison existed before; invalid input clears it."""
        state = _loaded_state()
        assert state.comparison is not None

        update_importance(state, WHATIF_PLACE_ID, 99)
        assert state.comparison is None

    def test_no_op_without_scenario(self):
        """update_importance on an empty state does nothing."""
        state = initialize_state()
        update_importance(state, WHATIF_PLACE_ID, 3)
        assert state.comparison is None
        assert state.validation_issues == []


# =========================================================================
# 5. inspect_hotel
# =========================================================================

class TestInspectHotel:
    """Inspection is view-only — rankings must NOT change. (FR-012, EC-018)"""

    def test_changes_inspected_hotel(self):
        state = _loaded_state()
        inspect_hotel(state, "AURORA")
        assert state.inspected_hotel_id == "AURORA"

    def test_inspect_multiple_hotels(self):
        state = _loaded_state()
        for hotel_id in ["AURORA", "HAVEN", "CLIFF", "EMBER"]:
            inspect_hotel(state, hotel_id)
            assert state.inspected_hotel_id == hotel_id

    def test_recommendation_unchanged(self):
        """FR-012: inspecting a different hotel must not change the recommendation."""
        state = _loaded_state()
        inspect_hotel(state, "HAVEN")
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

    def test_ranks_unchanged(self):
        """FR-012: ranks must not change when inspected hotel changes."""
        state = _loaded_state()
        inspect_hotel(state, "AURORA")
        for hotel_id, expected_rank in INITIAL_RANKS.items():
            actual = state.comparison.hotel_results[hotel_id].rank
            assert actual == expected_rank, (
                f"{hotel_id}: rank changed after inspection"
            )

    def test_outcome_unchanged(self):
        state = _loaded_state()
        inspect_hotel(state, "JADE")
        assert state.comparison.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE

    def test_contributions_unchanged(self):
        """Inspection must not trigger recalculation — contributions stay same."""
        state = _loaded_state()
        original_totals = {
            hid: r.weighted_travel_total
            for hid, r in state.comparison.hotel_results.items()
        }

        inspect_hotel(state, "FROST")

        for hid, r in state.comparison.hotel_results.items():
            assert r.weighted_travel_total == original_totals[hid]

    def test_comparison_object_identity_unchanged(self):
        """The comparison object itself should be the same reference (no recalc)."""
        state = _loaded_state()
        comparison_before = state.comparison
        inspect_hotel(state, "DUSK")
        assert state.comparison is comparison_before

    def test_nonexistent_hotel_ignored(self):
        """Inspecting a hotel that doesn't exist should be silently ignored."""
        state = _loaded_state()
        inspect_hotel(state, "NONEXISTENT")
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED

    def test_inspect_over_budget_hotel(self):
        """Any hotel can be inspected, including over-budget ones."""
        state = _loaded_state()
        inspect_hotel(state, "AURORA")
        assert state.inspected_hotel_id == "AURORA"
        assert state.comparison.hotel_results["AURORA"].is_affordable is False

    def test_no_op_without_scenario(self):
        """inspect_hotel on an empty state does nothing."""
        state = initialize_state()
        inspect_hotel(state, "BREEZE")
        assert state.inspected_hotel_id is None


# =========================================================================
# 6. reset_scenario
# =========================================================================

class TestResetScenario:
    """Reset must restore the exact original state. (FR-018, AC-017)"""

    def test_budget_restored(self):
        state = _loaded_state()
        update_budget(state, 9999)
        reset_scenario(state)
        assert state.scenario.budget == INITIAL_BUDGET

    def test_importance_restored(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)
        reset_scenario(state)
        tp = next(p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID)
        assert tp.importance == WHATIF_ORIGINAL_IMPORTANCE

    def test_recommendation_restored(self):
        state = _loaded_state()
        update_budget(state, 7500)
        assert state.comparison.recommended_hotel_id == "AURORA"
        reset_scenario(state)
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

    def test_inspected_hotel_restored(self):
        """FR-018, AC-017: reset restores the default inspected hotel."""
        state = _loaded_state()
        inspect_hotel(state, "HAVEN")
        assert state.inspected_hotel_id == "HAVEN"
        reset_scenario(state)
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED

    def test_ranks_restored(self):
        state = _loaded_state()
        update_budget(state, 7500)
        reset_scenario(state)
        for hotel_id, expected_rank in INITIAL_RANKS.items():
            actual = state.comparison.hotel_results[hotel_id].rank
            assert actual == expected_rank, (
                f"{hotel_id}: rank not restored after reset"
            )

    def test_affordability_restored(self):
        state = _loaded_state()
        update_budget(state, 0)
        reset_scenario(state)
        for hotel_id, expected_aff in INITIAL_AFFORDABILITY.items():
            actual = state.comparison.hotel_results[hotel_id].is_affordable
            assert actual == expected_aff, (
                f"{hotel_id}: affordability not restored after reset"
            )

    def test_weighted_totals_restored(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 5)
        reset_scenario(state)
        for hotel_id, expected_total in INITIAL_TOTALS.items():
            actual = state.comparison.hotel_results[hotel_id].weighted_travel_total
            assert actual == expected_total, (
                f"{hotel_id}: total not restored after reset"
            )

    def test_validation_issues_cleared(self):
        state = _loaded_state()
        update_budget(state, -1)
        assert len(state.validation_issues) > 0
        reset_scenario(state)
        assert state.validation_issues == []

    def test_comparison_restored_after_invalid_state(self):
        """Reset from an invalid state must restore a valid comparison."""
        state = _loaded_state()
        update_budget(state, -1)
        assert state.comparison is None
        reset_scenario(state)
        assert state.comparison is not None
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED

    def test_outcome_restored(self):
        state = _loaded_state()
        update_budget(state, 0)
        assert state.comparison.outcome == ComparisonOutcome.NO_AFFORDABLE_HOTEL
        reset_scenario(state)
        assert state.comparison.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE

    def test_reset_after_multiple_changes(self):
        """Budget change + importance change + inspection → reset restores all."""
        state = _loaded_state()
        update_budget(state, 7500)
        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)
        inspect_hotel(state, "FROST")

        reset_scenario(state)

        assert state.scenario.budget == INITIAL_BUDGET
        tp = next(p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID)
        assert tp.importance == WHATIF_ORIGINAL_IMPORTANCE
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED

    def test_repeated_reset_is_deterministic(self):
        """NFR-002, DR-015: repeated resets produce the same result."""
        state = _loaded_state()

        for _ in range(3):
            update_budget(state, 7500)
            inspect_hotel(state, "JADE")
            reset_scenario(state)

            assert state.scenario.budget == INITIAL_BUDGET
            assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED
            assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED
            for hotel_id, expected_rank in INITIAL_RANKS.items():
                assert state.comparison.hotel_results[hotel_id].rank == expected_rank

    def test_no_op_without_initial_scenario(self):
        """reset_scenario on an empty state does nothing."""
        state = initialize_state()
        reset_scenario(state)
        assert state.scenario is None
        assert state.comparison is None


# =========================================================================
# Deepcopy isolation: changes must NOT affect the snapshot
# =========================================================================

class TestDeepcopyIsolation:
    """Working scenario mutations must not leak into initial_scenario."""

    def test_budget_change_does_not_affect_snapshot(self):
        state = _loaded_state()
        update_budget(state, 9999)
        assert state.scenario.budget == 9999
        assert state.initial_scenario.budget == INITIAL_BUDGET

    def test_importance_change_does_not_affect_snapshot(self):
        state = _loaded_state()
        update_importance(state, WHATIF_PLACE_ID, 5)

        # Working copy changed
        working_tp = next(
            p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID
        )
        assert working_tp.importance == 5

        # Snapshot unchanged
        snapshot_tp = next(
            p for p in state.initial_scenario.places if p.place_id == WHATIF_PLACE_ID
        )
        assert snapshot_tp.importance == WHATIF_ORIGINAL_IMPORTANCE

    def test_snapshot_hotels_are_independent(self):
        """Mutating a working hotel should not affect the snapshot's hotel."""
        state = _loaded_state()
        working_hotel = state.scenario.hotels[0]
        snapshot_hotel = next(
            h for h in state.initial_scenario.hotels
            if h.hotel_id == working_hotel.hotel_id
        )
        original_cost = snapshot_hotel.stay_cost

        working_hotel.stay_cost = 999999

        assert snapshot_hotel.stay_cost == original_cost

    def test_snapshot_travel_times_are_independent(self):
        """Mutating working hotel's travel times must not affect snapshot."""
        state = _loaded_state()
        working_hotel = state.scenario.hotels[0]
        first_place_id = state.scenario.places[0].place_id
        snapshot_hotel = next(
            h for h in state.initial_scenario.hotels
            if h.hotel_id == working_hotel.hotel_id
        )
        original_time = snapshot_hotel.round_trip_minutes[first_place_id]

        working_hotel.round_trip_minutes[first_place_id] = 999

        assert snapshot_hotel.round_trip_minutes[first_place_id] == original_time

    def test_reset_produces_independent_working_copy(self):
        """After reset, the new working scenario must still be independent."""
        state = _loaded_state()
        reset_scenario(state)

        # Mutate the post-reset working scenario
        state.scenario.budget = 1

        # Snapshot must still hold original budget
        assert state.initial_scenario.budget == INITIAL_BUDGET

    def test_multiple_resets_keep_snapshot_intact(self):
        """Even after multiple load-change-reset cycles, the snapshot survives."""
        state = _loaded_state()

        for new_budget in [100, 7500, 0, 999999]:
            update_budget(state, new_budget)
            reset_scenario(state)
            assert state.initial_scenario.budget == INITIAL_BUDGET

        for imp in [1, 2, 4, 5]:
            update_importance(state, WHATIF_PLACE_ID, imp)
            reset_scenario(state)
            snapshot_tp = next(
                p for p in state.initial_scenario.places
                if p.place_id == WHATIF_PLACE_ID
            )
            assert snapshot_tp.importance == WHATIF_ORIGINAL_IMPORTANCE


# =========================================================================
# Combined flow: budget → importance → inspect → reset
# =========================================================================

class TestCombinedFlow:
    """End-to-end state transitions matching USER_FLOWS.md Flow 2."""

    def test_full_user_journey(self):
        """Simulate: load → budget change → importance change → inspect → reset."""
        state = initialize_state()

        # Step 1: load
        load_scenario(state)
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED

        # Step 2: raise budget → AURORA becomes recommended (AC-006)
        update_budget(state, 7500)
        assert state.comparison.recommended_hotel_id == "AURORA"
        assert state.comparison.hotel_results["AURORA"].rank == 1

        # Step 3: change TIDE_POOLS importance
        # (AURORA is now affordable, but we're also changing importance)
        update_importance(state, WHATIF_PLACE_ID, WHATIF_CHANGED_IMPORTANCE)
        assert state.comparison is not None
        # AURORA should still be rank-1 at budget=7500 (it has the lowest total)
        assert state.comparison.hotel_results["AURORA"].is_affordable is True

        # Step 4: inspect a different hotel
        inspect_hotel(state, "HAVEN")
        assert state.inspected_hotel_id == "HAVEN"
        # Comparison unchanged by inspection
        aurora_rank = state.comparison.hotel_results["AURORA"].rank
        assert aurora_rank is not None  # Still ranked

        # Step 5: reset
        reset_scenario(state)
        assert state.scenario.budget == INITIAL_BUDGET
        tp = next(p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID)
        assert tp.importance == WHATIF_ORIGINAL_IMPORTANCE
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED
        assert state.inspected_hotel_id == INITIAL_DEFAULT_INSPECTED
        assert state.validation_issues == []

    def test_invalid_then_recover(self):
        """Invalid input → stale cleared → valid input → results restored."""
        state = _loaded_state()

        # Invalid budget clears everything
        update_budget(state, -1)
        assert state.comparison is None
        assert len(state.validation_issues) > 0

        # Valid budget brings results back
        update_budget(state, 5000)
        assert state.comparison is not None
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED
        assert state.validation_issues == []

    def test_invalid_importance_then_reset(self):
        """Invalid importance → stale cleared → reset restores everything."""
        state = _loaded_state()

        update_importance(state, WHATIF_PLACE_ID, 0)
        assert state.comparison is None

        reset_scenario(state)
        assert state.comparison is not None
        assert state.comparison.recommended_hotel_id == INITIAL_RECOMMENDED
        tp = next(p for p in state.scenario.places if p.place_id == WHATIF_PLACE_ID)
        assert tp.importance == WHATIF_ORIGINAL_IMPORTANCE
