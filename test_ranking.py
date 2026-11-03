"""Tests for ranking logic, tie-breaks, and no-affordable-hotel handling.

Covers: FR-006 through FR-009, EC-010 through EC-015, AC-011 through AC-013,
        AC-016.

Uses small, self-contained fixtures (2–3 hotels, 3 places) for edge-case
isolation. No scenario-switching UI — code-level test fixtures only.
"""

from __future__ import annotations

from models import (
    ComparisonOutcome,
    Hotel,
    Place,
    PlaceType,
    TripScenario,
)
from calculations import calculate_comparison


# ---------------------------------------------------------------------------
# Helpers: build small focused scenarios
# ---------------------------------------------------------------------------

def _three_places(importances: tuple[int, ...] = (1, 1, 1)) -> list[Place]:
    """Return 3 places with given importances."""
    types = [PlaceType.ATTRACTION, PlaceType.FOOD, PlaceType.ATTRACTION]
    return [
        Place(f"P{i+1}", f"Place {i+1}", types[i], importances[i], 0, 0)
        for i in range(3)
    ]


def _hotel(
    hotel_id: str,
    cost: int,
    times: dict[str, int],
    *,
    name: str | None = None,
) -> Hotel:
    """Create a single hotel with specified times."""
    return Hotel(hotel_id, name or f"Hotel {hotel_id}", cost, times, 0, 0)


def _scenario(
    hotels: list[Hotel],
    places: list[Place],
    budget: int,
) -> TripScenario:
    return TripScenario("Test City", "$", budget, hotels, places)


def _default_times(value: int = 10) -> dict[str, int]:
    """Travel times of `value` for places P1, P2, P3."""
    return {"P1": value, "P2": value, "P3": value}


# =========================================================================
# Basic ranking by weighted total  (FR-006, FR-007)
# =========================================================================

class TestBasicRanking:
    """Lower weighted total → lower rank number (better)."""

    def test_two_hotels_different_totals(self):
        """HA total < HB total → HA rank-1, HB rank-2."""
        places = _three_places((1, 1, 1))  # imp_total = 3
        ha = _hotel("HA", 100, {"P1": 5, "P2": 5, "P3": 5})   # total = 15
        hb = _hotel("HB", 100, {"P1": 10, "P2": 10, "P3": 10}) # total = 30
        result = calculate_comparison(_scenario([ha, hb], places, budget=200))

        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HB"].rank == 2
        assert result.recommended_hotel_id == "HA"

    def test_three_hotels_ranked_consecutively(self):
        """FR-007: ranks are consecutive 1, 2, 3 with no gaps."""
        places = _three_places((2, 1, 1))  # imp_total = 4
        ha = _hotel("HA", 100, {"P1": 5, "P2": 5, "P3": 5})    # total = 2*5+1*5+1*5 = 20
        hb = _hotel("HB", 100, {"P1": 10, "P2": 10, "P3": 10}) # total = 40
        hc = _hotel("HC", 100, {"P1": 15, "P2": 15, "P3": 15}) # total = 60
        result = calculate_comparison(_scenario([ha, hb, hc], places, budget=200))

        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HB"].rank == 2
        assert result.hotel_results["HC"].rank == 3


# =========================================================================
# Tie-break by stay cost  (FR-006, EC-013, AC-012)
# =========================================================================

class TestTieBreakByCost:
    """Same weighted total → lower stay cost ranks first."""

    def test_same_total_different_cost(self):
        """EC-013: equal totals, cost 200 vs 100 → HB (100) ranks first."""
        places = _three_places((1, 1, 1))
        ha = _hotel("HA", 200, _default_times(10))  # total = 30
        hb = _hotel("HB", 100, _default_times(10))  # total = 30
        result = calculate_comparison(_scenario([ha, hb], places, budget=300))

        assert result.hotel_results["HA"].weighted_travel_total == 30
        assert result.hotel_results["HB"].weighted_travel_total == 30
        # HB has lower cost → rank 1
        assert result.hotel_results["HB"].rank == 1
        assert result.hotel_results["HA"].rank == 2
        assert result.recommended_hotel_id == "HB"


# =========================================================================
# Tie-break by hotel ID  (FR-006, EC-014, AC-012)
# =========================================================================

class TestTieBreakByHotelId:
    """Same total + same cost → lower ASCII hotel ID ranks first."""

    def test_same_total_same_cost_different_id(self):
        """EC-014: HA < HB in ASCII → HA ranks first."""
        places = _three_places((1, 1, 1))
        ha = _hotel("HA", 100, _default_times(10))  # total = 30
        hb = _hotel("HB", 100, _default_times(10))  # total = 30
        result = calculate_comparison(_scenario([ha, hb], places, budget=200))

        assert result.hotel_results["HA"].weighted_travel_total == 30
        assert result.hotel_results["HB"].weighted_travel_total == 30
        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HB"].rank == 2
        assert result.recommended_hotel_id == "HA"


# =========================================================================
# Same display average, different exact total  (EC-015, AC-016)
# =========================================================================

class TestSameDisplayAverageDifferentExactTotal:
    """Rank by exact weighted total, not the rounded display value."""

    def test_same_display_different_exact(self):
        """EC-015: imp=[5,5,4], imp_total=14.
        HA: times [3,2,1] → contributions [15,10,4] → total=29.
        HB: times [1,1,5] → contributions [5,5,20] → total=30.
        Both tenths = 21 (display 2.1), but HA ranks first by exact total.

        HA: (20*29+14)/(2*14) = 594/28 = 21.21... → floor = 21
        HB: (20*30+14)/(2*14) = 614/28 = 21.92... → floor = 21
        """
        places = _three_places((5, 5, 4))
        ha = _hotel("HA", 100, {"P1": 3, "P2": 2, "P3": 1})  # total = 29
        hb = _hotel("HB", 100, {"P1": 1, "P2": 1, "P3": 5})  # total = 30
        result = calculate_comparison(_scenario([ha, hb], places, budget=200))

        # Verify both display the same
        assert result.hotel_results["HA"].weighted_average_tenths == 21
        assert result.hotel_results["HB"].weighted_average_tenths == 21

        # But exact totals differ
        assert result.hotel_results["HA"].weighted_travel_total == 29
        assert result.hotel_results["HB"].weighted_travel_total == 30

        # HA ranks first (lower exact total)
        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HB"].rank == 2
        assert result.recommended_hotel_id == "HA"


# =========================================================================
# Over-budget hotels  (FR-008, EC-011)
# =========================================================================

class TestOverBudgetHotels:
    """Over-budget hotels get rank=None and are never recommended."""

    def test_over_budget_hotel_has_no_rank(self):
        """FR-008: over-budget → rank is None."""
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(10))   # affordable
        hb = _hotel("HB", 1500, _default_times(5))   # over budget, better total
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        assert result.hotel_results["HB"].is_affordable is False
        assert result.hotel_results["HB"].rank is None
        assert result.hotel_results["HA"].rank == 1
        assert result.recommended_hotel_id == "HA"

    def test_over_budget_hotel_shows_shortfall(self):
        """FR-008: over-budget hotel shows negative remaining budget."""
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(10))
        hb = _hotel("HB", 1200, _default_times(5))
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        assert result.hotel_results["HB"].remaining_budget == -200

    def test_over_budget_never_recommended(self):
        """Even with the best total, an over-budget hotel is not recommended."""
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(100))  # total=300, affordable
        hb = _hotel("HB", 2000, _default_times(1))   # total=3, over budget
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        assert result.hotel_results["HB"].weighted_travel_total < \
               result.hotel_results["HA"].weighted_travel_total
        assert result.hotel_results["HB"].rank is None
        assert result.recommended_hotel_id == "HA"


# =========================================================================
# No affordable hotel  (FR-009, EC-012, AC-013)
# =========================================================================

class TestNoAffordableHotel:
    """When all hotels exceed budget: NO_AFFORDABLE_HOTEL outcome."""

    def test_no_affordable_outcome(self):
        """EC-012: budget below every hotel cost."""
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(10))
        hb = _hotel("HB", 600, _default_times(15))
        result = calculate_comparison(_scenario([ha, hb], places, budget=100))

        assert result.outcome == ComparisonOutcome.NO_AFFORDABLE_HOTEL
        assert result.recommended_hotel_id is None

    def test_no_affordable_all_ranks_none(self):
        """All hotels must have rank=None. (FR-009)"""
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(10))
        hb = _hotel("HB", 600, _default_times(15))
        result = calculate_comparison(_scenario([ha, hb], places, budget=100))

        for hotel_result in result.hotel_results.values():
            assert hotel_result.rank is None

    def test_no_affordable_shortfalls_retained(self):
        """Shortfalls (negative remaining_budget) must be available. (FR-009)"""
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(10))
        hb = _hotel("HB", 600, _default_times(15))
        result = calculate_comparison(_scenario([ha, hb], places, budget=100))

        assert result.hotel_results["HA"].remaining_budget == -400
        assert result.hotel_results["HB"].remaining_budget == -500

    def test_budget_zero_no_affordable(self):
        """Budget=0 → all hotels over budget (costs start at 1). (DR-007)"""
        places = _three_places()
        ha = _hotel("HA", 100, _default_times(10))
        hb = _hotel("HB", 200, _default_times(15))
        result = calculate_comparison(_scenario([ha, hb], places, budget=0))

        assert result.outcome == ComparisonOutcome.NO_AFFORDABLE_HOTEL
        assert result.recommended_hotel_id is None
        assert result.hotel_results["HA"].remaining_budget == -100
        assert result.hotel_results["HB"].remaining_budget == -200


# =========================================================================
# Budget boundary  (FR-005, EC-010, EC-011, AC-011)
# =========================================================================

class TestBudgetBoundary:
    """Budget-boundary affordability checks."""

    def test_cost_equals_budget_is_affordable(self):
        """EC-010, AC-011: cost == budget → affordable, rank assigned."""
        places = _three_places()
        ha = _hotel("HA", 1000, _default_times(10))
        hb = _hotel("HB", 500, _default_times(15))
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        assert result.hotel_results["HA"].is_affordable is True
        assert result.hotel_results["HA"].remaining_budget == 0
        assert result.hotel_results["HA"].rank is not None

    def test_cost_one_above_budget_not_affordable(self):
        """EC-011, AC-011: cost == budget + 1 → not affordable."""
        places = _three_places()
        ha = _hotel("HA", 1001, _default_times(5))
        hb = _hotel("HB", 500, _default_times(15))
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        assert result.hotel_results["HA"].is_affordable is False
        assert result.hotel_results["HA"].remaining_budget == -1
        assert result.hotel_results["HA"].rank is None

    def test_boundary_hotel_can_be_recommended(self):
        """A hotel exactly at the budget should be eligible for rank-1."""
        places = _three_places()
        ha = _hotel("HA", 1000, _default_times(5))   # total=15, at budget
        hb = _hotel("HB", 500, _default_times(15))   # total=45, under budget
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        # HA has lower total → rank 1 despite being at the exact boundary
        assert result.hotel_results["HA"].rank == 1
        assert result.recommended_hotel_id == "HA"


# =========================================================================
# Single affordable hotel  (FR-007)
# =========================================================================

class TestSingleAffordableHotel:
    """When only one hotel is affordable, it gets rank=1."""

    def test_single_affordable_gets_rank_one(self):
        places = _three_places()
        ha = _hotel("HA", 500, _default_times(10))   # affordable
        hb = _hotel("HB", 2000, _default_times(5))   # over budget
        result = calculate_comparison(_scenario([ha, hb], places, budget=1000))

        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HB"].rank is None
        assert result.recommended_hotel_id == "HA"
        assert result.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE


# =========================================================================
# All hotels affordable  (FR-007)
# =========================================================================

class TestAllHotelsAffordable:
    """When every hotel is affordable, all get consecutive ranks."""

    def test_all_affordable_all_ranked(self):
        places = _three_places()
        ha = _hotel("HA", 100, _default_times(10))   # total=30
        hb = _hotel("HB", 200, _default_times(20))   # total=60
        result = calculate_comparison(_scenario([ha, hb], places, budget=5000))

        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HB"].rank == 2
        assert result.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE
        assert result.recommended_hotel_id == "HA"


# =========================================================================
# Consecutive ranks with no gaps  (FR-007)
# =========================================================================

class TestConsecutiveRanks:
    """Ranks must be 1, 2, 3, ... with no gaps or duplicates."""

    def test_four_affordable_consecutive_ranks(self):
        places = _three_places((2, 1, 1))  # imp_total = 4
        hotels = [
            _hotel("HA", 100, {"P1": 5, "P2": 5, "P3": 5}),     # total=20
            _hotel("HB", 100, {"P1": 10, "P2": 10, "P3": 10}),   # total=40
            _hotel("HC", 100, {"P1": 15, "P2": 15, "P3": 15}),   # total=60
            _hotel("HD", 100, {"P1": 20, "P2": 20, "P3": 20}),   # total=80
        ]
        result = calculate_comparison(_scenario(hotels, places, budget=500))

        ranks = sorted(
            r.rank for r in result.hotel_results.values() if r.rank is not None
        )
        assert ranks == [1, 2, 3, 4]

    def test_mix_of_affordable_and_over_budget(self):
        """Over-budget hotels don't create gaps in the affordable ranks."""
        places = _three_places()
        hotels = [
            _hotel("HA", 100, {"P1": 5, "P2": 5, "P3": 5}),     # total=15, affordable
            _hotel("HB", 9999, {"P1": 1, "P2": 1, "P3": 1}),    # total=3, over budget
            _hotel("HC", 200, {"P1": 10, "P2": 10, "P3": 10}),   # total=30, affordable
        ]
        result = calculate_comparison(_scenario(hotels, places, budget=500))

        assert result.hotel_results["HB"].rank is None  # over budget
        assert result.hotel_results["HA"].rank == 1
        assert result.hotel_results["HC"].rank == 2
        # No rank 3 exists — only 2 affordable hotels


# =========================================================================
# Main scenario ranking on the main data  (AC-012, AC-016)
# =========================================================================

class TestMainScenarioRankingOrder:
    """Verify the complete rank order on the main 10-hotel scenario."""

    def test_complete_rank_order(self):
        """Ranks: BREEZE=1, EMBER=2, CLIFF=3, DUSK=4, JADE=5, HAVEN=6.
        Over budget: AURORA, FROST, GALE, IVORY = None.
        """
        from scenario_data import create_main_scenario
        result = calculate_comparison(create_main_scenario())

        expected_ranked = [
            ("BREEZE", 1),
            ("EMBER", 2),
            ("CLIFF", 3),
            ("DUSK", 4),
            ("JADE", 5),
            ("HAVEN", 6),
        ]
        for hotel_id, expected_rank in expected_ranked:
            assert result.hotel_results[hotel_id].rank == expected_rank, (
                f"{hotel_id}: expected rank {expected_rank}, "
                f"got {result.hotel_results[hotel_id].rank}"
            )

        expected_unranked = ["AURORA", "FROST", "GALE", "IVORY"]
        for hotel_id in expected_unranked:
            assert result.hotel_results[hotel_id].rank is None, (
                f"{hotel_id} should have rank=None"
            )

    def test_exactly_one_rank_one(self):
        """FR-007: exactly one hotel has rank=1."""
        from scenario_data import create_main_scenario
        result = calculate_comparison(create_main_scenario())
        rank_one_hotels = [
            hid for hid, r in result.hotel_results.items() if r.rank == 1
        ]
        assert rank_one_hotels == ["BREEZE"]

    def test_no_duplicate_ranks(self):
        """FR-007: no two affordable hotels share a rank."""
        from scenario_data import create_main_scenario
        result = calculate_comparison(create_main_scenario())
        ranks = [
            r.rank for r in result.hotel_results.values() if r.rank is not None
        ]
        assert len(ranks) == len(set(ranks)), f"Duplicate ranks found: {ranks}"
