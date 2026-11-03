"""Tests for app.py using pytest and Streamlit AppTest.

Covers:
- Initial application state (pre-load view)
- Loading the scenario
- Budget changes and their effect on rankings/recommendation
- Importance changes and their effect on rankings/recommendation
- Hotel inspection (no recalculation)
- Reset to original state
- No-affordable-hotel scenario
- Invalid input handling
- Synchronisation between displayed rankings, contribution detail, and state

Expected values are independently calculated from scenario_data.py,
not copied from function outputs.

Reference: REQUIREMENTS.md, USER_FLOWS.md
"""

import pytest
from streamlit.testing.v1 import AppTest


# ---------------------------------------------------------------------------
# Independently verified expected values (from scenario_data.py + formulas)
# ---------------------------------------------------------------------------
# importance_total = 5+5+4+4+4+3+3+2+4+3+3+3+2+2+1 = 48
IMPORTANCE_TOTAL = 48
INITIAL_BUDGET = 5000
CITY_NAME = "Starfall Bay"

# Hotel expected results at budget=5000
#   (hotel_id, cost, wtd_total, avg_tenths, affordable, remaining, rank)
EXPECTED_INITIAL = {
    "AURORA":  (7500, 1349, 281, False, -2500, None),
    "BREEZE":  (4800, 1704, 355, True,    200,    1),
    "CLIFF":   (4200, 1912, 398, True,    800,    3),
    "DUSK":    (4500, 2046, 426, True,    500,    4),
    "EMBER":   (3900, 1740, 363, True,   1100,    2),
    "FROST":   (6200, 1500, 313, False, -1200, None),
    "GALE":    (5800, 1579, 329, False,  -800, None),
    "HAVEN":   (3500, 2486, 518, True,   1500,    6),
    "IVORY":   (5500, 1695, 353, False,  -500, None),
    "JADE":    (4600, 2120, 442, True,    400,    5),
}

INITIAL_RECOMMENDATION = "BREEZE"
DEFAULT_INSPECTED_HOTEL = "BREEZE"
AFFORDABLE_COUNT_INITIAL = 6

# AC-006: budget $7500 → AURORA becomes rank-1
BUDGET_ALL_AFFORDABLE = 7500

# AC-007: TIDE_POOLS importance 3→4 flips recommendation BREEZE→EMBER
WHAT_IF_PLACE_ID = "TIDE_POOLS"
WHAT_IF_NEW_IMPORTANCE = 4

# Number of hotels and places
NUM_HOTELS = 10
NUM_PLACES = 15


# ---------------------------------------------------------------------------
# Helper: create a loaded AppTest instance
# ---------------------------------------------------------------------------

def _load_app() -> AppTest:
    """Create and run the app, then click Load Scenario."""
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    # Click the "Load Scenario" button (pre-load view)
    at.button[0].click()
    at.run(timeout=30)
    return at


# =========================================================================
# 1. Initial Application State (Pre-Load)
# =========================================================================

class TestPreLoadView:
    """Before loading a scenario, only the title and Load button appear."""

    def test_title_shown(self):
        """FR-001: title is displayed before loading."""
        at = AppTest.from_file("app.py").run(timeout=30)
        assert not at.exception
        titles = [t.value for t in at.title]
        assert any("Hotel Base-Camp Comparator" in t for t in titles)

    def test_load_button_present(self):
        """FR-001: a Load Scenario button is shown."""
        at = AppTest.from_file("app.py").run(timeout=30)
        assert len(at.button) >= 1

    def test_no_success_or_warning_before_load(self):
        """No recommendation or no-affordable banner before loading."""
        at = AppTest.from_file("app.py").run(timeout=30)
        assert len(at.success) == 0
        assert len(at.warning) == 0


# =========================================================================
# 2. Loading the Scenario
# =========================================================================

class TestLoadScenario:
    """Clicking Load Scenario populates the workspace. (FR-001)"""

    def test_no_exception_after_load(self):
        at = _load_app()
        assert not at.exception

    def test_recommendation_banner_shown(self):
        """FR-007: a recommendation banner appears after load."""
        at = _load_app()
        assert len(at.success) >= 1
        banner_text = at.success[0].value
        assert "Recommended" in banner_text

    def test_recommended_hotel_is_breeze(self):
        """AC-004: BREEZE is the initial recommendation."""
        at = _load_app()
        banner_text = at.success[0].value
        assert "Breeze Inn" in banner_text

    def test_no_validation_errors(self):
        """FR-019: the main scenario must be valid."""
        at = _load_app()
        assert len(at.error) == 0

    def test_map_rendered(self):
        """FR-014: a map is shown after loading."""
        at = _load_app()
        # AppTest does not expose plotly_chart as a direct collection;
        # use the get() workaround.  Chart content is verified manually.
        charts = at.get("plotly_chart")
        assert len(charts) >= 1

    def test_ranking_dataframe_present(self):
        """FR-006: a ranking table is displayed."""
        at = _load_app()
        assert len(at.dataframe) >= 1

    def test_ranking_table_has_all_hotels(self):
        """All 10 hotels appear in the ranking table."""
        at = _load_app()
        df = at.dataframe[0].value
        assert len(df) == NUM_HOTELS

    def test_ranking_table_recommended_hotel_first(self):
        """AC-004: rank-1 hotel appears first in the ranking table."""
        at = _load_app()
        df = at.dataframe[0].value
        first_row = df.iloc[0]
        assert first_row["Rank"] == "1"
        assert first_row["Status"] == "★ Recommended"
        assert "Breeze" in first_row["Hotel"]

    def test_affordable_count_in_caption(self):
        """FR-008: caption shows affordable count."""
        at = _load_app()
        captions = [c.value for c in at.caption]
        found = any(
            f"Affordable: {AFFORDABLE_COUNT_INITIAL} of {NUM_HOTELS}" in c
            for c in captions
        )
        assert found

    def test_importance_total_in_caption(self):
        """Caption shows the importance total."""
        at = _load_app()
        captions = [c.value for c in at.caption]
        found = any(
            f"Importance total: {IMPORTANCE_TOTAL}" in c for c in captions
        )
        assert found

    def test_city_name_displayed(self):
        """The city name appears somewhere in the sidebar."""
        at = _load_app()
        headers = [h.value for h in at.header]
        found = any(CITY_NAME in h for h in headers)
        assert found


# =========================================================================
# 3. Budget Changes
# =========================================================================

class TestBudgetChange:
    """Changing the budget recalculates affordability and ranking."""

    def test_raise_budget_makes_aurora_recommended(self):
        """AC-006: budget=$7500 → AURORA becomes rank-1."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()

        assert not at.exception
        assert len(at.success) >= 1
        banner_text = at.success[0].value
        assert "Aurora Hotel" in banner_text

    def test_raise_budget_all_affordable(self):
        """AC-006: at $7500 all 10 hotels are affordable."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()

        df = at.dataframe[0].value
        # All ranks should be numeric (no "—")
        assert all(r != "—" for r in df["Rank"])
        captions = [c.value for c in at.caption]
        found = any(
            f"Affordable: {NUM_HOTELS} of {NUM_HOTELS}" in c for c in captions
        )
        assert found

    def test_aurora_ranking_after_budget_raise(self):
        """At $7500, AURORA has rank 1 (lowest weighted total)."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()

        df = at.dataframe[0].value
        aurora_row = df[df["Hotel"] == "Aurora Hotel"].iloc[0]
        assert aurora_row["Rank"] == "1"
        assert aurora_row["Status"] == "★ Recommended"

    def test_budget_does_not_change_contributions(self):
        """FR-010, EC-016: budget change does not change travel contributions."""
        at = _load_app()

        # Record weighted totals at initial budget
        df_initial = at.dataframe[0].value
        totals_initial = dict(
            zip(df_initial["Hotel"], df_initial["Wtd Total"])
        )

        # Change budget
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()

        df_new = at.dataframe[0].value
        totals_new = dict(zip(df_new["Hotel"], df_new["Wtd Total"]))

        # Weighted totals must be identical (budget doesn't affect travel)
        assert totals_initial == totals_new


# =========================================================================
# 4. No-Affordable-Hotel Scenario
# =========================================================================

class TestNoAffordableHotel:
    """When budget is too low, NO_AFFORDABLE_HOTEL is shown. (FR-009, AC-013)"""

    def test_no_affordable_warning(self):
        """FR-009: warning banner with NO_AFFORDABLE_HOTEL sentinel."""
        at = _load_app()
        # Set budget below cheapest hotel (Haven=$3500)
        at.number_input(key="budget_input").set_value(1000)
        at.run()

        assert not at.exception
        assert len(at.warning) >= 1
        warning_text = at.warning[0].value
        assert "NO_AFFORDABLE_HOTEL" in warning_text

    def test_no_recommendation_banner(self):
        """No success banner when no hotel is affordable."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(1000)
        at.run()

        assert len(at.success) == 0

    def test_all_hotels_over_budget(self):
        """All hotels show '—' rank and '✗ Over Budget' status."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(1000)
        at.run()

        df = at.dataframe[0].value
        assert all(r == "—" for r in df["Rank"])
        assert all("Over Budget" in s for s in df["Status"])

    def test_shortfalls_shown(self):
        """FR-008: budget shortfalls are displayed."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(1000)
        at.run()

        df = at.dataframe[0].value
        assert all("Over budget by" in b for b in df["Budget"])


# =========================================================================
# 5. Importance Changes
# =========================================================================

class TestImportanceChange:
    """Changing a place's importance recalculates everything. (FR-011)"""

    def test_tide_pools_change_flips_recommendation(self):
        """AC-007: TIDE_POOLS importance 3→4 changes rec from BREEZE to EMBER."""
        at = _load_app()

        # Change TIDE_POOLS importance from 3 to 4
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        assert not at.exception
        assert len(at.success) >= 1
        banner_text = at.success[0].value
        assert "Ember Suites" in banner_text

    def test_importance_change_updates_ranking_table(self):
        """FR-011: ranking table reflects the new recommendation."""
        at = _load_app()

        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        df = at.dataframe[0].value
        rank_1_row = df[df["Rank"] == "1"].iloc[0]
        assert "Ember" in rank_1_row["Hotel"]
        assert rank_1_row["Status"] == "★ Recommended"

    def test_importance_change_updates_importance_total(self):
        """FR-011: importance total in caption changes."""
        at = _load_app()

        # importance_total was 48; changing TIDE_POOLS 3→4 adds 1 → 49
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        captions = [c.value for c in at.caption]
        found = any(
            f"Importance total: {IMPORTANCE_TOTAL + 1}" in c for c in captions
        )
        assert found


# =========================================================================
# 6. Hotel Inspection
# =========================================================================

class TestHotelInspection:
    """Inspecting a hotel changes the detail view without recalculating."""

    def test_inspect_different_hotel(self):
        """FR-012: selecting a different hotel changes the detail display."""
        at = _load_app()

        # Initially inspecting BREEZE; switch to HAVEN
        at.selectbox(key="hotel_selector").select("HAVEN")
        at.run()

        assert not at.exception
        # The contribution detail tab should now show Haven
        # Check markdown header in detail tab
        markdowns = [m.value for m in at.markdown]
        found_haven = any("Haven Hostel" in m for m in markdowns)
        assert found_haven

    def test_inspect_does_not_change_ranking(self):
        """EC-018: inspection does not change ranking or recommendation."""
        at = _load_app()

        # Record the recommendation banner
        banner_before = at.success[0].value

        # Inspect a different hotel
        at.selectbox(key="hotel_selector").select("HAVEN")
        at.run()

        # Recommendation should be unchanged
        banner_after = at.success[0].value
        assert banner_before == banner_after

    def test_inspect_over_budget_hotel(self):
        """Inspecting an over-budget hotel shows its over-budget status."""
        at = _load_app()

        # AURORA is over budget at $5000
        at.selectbox(key="hotel_selector").select("AURORA")
        at.run()

        markdowns = [m.value for m in at.markdown]
        found_aurora = any("Aurora Hotel" in m for m in markdowns)
        found_over = any("Over budget by" in m for m in markdowns)
        assert found_aurora
        assert found_over

    def test_contribution_detail_metrics(self):
        """FR-013: contribution detail shows metrics for the inspected hotel."""
        at = _load_app()

        # Default is BREEZE
        metrics = at.metric
        # Should have Weighted Total, Weighted Average, Importance Total
        assert len(metrics) >= 3
        labels = [m.label for m in metrics]
        assert "Weighted Total" in labels
        assert "Weighted Average" in labels
        assert "Importance Total" in labels

    def test_contribution_detail_breeze_values(self):
        """Verify metric values for BREEZE (initial inspected hotel)."""
        at = _load_app()

        metrics = {m.label: m.value for m in at.metric}
        # BREEZE: wtd_total=1704, avg_tenths=355 → 35.5 min
        assert metrics["Weighted Total"] == "1,704"
        assert metrics["Weighted Average"] == "35.5 min"
        assert metrics["Importance Total"] == str(IMPORTANCE_TOTAL)

    def test_contribution_table_columns(self):
        """FR-013, FR-016: contribution table has the required columns."""
        at = _load_app()
        assert len(at.dataframe) >= 2
        contrib_df = at.dataframe[1].value
        required_cols = {"Place", "Type", "Importance",
                         "Round Trip (min)", "Contribution"}
        assert required_cols.issubset(set(contrib_df.columns))

    def test_contribution_table_has_15_rows(self):
        """FR-013: contribution table has one row per place."""
        at = _load_app()
        # The second dataframe is the contribution detail table
        assert len(at.dataframe) >= 2
        contrib_df = at.dataframe[1].value
        assert len(contrib_df) == NUM_PLACES


# =========================================================================
# 7. Reset
# =========================================================================

class TestReset:
    """Resetting restores the original scenario. (FR-018, AC-017)"""

    def test_reset_after_budget_change(self):
        """FR-018: reset after budget change restores original recommendation."""
        at = _load_app()

        # Change budget to make AURORA recommended
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()
        assert "Aurora Hotel" in at.success[0].value

        # Click Reset button (stable key)
        at.button(key="reset_btn").click()
        at.run()

        assert len(at.success) >= 1
        assert "Breeze Inn" in at.success[0].value

    def test_reset_after_importance_change(self):
        """FR-018: reset after importance change restores recommendation."""
        at = _load_app()

        # Change TIDE_POOLS importance → EMBER becomes recommended
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()
        assert "Ember Suites" in at.success[0].value

        # Click Reset button (stable key)
        at.button(key="reset_btn").click()
        at.run()

        assert len(at.success) >= 1
        assert "Breeze Inn" in at.success[0].value

    def test_reset_restores_budget_widget(self):
        """FR-018: reset restores the budget widget to initial value."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()

        # Reset (stable key)
        at.button(key="reset_btn").click()
        at.run()

        budget_val = at.number_input(key="budget_input").value
        assert budget_val == INITIAL_BUDGET

    def test_reset_restores_importance_sliders(self):
        """FR-018: reset restores importance sliders to original values."""
        at = _load_app()

        # TIDE_POOLS originally 3, change to 4
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        # Reset (stable key)
        at.button(key="reset_btn").click()
        at.run()

        slider_val = at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").value
        assert slider_val == 3  # original importance


# =========================================================================
# 8. Invalid Input Handling
# =========================================================================

class TestInvalidInput:
    """Invalid inputs show validation errors. (FR-020, FR-021, AC-014)"""

    def test_negative_budget_shows_error(self):
        """DR-007: negative budget is rejected with a validation error."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(-1)
        at.run()

        assert len(at.error) >= 1
        error_text = at.error[0].value
        assert "Budget" in error_text or "budget" in error_text

    def test_over_max_budget_shows_error(self):
        """DR-007: budget > 1,000,000 is rejected."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(1_000_001)
        at.run()

        assert len(at.error) >= 1

    def test_invalid_budget_clears_comparison(self):
        """FR-020: invalid input clears stale comparison results."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(-1)
        at.run()

        # No success banner, no ranking table data should appear
        assert len(at.success) == 0

    def test_invalid_budget_then_valid_recovers(self):
        """After fixing invalid budget, comparison results return."""
        at = _load_app()

        # Set invalid
        at.number_input(key="budget_input").set_value(-1)
        at.run()
        assert len(at.error) >= 1

        # Set valid
        at.number_input(key="budget_input").set_value(INITIAL_BUDGET)
        at.run()
        assert len(at.error) == 0
        assert len(at.success) >= 1

    def test_info_message_on_validation_error(self):
        """FR-021: an info message guides the user to fix or reset."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(-1)
        at.run()

        assert len(at.info) >= 1
        info_text = at.info[0].value
        assert "Reset" in info_text


# =========================================================================
# 9. Synchronisation Between Views
# =========================================================================

class TestViewSynchronisation:
    """Rankings, contribution detail, map, and state stay in sync."""

    def test_ranking_and_banner_agree_initially(self):
        """The ranking table rank-1 matches the recommendation banner."""
        at = _load_app()

        banner_text = at.success[0].value
        df = at.dataframe[0].value
        rank_1_hotel = df[df["Rank"] == "1"].iloc[0]["Hotel"]

        # Banner should mention the same hotel
        assert rank_1_hotel.split()[0] in banner_text  # e.g. "Breeze"

    def test_ranking_and_banner_agree_after_budget_change(self):
        """After budget change, ranking table and banner agree."""
        at = _load_app()
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()

        banner_text = at.success[0].value
        df = at.dataframe[0].value
        rank_1_hotel = df[df["Rank"] == "1"].iloc[0]["Hotel"]
        assert rank_1_hotel.split()[0] in banner_text

    def test_ranking_and_banner_agree_after_importance_change(self):
        """After importance change, ranking table and banner agree."""
        at = _load_app()
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        banner_text = at.success[0].value
        df = at.dataframe[0].value
        rank_1_hotel = df[df["Rank"] == "1"].iloc[0]["Hotel"]
        assert rank_1_hotel.split()[0] in banner_text

    def test_contribution_detail_matches_ranking(self):
        """The contribution detail's weighted total matches the ranking table."""
        at = _load_app()

        # BREEZE is inspected initially
        df = at.dataframe[0].value
        breeze_row = df[df["Hotel"] == "Breeze Inn"].iloc[0]
        ranking_wtd_total = breeze_row["Wtd Total"]

        # Metric shows weighted total
        metrics = {m.label: m.value for m in at.metric}
        detail_wtd_total = metrics["Weighted Total"]

        assert ranking_wtd_total == detail_wtd_total

    def test_over_budget_hotels_have_no_rank(self):
        """Over-budget hotels show '—' in rank column."""
        at = _load_app()
        df = at.dataframe[0].value

        # AURORA (cost=7500) is over budget at $5000
        aurora_row = df[df["Hotel"] == "Aurora Hotel"].iloc[0]
        assert aurora_row["Rank"] == "—"
        assert "Over Budget" in aurora_row["Status"]

    def test_affordable_hotels_ranked_consecutively(self):
        """Affordable hotels have consecutive ranks 1..N."""
        at = _load_app()
        df = at.dataframe[0].value

        ranked_rows = df[df["Rank"] != "—"]
        ranks = sorted([int(r) for r in ranked_rows["Rank"]])
        expected = list(range(1, AFFORDABLE_COUNT_INITIAL + 1))
        assert ranks == expected

    def test_ranking_order_initial(self):
        """Initial ranking order follows independently verified expected values."""
        at = _load_app()
        df = at.dataframe[0].value

        # Affordable hotels by rank: BREEZE(1), EMBER(2), CLIFF(3),
        # DUSK(4), JADE(5), HAVEN(6)
        ranked_df = df[df["Rank"] != "—"].sort_values(
            by="Rank", key=lambda s: s.astype(int)
        )
        hotel_order = list(ranked_df["Hotel"])
        expected_order = [
            "Breeze Inn", "Ember Suites", "Cliff Lodge",
            "Dusk Retreat", "Jade Villa", "Haven Hostel",
        ]
        assert hotel_order == expected_order

    def test_map_and_contribution_table_present(self):
        """Map (via Plotly) and contribution table are both rendered."""
        at = _load_app()
        # Map chart exists (best-effort via get workaround)
        charts = at.get("plotly_chart")
        assert len(charts) >= 1
        # Contribution table exists with all 15 places
        assert len(at.dataframe) >= 2
        assert len(at.dataframe[1].value) == NUM_PLACES

    def test_budget_widget_synced_after_importance_change(self):
        """Budget widget divergence fix: importance change syncs budget widget."""
        at = _load_app()

        # Verify initial budget
        assert at.number_input(key="budget_input").value == INITIAL_BUDGET

        # Change importance (should NOT change budget)
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        # Budget widget should still show 5000
        assert at.number_input(key="budget_input").value == INITIAL_BUDGET


# =========================================================================
# 10. Combined Flows
# =========================================================================

class TestCombinedFlows:
    """End-to-end flows combining multiple interactions."""

    def test_budget_then_importance_then_reset(self):
        """Full flow: change budget → change importance → reset."""
        at = _load_app()

        # Step 1: raise budget
        at.number_input(key="budget_input").set_value(BUDGET_ALL_AFFORDABLE)
        at.run()
        assert "Aurora Hotel" in at.success[0].value

        # Step 2: change importance
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()
        # Aurora may or may not still be rank-1, but results updated
        assert len(at.success) >= 1

        # Step 3: reset (stable key)
        at.button(key="reset_btn").click()
        at.run()
        assert len(at.success) >= 1
        assert "Breeze Inn" in at.success[0].value

    def test_inspect_then_importance_preserves_inspected(self):
        """EC-018: importance change does not change the inspected hotel."""
        at = _load_app()

        # Inspect HAVEN
        at.selectbox(key="hotel_selector").select("HAVEN")
        at.run()

        # Change importance
        at.slider(key=f"imp_{WHAT_IF_PLACE_ID}").set_value(
            WHAT_IF_NEW_IMPORTANCE
        )
        at.run()

        # HAVEN should still be inspected (its detail should be shown)
        markdowns = [m.value for m in at.markdown]
        found_haven = any("Haven Hostel" in m for m in markdowns)
        assert found_haven

    def test_no_affordable_then_raise_budget_recovers(self):
        """Flow: budget too low → raise budget → recommendation returns."""
        at = _load_app()

        # Set budget very low
        at.number_input(key="budget_input").set_value(1000)
        at.run()
        assert len(at.warning) >= 1
        assert "NO_AFFORDABLE_HOTEL" in at.warning[0].value

        # Raise budget
        at.number_input(key="budget_input").set_value(INITIAL_BUDGET)
        at.run()
        assert len(at.success) >= 1
        assert "Breeze Inn" in at.success[0].value

    def test_zero_budget_is_valid_but_no_affordable(self):
        """DR-007: budget=0 is valid but no hotel is affordable."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(0)
        at.run()

        assert len(at.error) == 0  # 0 is a valid budget
        assert len(at.warning) >= 1
        assert "NO_AFFORDABLE_HOTEL" in at.warning[0].value

    def test_max_budget_is_valid(self):
        """DR-007: budget=1,000,000 is valid."""
        at = _load_app()

        at.number_input(key="budget_input").set_value(1_000_000)
        at.run()

        assert len(at.error) == 0
        assert len(at.success) >= 1  # all hotels affordable at $1M
