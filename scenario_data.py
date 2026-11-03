"""Main scenario data for the Hotel Base-Camp Comparator.

City: Starfall Bay (fictional)
Currency: $
Initial Budget: $5,000
Hotels: 10
Places: 15 (8 attractions, 7 food)
Importance total: 48

Key scenario properties (see REQUIREMENTS.md acceptance criteria):
- 6 affordable hotels at the initial budget (AC-002)
- AURORA has the unique lowest weighted total but is over budget (AC-003)
- BREEZE is the initial recommendation (rank-1), HAVEN is cheapest affordable (AC-004)
- BREEZE has all round trips ≤ 90 min; EMBER has a trip > 90 min (AC-005)
- Raising budget to $7,500 (AURORA's cost) makes AURORA the recommendation (AC-006)
- Changing TIDE_POOLS importance from 3 to 4 changes recommendation
  from BREEZE to EMBER (AC-007)
- EMBER's weighted average (36.25) exercises round-half-up display (FR-004)

Default inspected hotel: BREEZE (initial rank-1)
"""

from models import Hotel, Place, PlaceType, TripScenario


CITY_NAME = "Starfall Bay"
CURRENCY = "$"
INITIAL_BUDGET = 5000

# AC-007: changing this place's importance flips the recommendation
WHAT_IF_PLACE_ID = "TIDE_POOLS"
WHAT_IF_ORIGINAL_IMPORTANCE = 3
WHAT_IF_CHANGED_IMPORTANCE = 4
# Original recommendation: BREEZE → After change: EMBER

DEFAULT_INSPECTED_HOTEL_ID = "BREEZE"


def create_places() -> list[Place]:
    """Create the 15 wishlist places for Starfall Bay."""
    return [
        # ---- Attractions (8) ----
        Place("CRYSTAL_CAVE", "Crystal Cave", PlaceType.ATTRACTION, 5, 80, 80),
        Place("SUNSET_PEAK", "Sunset Peak", PlaceType.ATTRACTION, 5, 820, 60),
        Place("OLD_LIGHT", "Old Lighthouse", PlaceType.ATTRACTION, 4, 40, 280),
        Place("DRAGON_BRIDGE", "Dragon Bridge", PlaceType.ATTRACTION, 4, 540, 40),
        Place("STAR_MUSEUM", "Star Museum", PlaceType.ATTRACTION, 4, 780, 180),
        Place("CLOUD_GARDEN", "Cloud Garden", PlaceType.ATTRACTION, 3, 380, 240),
        Place("TIDE_POOLS", "Tide Pools", PlaceType.ATTRACTION, 3, 180, 140),
        Place("WIND_TOWER", "Wind Tower", PlaceType.ATTRACTION, 2, 880, 380),
        # ---- Food (7) ----
        Place("HARBOR_GRILL", "Harbor Grill", PlaceType.FOOD, 4, 280, 340),
        Place("SPICE_MARKET", "Spice Market", PlaceType.FOOD, 3, 560, 380),
        Place("MOON_BAKERY", "Moon Bakery", PlaceType.FOOD, 3, 680, 440),
        Place("FIRE_KITCHEN", "Fire Kitchen", PlaceType.FOOD, 3, 80, 400),
        Place("CORAL_CAFE", "Coral Cafe", PlaceType.FOOD, 2, 460, 480),
        Place("DUNE_DINER", "Dune Diner", PlaceType.FOOD, 2, 780, 480),
        Place("PEARL_BISTRO", "Pearl Bistro", PlaceType.FOOD, 1, 220, 480),
    ]


def create_hotels() -> list[Hotel]:
    """Create the 10 hotels for Starfall Bay."""
    return [
        Hotel("AURORA", "Aurora Hotel", 7500, {
            "CRYSTAL_CAVE": 25, "SUNSET_PEAK": 28, "OLD_LIGHT": 30,
            "DRAGON_BRIDGE": 22, "STAR_MUSEUM": 32, "CLOUD_GARDEN": 28,
            "TIDE_POOLS": 18, "WIND_TOWER": 38, "HARBOR_GRILL": 25,
            "SPICE_MARKET": 30, "MOON_BAKERY": 32, "FIRE_KITCHEN": 26,
            "CORAL_CAFE": 34, "DUNE_DINER": 30, "PEARL_BISTRO": 42,
        }, 480, 80),
        Hotel("BREEZE", "Breeze Inn", 4800, {
            "CRYSTAL_CAVE": 28, "SUNSET_PEAK": 30, "OLD_LIGHT": 33,
            "DRAGON_BRIDGE": 26, "STAR_MUSEUM": 36, "CLOUD_GARDEN": 30,
            "TIDE_POOLS": 75, "WIND_TOWER": 48, "HARBOR_GRILL": 30,
            "SPICE_MARKET": 33, "MOON_BAKERY": 36, "FIRE_KITCHEN": 30,
            "CORAL_CAFE": 42, "DUNE_DINER": 35, "PEARL_BISTRO": 52,
        }, 280, 180),
        Hotel("CLIFF", "Cliff Lodge", 4200, {
            "CRYSTAL_CAVE": 35, "SUNSET_PEAK": 38, "OLD_LIGHT": 40,
            "DRAGON_BRIDGE": 35, "STAR_MUSEUM": 42, "CLOUD_GARDEN": 38,
            "TIDE_POOLS": 35, "WIND_TOWER": 60, "HARBOR_GRILL": 36,
            "SPICE_MARKET": 40, "MOON_BAKERY": 42, "FIRE_KITCHEN": 36,
            "CORAL_CAFE": 50, "DUNE_DINER": 42, "PEARL_BISTRO": 58,
        }, 680, 220),
        Hotel("DUSK", "Dusk Retreat", 4500, {
            "CRYSTAL_CAVE": 40, "SUNSET_PEAK": 42, "OLD_LIGHT": 44,
            "DRAGON_BRIDGE": 38, "STAR_MUSEUM": 46, "CLOUD_GARDEN": 38,
            "TIDE_POOLS": 36, "WIND_TOWER": 62, "HARBOR_GRILL": 40,
            "SPICE_MARKET": 40, "MOON_BAKERY": 42, "FIRE_KITCHEN": 40,
            "CORAL_CAFE": 52, "DUNE_DINER": 44, "PEARL_BISTRO": 60,
        }, 180, 340),
        Hotel("EMBER", "Ember Suites", 3900, {
            "CRYSTAL_CAVE": 26, "SUNSET_PEAK": 28, "OLD_LIGHT": 35,
            "DRAGON_BRIDGE": 30, "STAR_MUSEUM": 38, "CLOUD_GARDEN": 32,
            "TIDE_POOLS": 22, "WIND_TOWER": 92, "HARBOR_GRILL": 32,
            "SPICE_MARKET": 40, "MOON_BAKERY": 38, "FIRE_KITCHEN": 35,
            "CORAL_CAFE": 55, "DUNE_DINER": 45, "PEARL_BISTRO": 45,
        }, 520, 280),
        Hotel("FROST", "Frost Palace", 6200, {
            "CRYSTAL_CAVE": 28, "SUNSET_PEAK": 30, "OLD_LIGHT": 32,
            "DRAGON_BRIDGE": 25, "STAR_MUSEUM": 35, "CLOUD_GARDEN": 30,
            "TIDE_POOLS": 22, "WIND_TOWER": 42, "HARBOR_GRILL": 28,
            "SPICE_MARKET": 32, "MOON_BAKERY": 35, "FIRE_KITCHEN": 28,
            "CORAL_CAFE": 38, "DUNE_DINER": 32, "PEARL_BISTRO": 65,
        }, 380, 120),
        Hotel("GALE", "Gale Tower", 5800, {
            "CRYSTAL_CAVE": 30, "SUNSET_PEAK": 32, "OLD_LIGHT": 34,
            "DRAGON_BRIDGE": 28, "STAR_MUSEUM": 36, "CLOUD_GARDEN": 32,
            "TIDE_POOLS": 25, "WIND_TOWER": 45, "HARBOR_GRILL": 30,
            "SPICE_MARKET": 34, "MOON_BAKERY": 36, "FIRE_KITCHEN": 30,
            "CORAL_CAFE": 40, "DUNE_DINER": 34, "PEARL_BISTRO": 48,
        }, 620, 120),
        Hotel("HAVEN", "Haven Hostel", 3500, {
            "CRYSTAL_CAVE": 48, "SUNSET_PEAK": 52, "OLD_LIGHT": 50,
            "DRAGON_BRIDGE": 45, "STAR_MUSEUM": 52, "CLOUD_GARDEN": 48,
            "TIDE_POOLS": 45, "WIND_TOWER": 75, "HARBOR_GRILL": 50,
            "SPICE_MARKET": 52, "MOON_BAKERY": 55, "FIRE_KITCHEN": 48,
            "CORAL_CAFE": 62, "DUNE_DINER": 55, "PEARL_BISTRO": 70,
        }, 120, 460),
        Hotel("IVORY", "Ivory House", 5500, {
            "CRYSTAL_CAVE": 32, "SUNSET_PEAK": 35, "OLD_LIGHT": 36,
            "DRAGON_BRIDGE": 30, "STAR_MUSEUM": 38, "CLOUD_GARDEN": 34,
            "TIDE_POOLS": 28, "WIND_TOWER": 50, "HARBOR_GRILL": 33,
            "SPICE_MARKET": 36, "MOON_BAKERY": 38, "FIRE_KITCHEN": 32,
            "CORAL_CAFE": 42, "DUNE_DINER": 36, "PEARL_BISTRO": 52,
        }, 740, 320),
        Hotel("JADE", "Jade Villa", 4600, {
            "CRYSTAL_CAVE": 40, "SUNSET_PEAK": 42, "OLD_LIGHT": 44,
            "DRAGON_BRIDGE": 38, "STAR_MUSEUM": 46, "CLOUD_GARDEN": 42,
            "TIDE_POOLS": 40, "WIND_TOWER": 65, "HARBOR_GRILL": 42,
            "SPICE_MARKET": 44, "MOON_BAKERY": 44, "FIRE_KITCHEN": 40,
            "CORAL_CAFE": 56, "DUNE_DINER": 48, "PEARL_BISTRO": 62,
        }, 420, 400),
    ]


def create_main_scenario() -> TripScenario:
    """Create the main demonstration scenario for Starfall Bay."""
    return TripScenario(
        city_name=CITY_NAME,
        currency=CURRENCY,
        budget=INITIAL_BUDGET,
        hotels=create_hotels(),
        places=create_places(),
    )
