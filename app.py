"""Streamlit application for the Hotel Base-Camp Comparator.

This module implements the user interface, connecting sidebar controls
and main-area views to the existing state management (state.py),
calculation engine (calculations.py), and map visualisation (map_view.py).

No calculation or state-management logic is duplicated here — every user
interaction delegates to the approved functions in state.py.

Reference: REQUIREMENTS.md, USER_FLOWS.md
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from models import ComparisonOutcome, PlaceType
from state import (
    initialize_state,
    load_scenario,
    update_budget,
    update_importance,
    inspect_hotel,
    reset_scenario,
)
from map_view import create_city_map


# ---------------------------------------------------------------------------
# Page configuration (must be the first Streamlit command)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Hotel Base-Camp Comparator",
    page_icon="🏨",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------

if "app_state" not in st.session_state:
    st.session_state.app_state = initialize_state()

_state = st.session_state.app_state


# ---------------------------------------------------------------------------
# Callbacks  (all delegate to state.py — no calculations here)
# ---------------------------------------------------------------------------

def _sync_widgets() -> None:
    """Push current app-state values into widget session-state keys.

    Called after load and reset so that every widget reflects the
    restored scenario data on the next render.
    """
    st.session_state.budget_input = _state.scenario.budget
    for place in _state.scenario.places:
        st.session_state[f"imp_{place.place_id}"] = place.importance
    st.session_state.hotel_selector = _state.inspected_hotel_id


def _on_load() -> None:
    """Load Scenario button. (FR-001, USER_FLOWS Flow 1)"""
    load_scenario(_state)
    _sync_widgets()


def _on_reset() -> None:
    """Reset button. (FR-018, AC-017, USER_FLOWS Flow 2 — Reset)"""
    reset_scenario(_state)
    _sync_widgets()


def _on_budget_change() -> None:
    """Budget input changed. (FR-010, FR-021, USER_FLOWS Flow 2 — Change Budget)

    Streamlit's number_input may return a float (e.g. 500.5) when the
    user types a non-integer.  We pass the raw value to update_budget
    so that the isinstance(budget, int) check in state.py fires and
    the user sees the proper validation error (FR-021, AC-014).
    """
    raw = st.session_state.budget_input
    # Detect non-integer floats and let state.py reject them (DR-007)
    if isinstance(raw, float) and raw != int(raw):
        update_budget(_state, raw)  # type: ignore[arg-type]
    else:
        update_budget(_state, int(raw))


def _on_importance_change(place_id: str) -> None:
    """Importance slider changed. (FR-011, USER_FLOWS Flow 2 — Change Importance)"""
    update_importance(
        _state, place_id, int(st.session_state[f"imp_{place_id}"])
    )
    # Sync budget widget back to the scenario's current budget so that
    # a stale invalid value does not persist in the widget after a
    # successful importance recalculation (budget widget divergence fix).
    if _state.scenario is not None and not _state.validation_issues:
        st.session_state.budget_input = _state.scenario.budget


def _on_hotel_select() -> None:
    """Hotel selector changed. (FR-012, USER_FLOWS Flow 2 — Inspect Hotel)"""
    inspect_hotel(_state, st.session_state.hotel_selector)


# ---------------------------------------------------------------------------
# Pre-load view  (empty workspace — scenario not yet loaded)
# ---------------------------------------------------------------------------

if _state.scenario is None:
    st.title("🏨 Hotel Base-Camp Comparator")
    st.markdown(
        "Compare hotels by total stay cost and weighted round-trip "
        "travel times to your wishlist of places in a fictional city."
    )
    st.divider()
    _, centre, _ = st.columns([1, 2, 1])
    with centre:
        st.button(
            "📥  Load Scenario",
            on_click=_on_load,
            type="primary",
            use_container_width=True,
        )
        st.caption("Loads the Starfall Bay scenario with 10 hotels and 15 places.")
    st.stop()


# =========================================================================
# Post-load: everything below runs only when a scenario is loaded
# =========================================================================

currency = _state.scenario.currency
hotel_id_to_name = {h.hotel_id: h.name for h in _state.scenario.hotels}


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

with st.sidebar:
    # -- City header --
    st.header(f"🗺️ {_state.scenario.city_name}")
    st.caption(
        f"Currency: {currency}  ·  "
        f"Hotels: {len(_state.scenario.hotels)}  ·  "
        f"Places: {len(_state.scenario.places)}"
    )

    st.divider()

    # -- Budget input (FR-010, FR-021) --
    # No min_value / max_value so the user can enter out-of-range values
    # and see validation errors (FR-021, AC-014).
    st.subheader(f"Budget ({currency})")
    st.number_input(
        "Budget",
        step=100,
        key="budget_input",
        on_change=_on_budget_change,
        label_visibility="collapsed",
        help="Complete hotel-stay budget. Valid range: 0 – 1,000,000.",
    )

    st.divider()

    # -- Action buttons --
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        st.button("🔄 Reset", on_click=_on_reset, use_container_width=True, key="reset_btn")
    with bcol2:
        st.button("📥 Reload", on_click=_on_load, use_container_width=True)

    st.divider()

    # -- Hotel inspection selector (FR-012) --
    st.subheader("Inspect Hotel")
    st.selectbox(
        "Select hotel to inspect",
        options=list(hotel_id_to_name.keys()),
        format_func=lambda hid: hotel_id_to_name[hid],
        key="hotel_selector",
        on_change=_on_hotel_select,
        label_visibility="collapsed",
    )

    st.divider()

    # -- Place importance sliders (FR-011) --
    st.subheader("Place Importance")
    with st.expander("Adjust importance values", expanded=False):
        for place in _state.scenario.places:
            icon = "🏛️" if place.place_type == PlaceType.ATTRACTION else "🍽️"
            st.slider(
                f"{icon} {place.name}",
                min_value=1,
                max_value=5,
                key=f"imp_{place.place_id}",
                on_change=_on_importance_change,
                args=(place.place_id,),
            )


# ---------------------------------------------------------------------------
# Main content — title
# ---------------------------------------------------------------------------

st.title("🏨 Hotel Base-Camp Comparator")


# ---------------------------------------------------------------------------
# Validation errors  (FR-020, FR-021, AC-014)
# ---------------------------------------------------------------------------

if _state.validation_issues:
    for issue in _state.validation_issues:
        st.error(f"⚠️ {issue}")
    st.info(
        "Fix the validation errors above to see comparison results.  "
        "Use **Reset** to restore the original scenario."
    )
    st.stop()

if _state.comparison is None:
    st.warning("No comparison results available.")
    st.stop()

comparison = _state.comparison


# ---------------------------------------------------------------------------
# Outcome banner  (FR-007, FR-009, FR-017, AC-010)
# ---------------------------------------------------------------------------

if comparison.outcome == ComparisonOutcome.RECOMMENDATION_AVAILABLE:
    rec_id = comparison.recommended_hotel_id
    rec_hotel = next(h for h in _state.scenario.hotels if h.hotel_id == rec_id)
    rec_result = comparison.hotel_results[rec_id]
    avg_rec = rec_result.weighted_average_tenths / 10
    st.success(
        f"★ **Recommended: {rec_hotel.name}**  ·  "
        f"Stay: {currency}{rec_hotel.stay_cost:,}  ·  "
        f"Wtd avg: {avg_rec:.1f} min  ·  "
        f"Remaining: {currency}{rec_result.remaining_budget:,}"
    )
else:
    st.warning(
        f"⚠️ **NO_AFFORDABLE_HOTEL** — No affordable hotel at the current "
        f"budget of {currency}{_state.scenario.budget:,}. "
        "All hotels exceed the budget. Shortfalls are shown below."
    )


# ---------------------------------------------------------------------------
# Schematic map  (FR-014, FR-015, FR-016, NFR-005)
# ---------------------------------------------------------------------------

st.plotly_chart(
    create_city_map(_state.scenario, comparison, _state.inspected_hotel_id),
    use_container_width=True,
    key="city_map",
)


# ---------------------------------------------------------------------------
# Tabs: Hotel Ranking + Contribution Detail
# ---------------------------------------------------------------------------

tab_ranking, tab_detail = st.tabs(["🏆 Hotel Ranking", "🔍 Contribution Detail"])


# ---- Tab 1: Hotel Ranking  (FR-006 – FR-008, FR-017, AC-010) ----

with tab_ranking:
    ranking_rows: list[dict] = []

    for hotel in _state.scenario.hotels:
        result = comparison.hotel_results[hotel.hotel_id]

        # Rank and status text  (FR-017: text/symbols, not colour alone)
        if result.rank is not None:
            rank_display = str(result.rank)
            status = "★ Recommended" if result.rank == 1 else "Affordable"
        else:
            rank_display = "—"
            status = "✗ Over Budget"

        avg = result.weighted_average_tenths / 10

        # Budget column
        if result.remaining_budget >= 0:
            budget_col = f"+{currency}{result.remaining_budget:,}"
        else:
            budget_col = (
                f"Over budget by {currency}{abs(result.remaining_budget):,}"
            )

        ranking_rows.append({
            "Rank": rank_display,
            "Status": status,
            "Hotel": hotel.name,
            "Stay Cost": f"{currency}{hotel.stay_cost:,}",
            "Wtd Total": f"{result.weighted_travel_total:,}",
            "Wtd Avg": f"{avg:.1f} min",
            "Budget": budget_col,
        })

    # Affordable hotels first (by rank), then over-budget
    ranking_rows.sort(
        key=lambda r: (
            r["Rank"] == "—",
            int(r["Rank"]) if r["Rank"] != "—" else 999,
        )
    )

    st.dataframe(
        pd.DataFrame(ranking_rows),
        use_container_width=True,
        hide_index=True,
    )

    affordable_count = sum(
        1 for r in comparison.hotel_results.values() if r.is_affordable
    )
    st.caption(
        f"Affordable: {affordable_count} of {len(comparison.hotel_results)} "
        f"hotels  ·  Importance total: {comparison.importance_total}"
    )


# ---- Tab 2: Contribution Detail  (FR-013, FR-016) ----

with tab_detail:
    inspected_id = _state.inspected_hotel_id
    inspected_name = hotel_id_to_name.get(inspected_id, inspected_id)
    inspected_result = comparison.hotel_results[inspected_id]
    inspected_hotel_obj = next(
        h for h in _state.scenario.hotels if h.hotel_id == inspected_id
    )

    # Hotel summary line
    avg_insp = inspected_result.weighted_average_tenths / 10
    if inspected_result.is_affordable:
        status_line = f"Rank {inspected_result.rank}"
    else:
        status_line = (
            f"✗ Over budget by "
            f"{currency}{abs(inspected_result.remaining_budget):,}"
        )

    st.markdown(
        f"### {inspected_name}\n"
        f"Stay: {currency}{inspected_hotel_obj.stay_cost:,}  ·  {status_line}"
    )

    # Per-place contribution table
    contrib_rows: list[dict] = []
    for place in _state.scenario.places:
        travel_time = inspected_hotel_obj.round_trip_minutes[place.place_id]
        contribution = inspected_result.contributions[place.place_id]
        icon = "🏛️" if place.place_type == PlaceType.ATTRACTION else "🍽️"
        contrib_rows.append({
            "Place": f"{icon} {place.name}",
            "Type": place.place_type.value.title(),
            "Importance": place.importance,
            "Round Trip (min)": travel_time,
            "Contribution": contribution,
        })

    st.dataframe(
        pd.DataFrame(contrib_rows),
        use_container_width=True,
        hide_index=True,
    )

    # Contribution bar chart  (FR-011, FR-016 — "chart")
    place_names = [r["Place"] for r in contrib_rows]
    contributions = [r["Contribution"] for r in contrib_rows]
    bar_colors = [
        "#636EFA" if r["Type"] == "Attraction" else "#EF553B"
        for r in contrib_rows
    ]

    fig_contrib = go.Figure(go.Bar(
        y=place_names,
        x=contributions,
        orientation="h",
        marker_color=bar_colors,
        text=contributions,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Contribution: %{x}<extra></extra>",
    ))
    fig_contrib.update_layout(
        title=f"Per-Place Contributions — {inspected_name}",
        xaxis_title="Contribution (importance × round-trip min)",
        yaxis=dict(autorange="reversed"),  # keep same order as table
        height=max(400, len(place_names) * 28),
        margin=dict(l=10, r=30, t=40, b=40),
    )
    st.plotly_chart(fig_contrib, use_container_width=True, key="contrib_chart")

    # Summary metrics
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.metric("Weighted Total", f"{inspected_result.weighted_travel_total:,}")
    with mcol2:
        st.metric("Weighted Average", f"{avg_insp:.1f} min")
    with mcol3:
        st.metric("Importance Total", f"{comparison.importance_total}")
