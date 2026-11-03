"""Tests for core calculations and main-scenario expected values.

Covers: calculate_contribution, calculate_weighted_average_tenths,
        calculate_hotel_result, and full main-scenario acceptance criteria
        (FR-002 through FR-010, AC-002 through AC-008, AC-016, DR-016).

All expected values are independently calculated — not imported from
scenario_data or application output. (NFR-006)
"""

from __future__ import annotations

import copy

from models import (
    ComparisonOutcome,
    Hotel,
    Place,
    PlaceType,
    TripScenario,
)
from calculations import (
    calculate_contribution,
    calculate_weighted_average_tenths,
    calculate_hotel_result,
    calculate_comparison,
)


# ---------------------------------------------------------------------------
# Independently hard-coded expected values for the main scenario
# ---------------------------------------------------------------------------

EXPECTED_IMPORTANCE_TOTAL = 48

# Hotel ID → (stay_cost, weighted_total, tenths, is_affordable, remaining, rank)
EXPECTED_HOTEL_RESULTS = {
    "AURORA": (7500, 1349, 281, False, -2500, None),
    "BREEZE": (4800, 1704, 355, True,   200,  1),
    "CLIFF":  (4200, 1912, 398, True,   800,  3),
    "DUSK":   (4500, 2046, 426, True,   500,  4),
    "EMBER":  (3900, 1740, 363, True,  1100,  2),
    "FROST":  (6200, 1500, 313, False, -1200, None),
    "GALE":   (5800, 1579, 329, False,  -800, None),
    "HAVEN":  (3500, 2486, 518, True,  1500,  6),
    "IVORY":  (5500, 1695, 353, False,  -500, None),
    "JADE":   (4600, 2120, 442, True,   400,  5),
}

# BREEZE per-place contributions (independently calculated: importance × time)
EXPECTED_BREEZE_CONTRIBUTIONS = {
    "CRYSTAL_CAVE":  5 * 28,   # 140
    "SUNSET_PEAK":   5 * 30,   # 150
    "OLD_LIGHT":     4 * 33,   # 132
    "DRAGON_BRIDGE": 4 * 26,   # 104
    "STAR_MUSEUM":   4 * 36,   # 144
    "CLOUD_GARDEN":  3 * 30,   # 90
    "TIDE_POOLS":    3 * 75,   # 225
    "WIND_TOWER":    2 * 48,   # 96
    "HARBOR_GRILL":  4 * 30,   # 120
    "SPICE_MARKET":  3 * 33,   # 99
    "MOON_BAKERY":   3 * 36,   # 108
    "FIRE_KITCHEN":  3 * 30,   # 90
    "CORAL_CAFE":    2 * 42,   # 84
    "DUNE_DINER":    2 * 35,   # 70
    "PEARL_BISTRO":  1 * 52,   # 52
}


# ---------------------------------------------------------------------------
# Helper: load the main scenario (immutable reference copy)
# ---------------------------------------------------------------------------

def _main_scenario() -> TripScenario:
    """Return a fresh copy of the main scenario."""
    from scenario_data import create_main_scenario
    return create_main_scenario()


# =========================================================================
# calculate_contribution  (FR-002)
# =========================================================================

class TestCalculateContribution:
    """contribution = importance × round_trip_minutes (FR-002)."""

    def test_basic_case(self):
        assert calculate_contribution(5, 30) == 150

    def test_minimum_values(self):
        """importance=1, time=1 → 1."""
        assert calculate_contribution(1, 1) == 1

    def test_maximum_values(self):
        """importance=5, time=600 → 3000."""
        assert calculate_contribution(5, 600) == 3000

    def test_asymmetric(self):
        """Different orderings of factors."""
        assert calculate_contribution(3, 50) == 150
        assert calculate_contribution(2, 75) == 150

    def test_identity(self):
        assert calculate_contribution(1, 100) == 100
        assert calculate_contribution(4, 1) == 4


# =========================================================================
# calculate_weighted_average_tenths  (FR-004)
# =========================================================================

class TestWeightedAverageTenths:
    """Uses integer-only round-half-up formula from FR-004:
    rounded_tenths = floor((20 × total + imp_total) / (2 × imp_total))
    """

    def test_exact_division(self):
        """480 / 48 = 10.0 → tenths = 100."""
        assert calculate_weighted_average_tenths(480, 48) == 100

    def test_ember_half_up(self):
        """EMBER: 1740 / 48 = 36.25 → display 36.3 → tenths = 363.
        (20*1740 + 48) / (2*48) = 34848 / 96 = 363.0
        """
        assert calculate_weighted_average_tenths(1740, 48) == 363

    def test_frost_half_up(self):
        """FROST: 1500 / 48 = 31.25 → display 31.3 → tenths = 313.
        (20*1500 + 48) / (2*48) = 30048 / 96 = 313.0
        """
        assert calculate_weighted_average_tenths(1500, 48) == 313

    def test_breeze_value(self):
        """BREEZE: 1704 / 48 = 35.5 → tenths = 355."""
        assert calculate_weighted_average_tenths(1704, 48) == 355

    def test_aurora_value(self):
        """AURORA: 1349 / 48 = 28.1041... → tenths = 281."""
        assert calculate_weighted_average_tenths(1349, 48) == 281

    def test_haven_value(self):
        """HAVEN: 2486 / 48 = 51.791... → tenths = 518."""
        assert calculate_weighted_average_tenths(2486, 48) == 518

    def test_round_down_case(self):
        """A value that rounds down (fractional tenths < 0.5).
        total=100, imp_total=48 → 100/48 = 2.0833... → display 2.1 → tenths=21.
        (20*100+48)/(2*48) = 2048/96 = 21.333... → floor = 21.
        """
        assert calculate_weighted_average_tenths(100, 48) == 21

    def test_small_values(self):
        """total=3, imp_total=2 → 3/2=1.5 → display 1.5 → tenths=15.
        (20*3+2)/(2*2) = 62/4 = 15.5 → floor = 15.
        """
        assert calculate_weighted_average_tenths(3, 2) == 15


# =========================================================================
# calculate_hotel_result  (FR-002 – FR-005)
# =========================================================================

class TestCalculateHotelResult:
    """Per-hotel calculation: contributions, total, average, affordability."""

    def _simple_places(self) -> list[Place]:
        return [
            Place("PA", "Place A", PlaceType.ATTRACTION, 3, 0, 0),
            Place("PB", "Place B", PlaceType.FOOD, 2, 0, 0),
            Place("PC", "Place C", PlaceType.ATTRACTION, 1, 0, 0),
        ]

    def _simple_hotel(self, cost: int = 500) -> Hotel:
        return Hotel("HA", "Hotel A", cost, {"PA": 10, "PB": 20, "PC": 30}, 0, 0)

    def test_contributions_are_correct(self):
        places = self._simple_places()
        hotel = self._simple_hotel()
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.contributions == {"PA": 30, "PB": 40, "PC": 30}

    def test_weighted_total(self):
        places = self._simple_places()
        hotel = self._simple_hotel()
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.weighted_travel_total == 100  # 30 + 40 + 30

    def test_weighted_average_tenths(self):
        places = self._simple_places()
        hotel = self._simple_hotel()
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        # 100/6 = 16.666... → (20*100+6)/(2*6) = 2006/12 = 167.166... → floor = 167
        assert result.weighted_average_tenths == 167

    def test_affordable_hotel(self):
        """cost <= budget → affordable. (FR-005)"""
        places = self._simple_places()
        hotel = self._simple_hotel(cost=500)
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.is_affordable is True
        assert result.remaining_budget == 500

    def test_over_budget_hotel(self):
        """cost > budget → not affordable. (FR-005)"""
        places = self._simple_places()
        hotel = self._simple_hotel(cost=1500)
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.is_affordable is False
        assert result.remaining_budget == -500

    def test_budget_boundary_affordable(self):
        """cost == budget → affordable. (EC-010, AC-011)"""
        places = self._simple_places()
        hotel = self._simple_hotel(cost=1000)
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.is_affordable is True
        assert result.remaining_budget == 0

    def test_budget_one_over(self):
        """cost == budget + 1 → not affordable. (EC-011, AC-011)"""
        places = self._simple_places()
        hotel = self._simple_hotel(cost=1001)
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.is_affordable is False
        assert result.remaining_budget == -1

    def test_rank_is_none(self):
        """Rank is always None from calculate_hotel_result."""
        places = self._simple_places()
        hotel = self._simple_hotel()
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.rank is None

    def test_hotel_id_preserved(self):
        places = self._simple_places()
        hotel = self._simple_hotel()
        result = calculate_hotel_result(hotel, places, budget=1000, importance_total=6)
        assert result.hotel_id == "HA"


# =========================================================================
# Main scenario — full comparison (AC-002 through AC-008, DR-016)
# =========================================================================

class TestMainScenarioExpectedResults:
    """Independently verify all 10 hotels against hard-coded expectations."""

    def test_importance_total(self):
        """Sum of all place importances = 48. (FR-004)"""
        result = calculate_comparison(_main_scenario())
        assert result.importance_total == EXPECTED_IMPORTANCE_TOTAL

    def test_outcome_is_recommendation_available(self):
        result = calculate_comparison(_main_scenario())
        assert result.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE

    def test_recommended_hotel_is_breeze(self):
        """BREEZE is the initial recommendation. (AC-004)"""
        result = calculate_comparison(_main_scenario())
        assert result.recommended_hotel_id == "BREEZE"

    def test_all_ten_hotels_present(self):
        result = calculate_comparison(_main_scenario())
        assert len(result.hotel_results) == 10
        assert set(result.hotel_results.keys()) == set(EXPECTED_HOTEL_RESULTS.keys())

    def test_weighted_travel_totals(self):
        """DR-016: independently documented weighted totals."""
        result = calculate_comparison(_main_scenario())
        for hotel_id, (_, expected_total, _, _, _, _) in EXPECTED_HOTEL_RESULTS.items():
            actual = result.hotel_results[hotel_id].weighted_travel_total
            assert actual == expected_total, (
                f"{hotel_id}: expected total {expected_total}, got {actual}"
            )

    def test_weighted_average_tenths(self):
        """DR-016: independently documented display averages."""
        result = calculate_comparison(_main_scenario())
        for hotel_id, (_, _, expected_tenths, _, _, _) in EXPECTED_HOTEL_RESULTS.items():
            actual = result.hotel_results[hotel_id].weighted_average_tenths
            assert actual == expected_tenths, (
                f"{hotel_id}: expected tenths {expected_tenths}, got {actual}"
            )

    def test_affordability(self):
        """DR-016: independently documented affordability flags."""
        result = calculate_comparison(_main_scenario())
        for hotel_id, (_, _, _, expected_aff, _, _) in EXPECTED_HOTEL_RESULTS.items():
            actual = result.hotel_results[hotel_id].is_affordable
            assert actual == expected_aff, (
                f"{hotel_id}: expected affordable={expected_aff}, got {actual}"
            )

    def test_remaining_budget(self):
        """DR-016: independently documented remaining budget values."""
        result = calculate_comparison(_main_scenario())
        for hotel_id, (_, _, _, _, expected_rem, _) in EXPECTED_HOTEL_RESULTS.items():
            actual = result.hotel_results[hotel_id].remaining_budget
            assert actual == expected_rem, (
                f"{hotel_id}: expected remaining={expected_rem}, got {actual}"
            )

    def test_ranks(self):
        """DR-016: independently documented ranks."""
        result = calculate_comparison(_main_scenario())
        for hotel_id, (_, _, _, _, _, expected_rank) in EXPECTED_HOTEL_RESULTS.items():
            actual = result.hotel_results[hotel_id].rank
            assert actual == expected_rank, (
                f"{hotel_id}: expected rank={expected_rank}, got {actual}"
            )


# =========================================================================
# Acceptance criteria (AC-002 through AC-007)
# =========================================================================

class TestAcceptanceCriteria:
    """High-level acceptance checks on the main scenario."""

    def test_ac002_affordable_count(self):
        """AC-002: exactly 4–7 affordable hotels at initial budget."""
        result = calculate_comparison(_main_scenario())
        affordable_count = sum(
            1 for r in result.hotel_results.values() if r.is_affordable
        )
        assert 4 <= affordable_count <= 7, (
            f"Expected 4–7 affordable, got {affordable_count}"
        )
        # More precisely, we expect exactly 6
        assert affordable_count == 6

    def test_ac003_unique_lowest_total_is_over_budget(self):
        """AC-003: hotel with unique lowest weighted total is over budget."""
        result = calculate_comparison(_main_scenario())
        totals = {
            hid: r.weighted_travel_total
            for hid, r in result.hotel_results.items()
        }
        min_total = min(totals.values())
        lowest_hotels = [hid for hid, t in totals.items() if t == min_total]
        assert len(lowest_hotels) == 1, "Lowest total must be unique"
        assert lowest_hotels[0] == "AURORA"
        assert result.hotel_results["AURORA"].is_affordable is False

    def test_ac004_recommendation_not_cheapest(self):
        """AC-004: recommended hotel ≠ cheapest affordable hotel."""
        result = calculate_comparison(_main_scenario())
        affordable = {
            hid: r for hid, r in result.hotel_results.items()
            if r.is_affordable
        }
        cheapest_id = min(
            affordable.keys(),
            key=lambda hid: EXPECTED_HOTEL_RESULTS[hid][0]  # stay_cost
        )
        assert cheapest_id == "HAVEN"
        assert result.recommended_hotel_id == "BREEZE"
        assert result.recommended_hotel_id != cheapest_id

    def test_ac005_ninety_minute_contrast(self):
        """AC-005: BREEZE ≤ 90 min everywhere; EMBER has > 90 min trip."""
        scenario = _main_scenario()
        breeze = next(h for h in scenario.hotels if h.hotel_id == "BREEZE")
        ember = next(h for h in scenario.hotels if h.hotel_id == "EMBER")

        assert all(t <= 90 for t in breeze.round_trip_minutes.values()), (
            "BREEZE must have all trips ≤ 90"
        )
        assert any(t > 90 for t in ember.round_trip_minutes.values()), (
            "EMBER must have at least one trip > 90"
        )

    def test_ac006_budget_increase_changes_recommendation(self):
        """AC-006: raising budget to $7,500 makes AURORA the recommendation."""
        scenario = _main_scenario()
        scenario.budget = 7500
        result = calculate_comparison(scenario)
        assert result.recommended_hotel_id == "AURORA"
        assert result.hotel_results["AURORA"].is_affordable is True
        assert result.hotel_results["AURORA"].rank == 1

    def test_ac007_importance_change_flips_recommendation(self):
        """AC-007: TIDE_POOLS importance 3 → 4 flips BREEZE → EMBER."""
        scenario = _main_scenario()
        tide_pools = next(
            p for p in scenario.places if p.place_id == "TIDE_POOLS"
        )
        assert tide_pools.importance == 3, "Pre-condition: original importance"
        tide_pools.importance = 4
        result = calculate_comparison(scenario)
        assert result.recommended_hotel_id == "EMBER"


# =========================================================================
# BREEZE contribution detail  (FR-002, FR-013)
# =========================================================================

class TestBreezeContributions:
    """Verify all 15 per-place contributions for the recommended hotel."""

    def test_all_fifteen_contributions(self):
        result = calculate_comparison(_main_scenario())
        breeze = result.hotel_results["BREEZE"]
        assert breeze.contributions == EXPECTED_BREEZE_CONTRIBUTIONS

    def test_contribution_sum_equals_total(self):
        result = calculate_comparison(_main_scenario())
        breeze = result.hotel_results["BREEZE"]
        assert sum(breeze.contributions.values()) == breeze.weighted_travel_total
        assert breeze.weighted_travel_total == 1704


# =========================================================================
# FR-010: budget change preserves contributions
# =========================================================================

class TestBudgetChangePreservesContributions:
    """Contributions must not change when only the budget changes. (FR-010, EC-016)"""

    def test_contributions_unchanged_after_budget_change(self):
        scenario_a = _main_scenario()
        result_a = calculate_comparison(scenario_a)

        scenario_b = _main_scenario()
        scenario_b.budget = 3000
        result_b = calculate_comparison(scenario_b)

        for hotel_id in EXPECTED_HOTEL_RESULTS:
            assert (
                result_a.hotel_results[hotel_id].contributions
                == result_b.hotel_results[hotel_id].contributions
            ), f"{hotel_id}: contributions changed after budget change"

    def test_totals_unchanged_after_budget_change(self):
        scenario_a = _main_scenario()
        result_a = calculate_comparison(scenario_a)

        scenario_b = _main_scenario()
        scenario_b.budget = 8000
        result_b = calculate_comparison(scenario_b)

        for hotel_id in EXPECTED_HOTEL_RESULTS:
            assert (
                result_a.hotel_results[hotel_id].weighted_travel_total
                == result_b.hotel_results[hotel_id].weighted_travel_total
            ), f"{hotel_id}: weighted total changed after budget change"

    def test_affordability_changes_after_budget_change(self):
        """Affordability SHOULD change — only contributions must not."""
        scenario = _main_scenario()
        scenario.budget = 3000
        result = calculate_comparison(scenario)
        # At $3,000 budget: no hotel affordable (cheapest HAVEN = $3,500)
        assert result.outcome == ComparisonOutcome.NO_AFFORDABLE_HOTEL


# =========================================================================
# Round-half-up specific cases  (FR-004, AC-016)
# =========================================================================

class TestRoundHalfUp:
    """Verify the integer formula matches round-half-up behaviour."""

    def test_ember_36_point_25_rounds_to_36_point_3(self):
        """1740/48 = 36.25 → 36.3 (half-up). Tenths = 363."""
        assert calculate_weighted_average_tenths(1740, 48) == 363

    def test_frost_31_point_25_rounds_to_31_point_3(self):
        """1500/48 = 31.25 → 31.3 (half-up). Tenths = 313."""
        assert calculate_weighted_average_tenths(1500, 48) == 313

    def test_breeze_35_point_5_exact(self):
        """1704/48 = 35.5 exactly → 35.5. Tenths = 355."""
        assert calculate_weighted_average_tenths(1704, 48) == 355

    def test_cliff_39_point_833_rounds_to_39_point_8(self):
        """1912/48 = 39.833... → 39.8. Tenths = 398."""
        assert calculate_weighted_average_tenths(1912, 48) == 398
