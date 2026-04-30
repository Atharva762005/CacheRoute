"""
India Circle Rates — IGR/Guidance Value Data
Cities: Pune, Mumbai, Bangalore
Source: State registration authority ready-reckoner 2024-25
"""

# ── Pune ───────────────────────────────────────────────────────────────────
PUNE_RATES = {
    "Koregaon Park":  {"zone_tier": "prime",      "city": "Pune", "lat": 18.5362, "lon": 73.8938, "residential_apartment": 12500, "residential_plot": 18000, "commercial_shop": 22000, "commercial_office": 16000, "industrial": 8000},
    "Shivajinagar":   {"zone_tier": "prime",      "city": "Pune", "lat": 18.5308, "lon": 73.8474, "residential_apartment": 13000, "residential_plot": 19000, "commercial_shop": 24000, "commercial_office": 17000, "industrial": 9000},
    "Baner":          {"zone_tier": "prime",      "city": "Pune", "lat": 18.5590, "lon": 73.7868, "residential_apartment": 10800, "residential_plot": 14000, "commercial_shop": 18000, "commercial_office": 13500, "industrial": 6500},
    "Kothrud":        {"zone_tier": "prime",      "city": "Pune", "lat": 18.5074, "lon": 73.8077, "residential_apartment": 11200, "residential_plot": 15000, "commercial_shop": 19000, "commercial_office": 14000, "industrial": 7000},
    "Aundh":          {"zone_tier": "prime",      "city": "Pune", "lat": 18.5578, "lon": 73.8073, "residential_apartment": 11500, "residential_plot": 15500, "commercial_shop": 20000, "commercial_office": 14500, "industrial": 7500},
    "Viman Nagar":    {"zone_tier": "prime",      "city": "Pune", "lat": 18.5679, "lon": 73.9143, "residential_apartment": 10500, "residential_plot": 14500, "commercial_shop": 18500, "commercial_office": 13000, "industrial": 6800},
    "Wakad":          {"zone_tier": "mid",        "city": "Pune", "lat": 18.5975, "lon": 73.7614, "residential_apartment": 8200,  "residential_plot": 10500, "commercial_shop": 13000, "commercial_office": 10000, "industrial": 5500},
    "Hinjewadi":      {"zone_tier": "mid",        "city": "Pune", "lat": 18.5912, "lon": 73.7380, "residential_apartment": 7800,  "residential_plot": 9800,  "commercial_shop": 12000, "commercial_office": 9500,  "industrial": 5800},
    "Hadapsar":       {"zone_tier": "mid",        "city": "Pune", "lat": 18.5018, "lon": 73.9260, "residential_apartment": 7200,  "residential_plot": 9000,  "commercial_shop": 11500, "commercial_office": 9000,  "industrial": 5200},
    "Pimpri":         {"zone_tier": "mid",        "city": "Pune", "lat": 18.6279, "lon": 73.7997, "residential_apartment": 7500,  "residential_plot": 9500,  "commercial_shop": 12500, "commercial_office": 9800,  "industrial": 5600},
    "Chinchwad":      {"zone_tier": "mid",        "city": "Pune", "lat": 18.6436, "lon": 73.7983, "residential_apartment": 7800,  "residential_plot": 10000, "commercial_shop": 13000, "commercial_office": 10000, "industrial": 5800},
    "Katraj":         {"zone_tier": "mid",        "city": "Pune", "lat": 18.4601, "lon": 73.8669, "residential_apartment": 6800,  "residential_plot": 8500,  "commercial_shop": 11000, "commercial_office": 8500,  "industrial": 4800},
    "Wagholi":        {"zone_tier": "peripheral", "city": "Pune", "lat": 18.5617, "lon": 73.9757, "residential_apartment": 5500,  "residential_plot": 7000,  "commercial_shop": 9000,  "commercial_office": 7000,  "industrial": 4000},
    "Talegaon":       {"zone_tier": "peripheral", "city": "Pune", "lat": 18.7332, "lon": 73.6723, "residential_apartment": 4800,  "residential_plot": 6200,  "commercial_shop": 8000,  "commercial_office": 6000,  "industrial": 3500},
    "Chakan":         {"zone_tier": "peripheral", "city": "Pune", "lat": 18.7601, "lon": 73.8637, "residential_apartment": 4500,  "residential_plot": 5800,  "commercial_shop": 7500,  "commercial_office": 5500,  "industrial": 4500},
    "Ambegaon":       {"zone_tier": "peripheral", "city": "Pune", "lat": 18.4489, "lon": 73.8526, "residential_apartment": 5200,  "residential_plot": 6500,  "commercial_shop": 8500,  "commercial_office": 6500,  "industrial": 3800},
}

# ── Mumbai ─────────────────────────────────────────────────────────────────
MUMBAI_RATES = {
    "Bandra West":    {"zone_tier": "prime",      "city": "Mumbai", "lat": 19.0596, "lon": 72.8295, "residential_apartment": 42000, "residential_plot": 65000, "commercial_shop": 75000, "commercial_office": 55000, "industrial": 20000},
    "Worli":          {"zone_tier": "prime",      "city": "Mumbai", "lat": 19.0176, "lon": 72.8178, "residential_apartment": 38000, "residential_plot": 58000, "commercial_shop": 68000, "commercial_office": 50000, "industrial": 18000},
    "Powai":          {"zone_tier": "prime",      "city": "Mumbai", "lat": 19.1197, "lon": 72.9051, "residential_apartment": 22000, "residential_plot": 32000, "commercial_shop": 40000, "commercial_office": 30000, "industrial": 12000},
    "Andheri West":   {"zone_tier": "prime",      "city": "Mumbai", "lat": 19.1313, "lon": 72.8258, "residential_apartment": 20000, "residential_plot": 28000, "commercial_shop": 35000, "commercial_office": 26000, "industrial": 10000},
    "Andheri East":   {"zone_tier": "mid",        "city": "Mumbai", "lat": 19.1136, "lon": 72.8697, "residential_apartment": 16000, "residential_plot": 22000, "commercial_shop": 28000, "commercial_office": 21000, "industrial": 9000},
    "Thane":          {"zone_tier": "mid",        "city": "Mumbai", "lat": 19.2183, "lon": 72.9781, "residential_apartment": 12000, "residential_plot": 16000, "commercial_shop": 20000, "commercial_office": 15000, "industrial": 7500},
    "Navi Mumbai":    {"zone_tier": "mid",        "city": "Mumbai", "lat": 19.0368, "lon": 73.0158, "residential_apartment": 11000, "residential_plot": 14500, "commercial_shop": 18000, "commercial_office": 13500, "industrial": 7000},
    "Dadar":          {"zone_tier": "prime",      "city": "Mumbai", "lat": 19.0186, "lon": 72.8430, "residential_apartment": 28000, "residential_plot": 42000, "commercial_shop": 55000, "commercial_office": 38000, "industrial": 15000},
    "Borivali":       {"zone_tier": "mid",        "city": "Mumbai", "lat": 19.2288, "lon": 72.8563, "residential_apartment": 14000, "residential_plot": 19000, "commercial_shop": 24000, "commercial_office": 18000, "industrial": 8500},
    "Mira Road":      {"zone_tier": "peripheral", "city": "Mumbai", "lat": 19.2815, "lon": 72.8656, "residential_apartment": 8500,  "residential_plot": 11000, "commercial_shop": 14000, "commercial_office": 10500, "industrial": 5500},
    "Virar":          {"zone_tier": "peripheral", "city": "Mumbai", "lat": 19.4647, "lon": 72.8108, "residential_apartment": 5500,  "residential_plot": 7200,  "commercial_shop": 9000,  "commercial_office": 7000,  "industrial": 4000},
    "Kharghar":       {"zone_tier": "mid",        "city": "Mumbai", "lat": 19.0473, "lon": 73.0687, "residential_apartment": 10000, "residential_plot": 13500, "commercial_shop": 17000, "commercial_office": 12500, "industrial": 6500},
}

# ── Bangalore ──────────────────────────────────────────────────────────────
BANGALORE_RATES = {
    "Koramangala":    {"zone_tier": "prime",      "city": "Bangalore", "lat": 12.9279, "lon": 77.6271, "residential_apartment": 14500, "residential_plot": 22000, "commercial_shop": 28000, "commercial_office": 20000, "industrial": 9000},
    "Indiranagar":    {"zone_tier": "prime",      "city": "Bangalore", "lat": 12.9716, "lon": 77.6412, "residential_apartment": 13000, "residential_plot": 19000, "commercial_shop": 25000, "commercial_office": 18000, "industrial": 8500},
    "Whitefield":     {"zone_tier": "prime",      "city": "Bangalore", "lat": 12.9698, "lon": 77.7499, "residential_apartment": 10000, "residential_plot": 14000, "commercial_shop": 18000, "commercial_office": 14000, "industrial": 7000},
    "HSR Layout":     {"zone_tier": "prime",      "city": "Bangalore", "lat": 12.9082, "lon": 77.6476, "residential_apartment": 11500, "residential_plot": 16000, "commercial_shop": 21000, "commercial_office": 15500, "industrial": 7500},
    "Electronic City":{"zone_tier": "mid",        "city": "Bangalore", "lat": 12.8399, "lon": 77.6770, "residential_apartment": 7500,  "residential_plot": 10000, "commercial_shop": 13000, "commercial_office": 10000, "industrial": 6000},
    "Marathahalli":   {"zone_tier": "mid",        "city": "Bangalore", "lat": 12.9591, "lon": 77.7001, "residential_apartment": 8200,  "residential_plot": 11000, "commercial_shop": 14500, "commercial_office": 11000, "industrial": 5800},
    "Sarjapur Road":  {"zone_tier": "mid",        "city": "Bangalore", "lat": 12.8954, "lon": 77.6795, "residential_apartment": 8800,  "residential_plot": 12000, "commercial_shop": 15500, "commercial_office": 11500, "industrial": 6200},
    "Yelahanka":      {"zone_tier": "mid",        "city": "Bangalore", "lat": 13.1004, "lon": 77.5963, "residential_apartment": 7000,  "residential_plot": 9500,  "commercial_shop": 12000, "commercial_office": 9000,  "industrial": 5200},
    "Bannerghatta":   {"zone_tier": "peripheral", "city": "Bangalore", "lat": 12.8624, "lon": 77.5982, "residential_apartment": 5800,  "residential_plot": 7800,  "commercial_shop": 10000, "commercial_office": 7800,  "industrial": 4500},
    "Devanahalli":    {"zone_tier": "peripheral", "city": "Bangalore", "lat": 13.2468, "lon": 77.7137, "residential_apartment": 5000,  "residential_plot": 6800,  "commercial_shop": 8500,  "commercial_office": 6500,  "industrial": 4000},
    "Tumkur Road":    {"zone_tier": "peripheral", "city": "Bangalore", "lat": 13.0298, "lon": 77.4968, "residential_apartment": 5500,  "residential_plot": 7200,  "commercial_shop": 9500,  "commercial_office": 7200,  "industrial": 4200},
}

# ── Merged lookup ──────────────────────────────────────────────────────────
ALL_CIRCLE_RATES = {**PUNE_RATES, **MUMBAI_RATES, **BANGALORE_RATES}

CITY_LOCALITIES = {
    "Pune":      list(PUNE_RATES.keys()),
    "Mumbai":    list(MUMBAI_RATES.keys()),
    "Bangalore": list(BANGALORE_RATES.keys()),
}

ZONE_MULTIPLIERS = {
    "prime":      {"min": 1.7, "mid": 2.1, "max": 2.6},
    "mid":        {"min": 1.2, "mid": 1.45, "max": 1.75},
    "peripheral": {"min": 0.85, "mid": 1.05, "max": 1.25},
}

PROPERTY_TYPE_MAP = {
    "2bhk_apartment": "residential_apartment",
    "3bhk_apartment": "residential_apartment",
    "1bhk_apartment": "residential_apartment",
    "4bhk_apartment": "residential_apartment",
    "villa":           "residential_apartment",
    "plot":            "residential_plot",
    "shop":            "commercial_shop",
    "office":          "commercial_office",
    "warehouse":       "industrial",
    "residential_apartment": "residential_apartment",
    "commercial_shop":       "commercial_shop",
}


def get_circle_rate(locality: str, property_type: str) -> dict:
    from app.core.db import SessionLocal
    from app.models.db_models import CircleRate
    
    normalized = locality.strip().title()
    prop_key = PROPERTY_TYPE_MAP.get(property_type.lower(), "residential_apartment")
    
    db = SessionLocal()
    try:
        # Perform an ILIKE query for substring match, just like the old logic
        rate = db.query(CircleRate).filter(CircleRate.locality.ilike(f"%{normalized}%")).first()
        
        if rate:
            # Dynamically get the appropriate property rate column
            rate_val = getattr(rate, prop_key, rate.residential_apartment)
            return {
                "locality": rate.locality,
                "city": rate.city,
                "zone_tier": rate.zone_tier,
                "circle_rate_per_sqft": rate_val,
                "property_type_key": prop_key,
                "lat": rate.lat,
                "lon": rate.lon,
            }
        else:
            # Fallback if locality completely unknown
            return {
                "locality": locality,
                "city": "Pune",
                "zone_tier": "mid",
                "circle_rate_per_sqft": 6000,
                "property_type_key": prop_key,
                "lat": None,
                "lon": None,
            }
    finally:
        db.close()


def get_localities_by_city() -> dict:
    from app.core.db import SessionLocal
    from app.models.db_models import CircleRate
    
    db = SessionLocal()
    try:
        rates = db.query(CircleRate.city, CircleRate.locality).all()
        result = {}
        for city, locality in rates:
            if city not in result:
                result[city] = []
            result[city].append(locality)
        return result
    finally:
        db.close()