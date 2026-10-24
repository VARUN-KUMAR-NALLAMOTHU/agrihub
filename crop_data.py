"""Static agronomy knowledge base used by the recommendation engine."""

SOILS = ["Alluvial", "Black", "Red", "Laterite", "Sandy", "Clay", "Loamy"]

CROPS = {
    "Rice": {
        "soils": ["Alluvial", "Clay", "Loamy"],
        "season": "Kharif (June - November)",
        "temp": (20, 35),
        "water": "High - keep 5 cm standing water during growth",
        "sowing": "Nursery sowing in June, transplant after 25-30 days",
        "fertilizer": "120 kg N, 60 kg P2O5, 40 kg K2O per hectare, N in 3 splits",
        "practices": [
            "Level the field and puddle before transplanting",
            "Use 20x15 cm spacing, 2-3 seedlings per hill",
            "Weed at 20 and 40 days after transplanting",
            "Drain the field 10 days before harvest",
        ],
    },
    "Wheat": {
        "soils": ["Alluvial", "Loamy", "Black", "Clay"],
        "season": "Rabi (November - April)",
        "temp": (10, 25),
        "water": "Medium - 4 to 6 irrigations at critical stages",
        "sowing": "Mid-November, seed rate 100 kg per hectare",
        "fertilizer": "120 kg N, 60 kg P2O5, 40 kg K2O per hectare",
        "practices": [
            "Irrigate at crown root initiation (21 days)",
            "Line sowing at 20-22 cm row spacing",
            "Control weeds with 2,4-D at 30-35 days",
            "Harvest when grains are hard and straw turns golden",
        ],
    },
    "Cotton": {
        "soils": ["Black", "Alluvial", "Red"],
        "season": "Kharif (May - December)",
        "temp": (21, 35),
        "water": "Medium - avoid waterlogging",
        "sowing": "May-June with pre-monsoon or first rains",
        "fertilizer": "80-100 kg N, 40 kg P2O5, 40 kg K2O per hectare",
        "practices": [
            "Space 90x60 cm for hybrids",
            "Scout for bollworm and whitefly every week",
            "Use pheromone traps and neem-based sprays first",
            "Pick bolls in 3-4 rounds when fully open",
        ],
    },
    "Sugarcane": {
        "soils": ["Alluvial", "Black", "Loamy", "Clay"],
        "season": "Year-round planting; main: Feb - March",
        "temp": (20, 35),
        "water": "High - irrigate every 7-10 days",
        "sowing": "Plant 3-budded setts in furrows",
        "fertilizer": "250 kg N, 80 kg P2O5, 120 kg K2O per hectare in splits",
        "practices": [
            "Treat setts with fungicide before planting",
            "Earth up at 90-120 days to prevent lodging",
            "Trash mulching conserves moisture",
            "Harvest at 10-12 months at peak sucrose",
        ],
    },
    "Maize": {
        "soils": ["Loamy", "Alluvial", "Red", "Sandy"],
        "season": "Kharif and Rabi",
        "temp": (18, 32),
        "water": "Medium - critical at tasseling and silking",
        "sowing": "60x20 cm spacing, 20 kg seed per hectare",
        "fertilizer": "120 kg N, 60 kg P2O5, 40 kg K2O per hectare",
        "practices": [
            "Ensure good drainage - maize hates waterlogging",
            "Earth up at knee-high stage",
            "Watch for fall armyworm and treat early",
            "Harvest when husks dry and grain moisture is ~20%",
        ],
    },
    "Groundnut": {
        "soils": ["Sandy", "Red", "Loamy", "Laterite"],
        "season": "Kharif (June - Oct) and Rabi (Nov - Feb)",
        "temp": (22, 33),
        "water": "Low to medium - pod development needs moisture",
        "sowing": "30x10 cm spacing, 100-120 kg kernels per hectare",
        "fertilizer": "20 kg N, 40 kg P2O5, 40 kg K2O + 500 kg gypsum per hectare",
        "practices": [
            "Apply gypsum at flowering for better pod filling",
            "Keep soil loose around pegging zone",
            "Rotate with cereals to cut disease build-up",
            "Harvest when leaves yellow and inner pod shell darkens",
        ],
    },
    "Millets": {
        "soils": ["Red", "Sandy", "Laterite", "Black"],
        "season": "Kharif (June - Sept)",
        "temp": (25, 35),
        "water": "Low - drought tolerant",
        "sowing": "Broadcast or line sow at onset of monsoon",
        "fertilizer": "40 kg N, 20 kg P2O5 per hectare",
        "practices": [
            "Thin plants 15 days after sowing",
            "One or two weedings are enough",
            "Excellent choice for rainfed and low-input farms",
            "Harvest when ear heads turn brown",
        ],
    },
    "Pulses": {
        "soils": ["Black", "Loamy", "Red", "Laterite"],
        "season": "Kharif (red gram) / Rabi (chickpea)",
        "temp": (20, 32),
        "water": "Low - sensitive to waterlogging",
        "sowing": "Seed treatment with Rhizobium before sowing",
        "fertilizer": "20 kg N, 50 kg P2O5 per hectare (starter dose only)",
        "practices": [
            "Rhizobium culture fixes nitrogen naturally",
            "Avoid excess irrigation at flowering",
            "Intercrop with cereals for risk reduction",
            "Control pod borer with pheromone traps",
        ],
    },
    "Tomato": {
        "soils": ["Loamy", "Red", "Sandy"],
        "season": "Year-round with protection; best Oct - Feb",
        "temp": (18, 30),
        "water": "Medium - light, frequent irrigation; drip is ideal",
        "sowing": "Raise seedlings in nursery 25-30 days, transplant",
        "fertilizer": "120 kg N, 80 kg P2O5, 60 kg K2O per hectare + FYM 25 t",
        "practices": [
            "Stake plants to keep fruits off the ground",
            "Mulch to hold moisture and suppress weeds",
            "Watch for early blight and leaf curl virus",
            "Harvest at breaker stage for transport",
        ],
    },
    "Chilli": {
        "soils": ["Red", "Black", "Loamy"],
        "season": "Kharif (June - Jan)",
        "temp": (20, 32),
        "water": "Medium - avoid water stress at flowering",
        "sowing": "Transplant 40-45 day seedlings at 60x45 cm",
        "fertilizer": "100 kg N, 50 kg P2O5, 50 kg K2O per hectare",
        "practices": [
            "Use well-drained soils to avoid root rot",
            "Control thrips and mites with neem oil",
            "Pick fully ripe red fruits in multiple pickings",
            "Sun-dry on clean surface to keep colour",
        ],
    },
}


def recommend(soil: str, crop: str, temp_c=None):
    """Return a recommendation dict for a soil/crop pair, optionally weather-aware."""
    info = CROPS.get(crop)
    if not info or soil not in SOILS:
        return None

    suitable = soil in info["soils"]
    alternatives = [c for c, d in CROPS.items() if soil in d["soils"] and c != crop]

    notes = []
    if temp_c is not None:
        lo, hi = info["temp"]
        if temp_c < lo:
            notes.append(f"Current temperature ({temp_c:.0f} °C) is below the ideal {lo}-{hi} °C range for {crop}. Consider delaying sowing or using mulch/covers.")
        elif temp_c > hi:
            notes.append(f"Current temperature ({temp_c:.0f} °C) is above the ideal {lo}-{hi} °C range for {crop}. Irrigate in the evening and consider shade nets or mulching.")
        else:
            notes.append(f"Current temperature ({temp_c:.0f} °C) is within the ideal {lo}-{hi} °C range for {crop}.")

    return {
        "soil": soil,
        "crop": crop,
        "suitable": suitable,
        "verdict": (
            f"{crop} grows well in {soil} soil."
            if suitable
            else f"{crop} is not the best match for {soil} soil. Yields may suffer without amendments."
        ),
        "season": info["season"],
        "water": info["water"],
        "sowing": info["sowing"],
        "fertilizer": info["fertilizer"],
        "practices": info["practices"],
        "weather_notes": notes,
        "alternatives": alternatives[:5],
    }


# Earth-tone colour for each soil: (background, text colour). Used by the strata UI.
SOIL_COLORS = {
    "Alluvial": ("#cdb48a", "#2a2216"),
    "Black":    ("#2b2724", "#f1ece4"),
    "Red":      ("#a5482e", "#fff4ec"),
    "Laterite": ("#b8703f", "#1f1408"),
    "Sandy":    ("#e6d4a4", "#2a2216"),
    "Clay":     ("#8b6b55", "#fff4ec"),
    "Loamy":    ("#6a4d38", "#fff4ec"),
}


def soil_crops():
    """Map each soil to the crops that suit it."""
    return {s: [c for c, d in CROPS.items() if s in d["soils"]] for s in SOILS}
