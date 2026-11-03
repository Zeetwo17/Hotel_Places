# DOMAIN_MODEL.md — Hotel Base-Camp Comparator

## Overview

The domain model consists of **two enums** and **six dataclasses** defined in [`models.py`](file:///c:/Users/Lenovo/Desktop/cisco/models.py). These are plain data containers with no validation or calculation logic.

---

## Enums

### PlaceType

| Value | String |
|---|---|
| `ATTRACTION` | `"attraction"` |
| `FOOD` | `"food"` |

Represents the two allowed types of wishlist place (DR-005).

### ComparisonOutcome

| Value | String |
|---|---|
| `RECOMMENDATION_AVAILABLE` | `"recommendation_available"` |
| `NO_AFFORDABLE_HOTEL` | `"no_affordable_hotel"` |

Represents the overall outcome of a comparison — either a recommendation exists (FR-007) or no hotel is affordable (FR-009).

---

## Dataclasses

### Place

| Field | Type | Description |
|---|---|---|
| `place_id` | `str` | Unique ID matching `[A-Z][A-Z0-9_-]{0,15}` (DR-009) |
| `name` | `str` | Display name, non-empty after trimming (DR-010) |
| `place_type` | `PlaceType` | `ATTRACTION` or `FOOD` (DR-005) |
| `importance` | `int` | Whole number 1–5 (DR-005) |
| `x` | `float` | Horizontal marker position on the schematic map |
| `y` | `float` | Vertical marker position on the schematic map |

### Hotel

| Field | Type | Description |
|---|---|---|
| `hotel_id` | `str` | Unique ID matching `[A-Z][A-Z0-9_-]{0,15}` (DR-009) |
| `name` | `str` | Display name, non-empty after trimming (DR-010) |
| `stay_cost` | `int` | Complete-stay price, whole number 1–1,000,000 (DR-006) |
| `round_trip_minutes` | `dict[str, int]` | Maps each place ID to its round-trip time in minutes 1–600 (DR-011, DR-012) |
| `x` | `float` | Horizontal marker position on the schematic map |
| `y` | `float` | Vertical marker position on the schematic map |

### TripScenario

| Field | Type | Description |
|---|---|---|
| `city_name` | `str` | Name of the fictional city |
| `currency` | `str` | Currency used consistently across all prices and budget (DR-008) |
| `budget` | `int` | Complete-stay budget, whole number 0–1,000,000 (DR-007) |
| `hotels` | `list[Hotel]` | 2–10 hotels in the scenario (DR-001) |
| `places` | `list[Place]` | 3–15 wishlist places in the scenario (DR-001) |

### HotelComparisonResult

| Field | Type | Description |
|---|---|---|
| `hotel_id` | `str` | ID of the hotel this result belongs to |
| `contributions` | `dict[str, int]` | Maps each place ID to its contribution: `importance × round_trip_minutes` (FR-002) |
| `weighted_travel_total` | `int` | Sum of all contributions (FR-003) |
| `weighted_average_tenths` | `int` | Weighted average displayed as tenths: `floor((20 × total + imp_total) / (2 × imp_total))`. Display as `weighted_average_tenths / 10` for one decimal place with round-half-up (FR-004) |
| `is_affordable` | `bool` | `True` when `stay_cost ≤ budget` (FR-005) |
| `remaining_budget` | `int` | `budget − stay_cost`. Positive = under budget, negative = over budget (FR-008) |
| `rank` | `int \| None` | Consecutive rank starting at 1 for affordable hotels, `None` for over-budget (FR-007, FR-008) |

### ComparisonResult

| Field | Type | Description |
|---|---|---|
| `importance_total` | `int` | Sum of all place importance values, used as the divisor in weighted average (FR-004) |
| `hotel_results` | `dict[str, HotelComparisonResult]` | Maps each hotel ID to its comparison result |
| `recommended_hotel_id` | `str \| None` | Hotel ID of rank-1 hotel, or `None` when no hotel is affordable (FR-007, FR-009) |
| `outcome` | `ComparisonOutcome` | `RECOMMENDATION_AVAILABLE` or `NO_AFFORDABLE_HOTEL` (FR-007, FR-009) |

### AppState

| Field | Type | Default | Description |
|---|---|---|---|
| `scenario` | `TripScenario \| None` | `None` | Current working scenario (may have modified budget/importance) |
| `initial_scenario` | `TripScenario \| None` | `None` | Original scenario snapshot for reset (FR-018) |
| `comparison` | `ComparisonResult \| None` | `None` | Current comparison result, cleared on invalid input (FR-020) |
| `validation_issues` | `list[str]` | `[]` | Field-specific validation error messages (FR-020, FR-021) |
| `inspected_hotel_id` | `str \| None` | `None` | Currently inspected hotel (FR-012) |
| `default_inspected_hotel_id` | `str \| None` | `None` | Initial rank-1 hotel ID, restored on reset (FR-018, AC-017) |

---

## Field relationship summary

```
TripScenario
├── hotels[]
│   └── round_trip_minutes  ──keys must match──►  places[].place_id
└── places[]

ComparisonResult
├── hotel_results{}  ──keyed by──►  hotels[].hotel_id
│   └── contributions{}  ──keyed by──►  places[].place_id
└── recommended_hotel_id  ──references──►  hotels[].hotel_id

AppState
├── scenario  ──is a──►  TripScenario (working copy)
├── initial_scenario  ──is a──►  TripScenario (reset snapshot)
├── comparison  ──is a──►  ComparisonResult
├── inspected_hotel_id  ──references──►  hotels[].hotel_id
└── default_inspected_hotel_id  ──references──►  hotels[].hotel_id
```
