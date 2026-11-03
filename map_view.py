"""Schematic city map visualisation for the Hotel Base-Camp Comparator.

This module creates a Plotly figure showing all hotel and wishlist-place
markers on a schematic map, with comparison links highlighting the
inspected hotel's connections to every place.

Coordinates are used solely for marker positioning and link drawing.
Travel times, contributions, and rankings are read from the supplied
comparison results — never derived from map geometry.

Reference: REQUIREMENTS.md (FR-014, FR-015, FR-016, FR-017,
           NFR-003, NFR-005, DR-013)
"""

from __future__ import annotations

import plotly.graph_objects as go

from models import ComparisonResult, PlaceType, TripScenario


# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------

# Colours
_CLR_RECOMMENDED = "#FFB300"   # Amber/gold — rank-1 hotel
_CLR_AFFORDABLE  = "#1976D2"   # Blue — other affordable hotels
_CLR_OVER_BUDGET = "#9E9E9E"   # Grey — over-budget hotels
_CLR_ATTRACTION  = "#E65100"   # Deep orange — attraction places
_CLR_FOOD        = "#2E7D32"   # Green — food places
_CLR_LINK_LINE   = "#90CAF9"   # Light blue — comparison link lines
_CLR_BACKGROUND  = "#FAFAFA"   # Light grey map background

# Marker symbols
_SYM_HOTEL      = "square"
_SYM_ATTRACTION = "hexagram"   # Six-pointed star
_SYM_FOOD       = "diamond"

# Marker sizes
_SZ_RECOMMENDED = 16           # Larger for the recommended hotel
_SZ_HOTEL       = 12
_SZ_PLACE       = 11
_SZ_LINK_HOVER  = 18           # Invisible hover target at link midpoints

# Line width
_LW_LINK = 1.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_city_map(
    scenario: TripScenario,
    comparison: ComparisonResult,
    inspected_hotel_id: str,
) -> go.Figure:
    """Create the schematic city map as a Plotly figure.

    Parameters
    ----------
    scenario : TripScenario
        The current scenario with hotels, places, and coordinates.
    comparison : ComparisonResult
        Calculated comparison results (contributions, ranks, affordability).
    inspected_hotel_id : str
        ID of the currently inspected hotel whose 15 comparison links
        are highlighted on the map (FR-015).

    Returns
    -------
    go.Figure
        A Plotly figure with 25 labelled markers (10 hotels + 15 places)
        and exactly 15 highlighted comparison links for the inspected hotel.
    """
    fig = go.Figure()

    # Look up inspected hotel and its calculated results
    inspected_hotel = next(
        h for h in scenario.hotels if h.hotel_id == inspected_hotel_id
    )
    inspected_result = comparison.hotel_results[inspected_hotel_id]

    # 1. Comparison links — drawn first so markers appear on top (FR-015)
    _add_comparison_links(fig, inspected_hotel, scenario, inspected_result)

    # 2. Wishlist-place markers (FR-014)
    _add_place_markers(fig, scenario)

    # 3. Hotel markers with status indicators (FR-014, FR-017)
    _add_hotel_markers(fig, scenario, comparison)

    # 4. Layout configuration (NFR-005)
    _configure_layout(fig, scenario.city_name)

    return fig


# ---------------------------------------------------------------------------
# Comparison links  (FR-015, AC-009)
# ---------------------------------------------------------------------------

def _add_comparison_links(
    fig: go.Figure,
    inspected_hotel,
    scenario: TripScenario,
    inspected_result,
) -> None:
    """Add exactly 15 comparison links from the inspected hotel to all places.

    Each link is drawn as a line from the hotel's coordinates to the
    place's coordinates.  An invisible marker at the midpoint of each
    link provides a hover target showing:
    - Place name
    - Round-trip time (from the hotel's travel-time mapping)
    - Weighted contribution (from the comparison result)

    Values are read from the existing data — never calculated from
    coordinate distances (NFR-003, DR-013).
    """
    hx, hy = inspected_hotel.x, inspected_hotel.y

    line_x: list[float | None] = []
    line_y: list[float | None] = []
    mid_x: list[float] = []
    mid_y: list[float] = []
    hover_texts: list[str] = []

    for place in scenario.places:
        px, py = place.x, place.y
        travel_time = inspected_hotel.round_trip_minutes[place.place_id]
        contribution = inspected_result.contributions[place.place_id]

        # Line segment: hotel → place, separated by None
        line_x.extend([hx, px, None])
        line_y.extend([hy, py, None])

        # Midpoint for hover target
        mid_x.append((hx + px) / 2)
        mid_y.append((hy + py) / 2)
        hover_texts.append(
            f"<b>{place.name}</b><br>"
            f"Round trip: {travel_time} min<br>"
            f"Contribution: {contribution}"
        )

    # Link lines (hover is handled by midpoint markers, not the lines)
    fig.add_trace(go.Scatter(
        x=line_x,
        y=line_y,
        mode="lines",
        line=dict(color=_CLR_LINK_LINE, width=_LW_LINK),
        hoverinfo="skip",
        showlegend=True,
        name="Comparison Links",
        legendgroup="links",
    ))

    # Invisible midpoint markers carrying hover information
    fig.add_trace(go.Scatter(
        x=mid_x,
        y=mid_y,
        mode="markers",
        marker=dict(size=_SZ_LINK_HOVER, color="rgba(0,0,0,0)"),
        hoverinfo="text",
        hovertext=hover_texts,
        showlegend=False,
        legendgroup="links",
    ))


# ---------------------------------------------------------------------------
# Place markers  (FR-014, AC-009)
# ---------------------------------------------------------------------------

def _add_place_markers(fig: go.Figure, scenario: TripScenario) -> None:
    """Add labelled markers for all wishlist places, grouped by type.

    Attractions and food places use different symbols and colours so
    they are visually distinguishable (FR-014).
    """
    attractions = [
        p for p in scenario.places if p.place_type == PlaceType.ATTRACTION
    ]
    food_places = [
        p for p in scenario.places if p.place_type == PlaceType.FOOD
    ]

    if attractions:
        fig.add_trace(go.Scatter(
            x=[p.x for p in attractions],
            y=[p.y for p in attractions],
            mode="markers+text",
            marker=dict(
                symbol=_SYM_ATTRACTION,
                size=_SZ_PLACE,
                color=_CLR_ATTRACTION,
                line=dict(width=1, color="#BF360C"),
            ),
            text=[p.name for p in attractions],
            textposition="top center",
            textfont=dict(size=9, color=_CLR_ATTRACTION),
            hoverinfo="text",
            hovertext=[
                f"<b>{p.name}</b><br>"
                f"Type: Attraction<br>"
                f"Importance: {p.importance}"
                for p in attractions
            ],
            name="Attractions",
            legendgroup="attractions",
        ))

    if food_places:
        fig.add_trace(go.Scatter(
            x=[p.x for p in food_places],
            y=[p.y for p in food_places],
            mode="markers+text",
            marker=dict(
                symbol=_SYM_FOOD,
                size=_SZ_PLACE,
                color=_CLR_FOOD,
                line=dict(width=1, color="#1B5E20"),
            ),
            text=[p.name for p in food_places],
            textposition="top center",
            textfont=dict(size=9, color=_CLR_FOOD),
            hoverinfo="text",
            hovertext=[
                f"<b>{p.name}</b><br>"
                f"Type: Food<br>"
                f"Importance: {p.importance}"
                for p in food_places
            ],
            name="Food Places",
            legendgroup="food",
        ))


# ---------------------------------------------------------------------------
# Hotel markers  (FR-014, FR-017, AC-009, AC-010)
# ---------------------------------------------------------------------------

def _add_hotel_markers(
    fig: go.Figure,
    scenario: TripScenario,
    comparison: ComparisonResult,
) -> None:
    """Add labelled markers for all hotels, grouped by status.

    FR-017 requires text or symbols — not colour alone — to distinguish
    the recommended hotel from excluded (over-budget) hotels:

    - ★ prefix + gold marker  → recommended hotel (rank-1)
    - Blue marker (no prefix) → other affordable hotels
    - ✗ prefix + grey marker  → over-budget hotels
    """
    recommended_id = comparison.recommended_hotel_id

    rec_hotels: list[tuple] = []
    aff_hotels: list[tuple] = []
    ovr_hotels: list[tuple] = []

    for hotel in scenario.hotels:
        result = comparison.hotel_results[hotel.hotel_id]
        if hotel.hotel_id == recommended_id:
            rec_hotels.append((hotel, result))
        elif result.is_affordable:
            aff_hotels.append((hotel, result))
        else:
            ovr_hotels.append((hotel, result))

    # Recommended hotel — ★ prefix, larger gold marker
    if rec_hotels:
        _add_hotel_group(
            fig,
            rec_hotels,
            name="★ Recommended",
            color=_CLR_RECOMMENDED,
            border_color="#F57F17",
            size=_SZ_RECOMMENDED,
            label_prefix="★ ",
            currency=scenario.currency,
        )

    # Other affordable hotels — blue marker, no prefix
    if aff_hotels:
        _add_hotel_group(
            fig,
            aff_hotels,
            name="Affordable Hotels",
            color=_CLR_AFFORDABLE,
            border_color="#0D47A1",
            size=_SZ_HOTEL,
            label_prefix="",
            currency=scenario.currency,
        )

    # Over-budget hotels — ✗ prefix, grey marker
    if ovr_hotels:
        _add_hotel_group(
            fig,
            ovr_hotels,
            name="✗ Over Budget",
            color=_CLR_OVER_BUDGET,
            border_color="#616161",
            size=_SZ_HOTEL,
            label_prefix="✗ ",
            currency=scenario.currency,
        )


def _add_hotel_group(
    fig: go.Figure,
    hotels_with_results: list[tuple],
    *,
    name: str,
    color: str,
    border_color: str,
    size: int,
    label_prefix: str,
    currency: str,
) -> None:
    """Add a single Scatter trace for a group of hotels sharing a status.

    Hover text shows the hotel name, stay cost, rank or shortfall,
    and weighted average travel time.
    """
    hover_texts: list[str] = []
    for hotel, result in hotels_with_results:
        if result.rank is not None:
            status = f"Rank: {result.rank}"
        else:
            status = (
                f"Over budget by {currency}"
                f"{abs(result.remaining_budget):,}"
            )
        avg_display = result.weighted_average_tenths / 10
        hover_texts.append(
            f"<b>{hotel.name}</b><br>"
            f"Stay cost: {currency}{hotel.stay_cost:,}<br>"
            f"{status}<br>"
            f"Wtd avg: {avg_display:.1f} min"
        )

    fig.add_trace(go.Scatter(
        x=[h.x for h, _ in hotels_with_results],
        y=[h.y for h, _ in hotels_with_results],
        mode="markers+text",
        marker=dict(
            symbol=_SYM_HOTEL,
            size=size,
            color=color,
            line=dict(width=1.5, color=border_color),
        ),
        text=[
            f"{label_prefix}{h.name}" for h, _ in hotels_with_results
        ],
        textposition="bottom center",
        textfont=dict(size=10, color=color),
        hoverinfo="text",
        hovertext=hover_texts,
        name=name,
    ))


# ---------------------------------------------------------------------------
# Layout  (NFR-005)
# ---------------------------------------------------------------------------

def _configure_layout(fig: go.Figure, city_name: str) -> None:
    """Configure the figure layout for a clean schematic map.

    Axes are hidden since this is a schematic visualisation, not a
    geographic map (NFR-005).  The y-axis is reversed because the
    scenario coordinates use a top-left origin.
    """
    fig.update_layout(
        title=dict(
            text=f"🗺️ {city_name} — Schematic Map",
            font=dict(size=18),
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
            autorange="reversed",
            scaleanchor="x",
            scaleratio=1,
        ),
        plot_bgcolor=_CLR_BACKGROUND,
        paper_bgcolor="white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(l=20, r=20, t=80, b=20),
        hovermode="closest",
        height=600,
    )
