# REQUIREMENTS.md — Hotel Base-Camp Comparator

## 1. Purpose and scope

This document converts the supplied **SPR26_D2_P03: Hotel Base-Camp Comparator** problem statement into verifiable requirements. The supplied problem statement is the source of truth. No additional product features or technical design decisions are introduced here.

The project is a local, interactive **hotel base-camp comparison tool**. It compares complete-stay hotel prices and supplied round-trip travel times to a fixed wishlist of places. It is **not** an itinerary planner or a route-finding tool.

**Out of scope:** choosing wishlist places, arranging days, finding routes or roads, estimating admission/meal/transport costs, accounts, databases, live maps, geocoding, hotel booking, traffic services, and external APIs.

Requirement IDs are unique within this document. “Required” and “Optional” reflect the wording of the problem statement; open questions are listed separately rather than silently resolved.

## 2. Functional requirements (FR)

| ID | Requirement | Verification |
|---|---|---|
| FR-001 | The user must be able to load the fictional city and its trip data in one action. | Load the main scenario and confirm that the comparison is populated. |
| FR-002 | The application must calculate each hotel’s contribution for every wishlist place as `importance × round_trip_minutes`. | Check contributions for selected hotel/place pairs against the formula. |
| FR-003 | The application must calculate each hotel’s weighted travel total as the sum of all place contributions. | Recalculate the sum independently and compare it with the displayed total. |
| FR-004 | The application must calculate each hotel’s weighted average travel time as `weighted_travel_total / importance_total`, where `importance_total` is the sum of all place importance values, and display it to one decimal place using round-half-up. The stated integer-only display equivalent is `rounded_tenths = floor((20 × weighted_travel_total + importance_total) / (2 × importance_total))`, then display `rounded_tenths / 10`. | Check displayed averages, including a value that exercises a half-up rounding case. |
| FR-005 | A hotel must be considered affordable exactly when its complete-stay `stay_cost` is less than or equal to the current budget. | Test a hotel at the budget boundary and one unit above it. |
| FR-006 | Affordable hotels must be ranked by: (1) exact weighted travel total ascending, (2) stay cost ascending, and (3) hotel ID in ascending ASCII order. | Test ordinary ranking, each tie-break, and totals whose displayed averages round to the same value. |
| FR-007 | Affordable hotels must receive consecutive, unique ranks beginning at 1. Rank 1 must be the single recommended hotel. | Confirm ranks have no gaps or duplicates and exactly one rank-1 result exists when at least one hotel is affordable. |
| FR-008 | An over-budget hotel must remain visible, show `Over budget by X`, have no numerical rank, and never be recommended. | Inspect an over-budget hotel in the results. |
| FR-009 | When no hotel is affordable, the application must show `NO_AFFORDABLE_HOTEL`, retain each hotel’s shortfall, and show neither a recommendation nor numerical ranks. This is a valid comparison result, not a validation error. | Set a budget below every hotel’s stay cost and inspect the result. |
| FR-010 | The user must be able to change the budget. The application must recalculate affordability, shortfalls, ranks, and recommendation. Travel contributions must remain unchanged when only the budget changes. | Record contributions, change only the budget, and compare the contributions and updated eligibility/ranking. |
| FR-011 | The user must be able to change a place’s importance within the allowed range. The application must recalculate every affected contribution, weighted total, average, rank, and relevant chart or link label. | Change one importance value and verify the updated calculations and presentation. |
| FR-012 | The user must be able to inspect any hotel. Inspection must show that hotel’s explanation and its comparison links without changing the baseline ranking result. | Inspect multiple hotels and confirm the ranks and recommendation do not change merely because the inspected hotel changes. |
| FR-013 | When a hotel is inspected, the application must expose the supplied round-trip time and weighted contribution for each of the 15 wishlist places. | Inspect a hotel and verify all 15 place-level values. |
| FR-014 | The schematic map must display all 10 hotel markers and all 15 wishlist-place markers for the main scenario, with labels. | Count and inspect all 25 labelled markers. |
| FR-015 | The map must highlight only the 15 comparison links belonging to the currently inspected hotel. These links represent comparisons, not calculated roads or routes. | Inspect a hotel and confirm only its 15 links are highlighted. |
| FR-016 | The map must stay synchronized with an accessible hotel-by-place time table or an equivalent view, ranked hotel cards or rows, eligibility reasons, and contribution details or a chart. | Compare the selected hotel, times, contributions, and ranking across the views. |
| FR-017 | The interface must use text or symbols as well as colour to identify the recommended hotel and excluded hotels. | Check that status remains understandable without relying on colour alone. |
| FR-018 | The user must be able to reset the trip. Reset must restore all candidate-created city data, the original budget and importance values, the documented recommendation, and the default inspected hotel. | Change budget and importance, inspect another hotel, reset, and compare with the initial state. |
| FR-019 | The application must validate the complete scenario before producing a ranking. It must not produce a partial ranking from records that happen to look valid. | Introduce a structural validation error and confirm no partial ranking is shown. |
| FR-020 | An invalid result must identify the problem and clear stale ranks, recommendation, contributions, and derived map highlights. | First produce a valid result, then introduce an invalid editable or structural value and confirm all stale derived results are cleared. |
| FR-021 | The visible application must demonstrate invalid handling for an editable budget or importance value. | Enter an out-of-range budget or importance and observe the validation result. |

## 3. Non-functional requirements (NFR)

| ID | Requirement | Verification |
|---|---|---|
| NFR-001 | Processing must remain local. The solution must not depend on external APIs or services listed as out of scope in Section 1. | Run the application without relying on those services. |
| NFR-002 | The main scenario and its travel-time matrix must be deterministic. The same stable 10-by-15 matrix must be present on every reset. | Reset repeatedly and compare the complete matrix. |
| NFR-003 | Travel times, accessibility, and ranking must not be derived from map pixel positions, marker distance, or line length. | Compare the calculation inputs with the supplied matrix; confirm map position is not used as a calculation input. |
| NFR-004 | The comparison workspace must make the cost/accessibility trade-off and the selected hotel’s calculation clear. | Review the main scenario and confirm that the cost, budget, ranking, and contribution explanation can be understood together. |
| NFR-005 | The map must be a clear schematic visualisation of the fictional city, not a live map or route display. | Inspect the map and confirm it displays markers and comparison links only. |
| NFR-006 | Expected results must be checked independently of the application’s ranking calculation. Documented expected answers must not be used as ranking inputs. | Compare application output with separately calculated expected results and inspect the calculation inputs. |

## 4. Data requirements and validation constraints (DR)

| ID | Requirement / constraint | Verification |
|---|---|---|
| DR-001 | The calculation engine must support **2–10 hotels** and **3–15 wishlist places**. | Test the supported minimum and maximum counts, and reject counts outside the ranges. |
| DR-002 | The main demonstration scenario must contain exactly **10 hotels** and **15 wishlist places**. | Count the main scenario records. |
| DR-003 | The main scenario must include at least three `attraction` places and at least three `food` places. | Count places by type. |
| DR-004 | The main scenario must use at least three different place-importance values. | Count distinct importance values in the main scenario. |
| DR-005 | Each place must have a type of `attraction` or `food` and a whole-number importance from **1 through 5**. | Validate valid boundary values and reject unsupported types, non-whole numbers, and out-of-range values. |
| DR-006 | Each hotel must have a whole-number `stay_cost` from **1 through 1,000,000**, representing the quoted price for the complete stay. | Validate the minimum and maximum values and reject values outside the range or not whole numbers. |
| DR-007 | `budget` must be a whole-number amount from **0 through 1,000,000**, representing the budget for the complete hotel stay, not a nightly allowance. | Validate the minimum and maximum values and reject values outside the range or not whole numbers. |
| DR-008 | One currency must be used consistently throughout the scenario and its displayed prices/budget. | Inspect all displayed monetary values and scenario data for a consistent currency. |
| DR-009 | Hotel and place IDs must be unique across the complete scenario and match `[A-Z][A-Z0-9_-]{0,15}`. | Test valid IDs, malformed IDs, and collisions between hotel IDs and place IDs. |
| DR-010 | Every display name must remain non-empty after surrounding whitespace is removed. | Test empty, whitespace-only, and valid names. |
| DR-011 | Each hotel must contain a `round_trip_minutes` mapping whose keys match **exactly** the IDs of all wishlist places. Missing and unknown place IDs are invalid. | Test a complete mapping, a missing key, and an extra/unknown key. |
| DR-012 | Each round-trip time must be a whole number from **1 through 600** minutes. It represents the complete hotel-to-place-to-hotel time. | Test boundary values and reject zero, values above 600, and non-whole numbers. |
| DR-013 | Marker positions are presentation data only. They must not be treated as travel-time or accessibility data. | Verify that changing a marker position does not change calculated results. |
| DR-014 | The candidate must create the fictional city, demonstration data, test data, memorable place names, and marker positions; no starter asset is supplied. | Inspect the completed scenario and confirm the required data is present. |
| DR-015 | The travel-time matrix may be stored as constants or generated deterministically, but the same stable matrix must be materialized and inspected after every reset. | Compare the matrix before and after repeated resets. |
| DR-016 | Independently document each main-scenario hotel’s expected weighted total, one-decimal average, affordability, shortfall or remaining budget, and initial rank. | Compare the independent record with the application output for all 10 hotels. |

## 5. Acceptance criteria (AC)

The following are required acceptance checks unless marked optional. Each criterion is intended to be demonstrated with application behaviour, documented values, or repeatable test evidence.

| ID | Acceptance criterion | Verifiable condition |
|---|---|---|
| AC-001 | Main scenario can be loaded in one action. | Exactly 10 hotels, 15 places, at least three places of each type, at least three distinct importance values, and a complete 10-by-15 travel-time mapping are loaded. |
| AC-002 | Initial affordability story is satisfied. | At the initial budget, exactly 4–7 hotels are affordable. |
| AC-003 | The unique most-accessible hotel is initially over budget. | The hotel with the unique lowest exact weighted travel total is not affordable at the initial budget. |
| AC-004 | The initial recommendation is not the cheapest affordable hotel. | The rank-1 affordable hotel and the lowest-cost affordable hotel have different IDs. |
| AC-005 | The 90-minute travel-time contrast is represented. | At least one affordable hotel has every round trip at or below 90 minutes, and at least one other affordable hotel has one or more round trips above 90 minutes. |
| AC-006 | Increasing the budget changes the recommendation at the required boundary. | When the budget is raised to the complete-stay cost of the unique most-accessible hotel, that hotel becomes the recommendation. |
| AC-007 | An importance “what if” changes the recommendation. | For one selected place, a documented importance value within 1–5 changes the recommended affordable hotel from the initial recommendation. |
| AC-008 | Main-scenario expected results are independently documented. | All 10 hotels have documented expected weighted total, one-decimal average, affordability, shortfall or remaining budget, and initial rank; the application matches these values without using them as calculation input. |
| AC-009 | All map and comparison details are visible. | All 25 labelled markers are shown; only the inspected hotel’s 15 links are highlighted; each link exposes its supplied round-trip time and contribution. |
| AC-010 | Hotel costs, eligibility, ranking, and exclusions are explained. | Complete-stay price comparison, ranked results, and a clear reason for each unranked hotel are visible. |
| AC-011 | Budget-boundary behaviour is correct. | A hotel exactly at the budget is affordable; a hotel one currency unit over budget is unranked. |
| AC-012 | Both ranking tie-breaks are correct. | Equal weighted totals are ordered by stay cost; when both weighted total and stay cost tie, hotel ID in ascending ASCII order decides the order. Smaller candidate-authored test scenarios may be used. |
| AC-013 | No-affordable-hotel behaviour is correct. | When all hotels exceed the budget, `NO_AFFORDABLE_HOTEL` is shown, shortfalls remain visible, and no stale recommendation or numerical rank is displayed. |
| AC-014 | Invalid editable input is rejected visibly. | An invalid budget or importance is identified and stale derived results are cleared. |
| AC-015 | Structural invalid data is rejected. | Repeatable test evidence rejects at least one duplicate-ID case and at least one incomplete or unknown travel-time mapping. |
| AC-016 | Focused calculation and interaction checks exist. | Evidence covers contribution arithmetic, round-half-up display, exact ranking when displayed averages round alike, both tie-breaks, budget equality, budget changes, importance changes, invalid-state clearing, the no-affordable result, hotel inspection, and reset. |
| AC-017 | Reset restores the documented initial scenario. | After the required changes, reset restores all original data, budget, importance values, recommendation, and default inspected hotel. |
| AC-018 | Project planning and presentation can be explained. | A short plan with 3–5 ordered steps and useful checkpoints is available; changes from that plan can be explained. |
| AC-019 | AI-assisted work can be discussed. | Relevant prompts, design constraints provided to AI assistants, and examples of how AI recommendations influenced decisions can be presented. |
| AC-020 | Testing and solution presentation can be demonstrated. | The working solution and test evidence—such as tests, screenshots, or output samples—can be shown and explained. |
| AC-021 | A small live change can be made. | The development environment is ready to implement and verify one small modification, and possibly a second if time permits, using AI assistance. |
| AC-OPT-001 | Optional budget timeline. | If included, it shows the budget amounts at which the recommendation changes and preserves the same affordability and ranking rules. |

## 6. Edge cases and failure scenarios (EC)

| ID | Scenario | Required outcome / related requirements |
|---|---|---|
| EC-001 | Hotel count below 2 or above 10; place count below 3 or above 15. | Reject the invalid scenario before ranking. (DR-001, FR-019) |
| EC-002 | Main demonstration has other than 10 hotels or 15 places. | Main scenario does not meet acceptance. (DR-002, AC-001) |
| EC-003 | Duplicate ID, malformed ID, or an ID collision between a hotel and a place. | Reject the complete scenario. (DR-009, FR-019) |
| EC-004 | Name is empty or contains only surrounding whitespace. | Reject the complete scenario. (DR-010, FR-019) |
| EC-005 | Place type is unsupported, importance is not a whole number, or importance is outside 1–5. | Reject the complete scenario or invalid edit; do not retain stale results. (DR-005, FR-020, FR-021) |
| EC-006 | Stay cost is not a whole number or is outside 1–1,000,000. | Reject the complete scenario. (DR-006, FR-019) |
| EC-007 | Budget is not a whole number or is outside 0–1,000,000. | Identify the invalid editable value and clear stale derived results. (DR-007, FR-020, FR-021) |
| EC-008 | A hotel’s travel-time mapping omits a place ID or includes an unknown place ID. | Reject the complete scenario; do not calculate a partial ranking. (DR-011, FR-019) |
| EC-009 | A round-trip time is not a whole number or is outside 1–600 minutes. | Reject the complete scenario. (DR-012, FR-019) |
| EC-010 | Hotel stay cost equals the budget. | Treat the hotel as affordable. (FR-005, AC-011) |
| EC-011 | Hotel stay cost is one currency unit above the budget. | Keep it visible as over budget, show the shortfall, and assign no rank. (FR-008, AC-011) |
| EC-012 | No hotel is affordable. | Show `NO_AFFORDABLE_HOTEL`, retain shortfalls, and show no recommendation or numerical ranks. Do not classify this as invalid data. (FR-009, AC-013) |
| EC-013 | Two affordable hotels have equal weighted travel totals but different stay costs. | Lower stay cost ranks first. (FR-006, AC-012) |
| EC-014 | Two affordable hotels have equal weighted totals and equal stay costs. | Lower hotel ID in ascending ASCII order ranks first. (FR-006, AC-012) |
| EC-015 | Different exact weighted totals produce the same one-decimal displayed average. | Rank by exact weighted total, not the rounded display value. (FR-006, FR-007, AC-016) |
| EC-016 | Budget changes while importance and travel times remain unchanged. | Affordability, shortfalls, ranks, and recommendation may change; contributions must not change. (FR-010) |
| EC-017 | Importance changes. | Contributions, totals, averages, ranks, and relevant chart/link labels must be recalculated. (FR-011) |
| EC-018 | User inspects a different hotel. | Only the visible explanation and highlighted comparison links change; the ranking result does not. (FR-012, FR-015) |
| EC-019 | Invalid data is entered after a valid result was displayed. | Stale ranks, recommendation, contributions, and derived map highlights must be cleared. (FR-020) |
| EC-020 | User resets after changing budget, importance, or inspected hotel. | All original scenario values and the default inspected hotel are restored. (FR-018) |
| EC-021 | The map is moved or marker positions are changed. | Travel times, accessibility totals, and ranking remain unchanged. (NFR-003, DR-013) |
| EC-022 | Scenario is reset repeatedly. | The same deterministic travel-time matrix is restored each time. (NFR-002, DR-015) |

## 7. Dependencies, ambiguities, and potential conflicts

### 7.1 Requirement dependencies

| ID | Dependency | Notes |
|---|---|---|
| DEP-001 | Valid city/trip data is a prerequisite for calculation and ranking. | Counts, IDs, names, place types, importance values, costs, budget, and complete travel-time mappings must pass validation before derived results are produced. (DR-001–DR-012, FR-019) |
| DEP-002 | Contributions depend on place importance and supplied round-trip times. | Weighted totals and averages depend on all place contributions. (FR-002–FR-004) |
| DEP-003 | Affordability depends on the current budget and each hotel’s complete-stay cost. | Ranking applies only to affordable hotels. (FR-005–FR-009) |
| DEP-004 | The ranking depends on exact weighted totals, stay costs, and hotel IDs. | Display rounding and map positions are not ranking inputs. (FR-006, NFR-003) |
| DEP-005 | Hotel inspection depends on the currently selected hotel. | It controls the visible explanation and highlighted links, but not the baseline ranking. (FR-012–FR-015) |
| DEP-006 | Reset depends on the original candidate-created scenario values being known. | The original data, budget, importance values, documented recommendation, and default inspected hotel must all be restorable. (FR-018) |
| DEP-007 | Independent expected results depend on the completed main scenario but must remain separate from application ranking inputs. | The expected totals and order are used for verification only. (NFR-006, DR-016) |
| DEP-008 | Tie-break, no-affordable, and structural-validation demonstrations may use smaller candidate-authored test scenarios. | These tests do not replace the required 10-hotel/15-place main demonstration. (AC-012, AC-013, AC-015) |

### 7.2 Ambiguities to resolve while preparing the scenario

These details are not specified numerically in the problem statement. The candidate is expected to create the fictional data, but should document the chosen values rather than treating them as supplied facts.

| ID | Ambiguity / open detail | What needs to be recorded or clarified |
|---|---|---|
| AMB-001 | The fictional city, hotel names, place names, IDs, and marker positions are not provided. | Candidate-created values are required; no particular real-world city or names are mandated. |
| AMB-002 | The currency is not specified. | Select one currency and use it consistently. |
| AMB-003 | The initial budget and the 10 complete-stay hotel costs are not specified. | Record the selected values and demonstrate that all main-scenario story conditions are met. |
| AMB-004 | The initial importance values for the 15 places are not specified. | Record all initial values and ensure at least three distinct values are used. |
| AMB-005 | The place whose importance changes, and its changed value, are not specified. | Record the place ID, original importance, changed importance, and resulting alternative recommendation. |
| AMB-006 | The default inspected hotel after load/reset is not specified. | Select and document one default hotel. |
| AMB-007 | The exact independent expected results are not supplied. | Calculate and record every hotel’s weighted total, one-decimal average, affordability, shortfall/remaining budget, and initial rank independently. |
| AMB-008 | The phrase “accessible hotel-by-place time table” does not define a specific accessibility standard. | Clarify whether this means a readily available/easy-to-read view or whether formal accessibility support is expected. No formal standard is named in the problem statement. |
| AMB-009 | “Attractive,” “familiar technology,” and “equally clear visual map” are qualitative and have no measurable thresholds. | Use reasonable judgement and be prepared to explain the presentation choices; do not treat a particular visual style or technology as mandated. |
| AMB-010 | The required error message format and level of detail are not specified beyond identifying the problem and clearing stale results. | Decide how errors are worded and displayed while ensuring the invalid condition is identifiable. |
| AMB-011 | The problem does not prescribe a specific format for the independent expected-results record or test evidence. | Choose a reviewable format and ensure every required value and test case can be checked. |

### 7.3 Potential requirement tensions (not contradictions)

| ID | Potential tension | Interpretation grounded in the problem statement |
|---|---|---|
| CON-001 | The engine supports variable counts, while the main demonstration has fixed counts. | Support the stated ranges in the calculation engine; use exactly 10 hotels and 15 places in the main scenario. |
| CON-002 | The map shows all 25 markers, but only one hotel’s links should be highlighted. | Keep all markers visible and limit highlighted links to the currently inspected hotel’s 15 comparisons. |
| CON-003 | The over-budget hotel with the best accessibility must be visible but must not be recommended initially. | Accessibility totals can be calculated for all valid hotels, but only affordable hotels receive ranks or can be recommended. |
| CON-004 | An invalid scenario and a valid scenario with no affordable hotels must not look like the same failure. | Invalid data is rejected and stale derived results are cleared; a valid no-affordable result uses `NO_AFFORDABLE_HOTEL` and retains shortfalls. |
| CON-005 | The displayed average is rounded, but ranking must be exact. | Use the exact integer weighted total for sorting; rounding is only for display. |
| CON-006 | Changing budget can change ranks, but it must not change travel contributions. | Budget affects affordability and the resulting eligible ranking only; importance and travel times determine contributions. |

## 8. Explicitly unspecified items

The problem statement does not define performance targets, browser support, mobile layout behaviour, persistence across sessions, user accounts, formal accessibility standards, security requirements, deployment/hosting, or a required programming language/framework. These are **not included as requirements** in this document unless separately clarified by the project evaluator.
