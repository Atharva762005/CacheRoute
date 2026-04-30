"""
Synthetic training data generator for PropIQ valuation model.
Anchored to Pune circle rates, validated design based on domain rules.
Generates ~18,000 records across all property/zone combinations.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Support both `python -m app.ml.data_generator` (from backend/) and direct run
_backend_dir = Path(__file__).parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.data.india_circle_rates import ALL_CIRCLE_RATES, ZONE_MULTIPLIERS

np.random.seed(42)

PROPERTY_CONFIGS = {
    "1bhk_apartment": {"size_range": (350, 600), "floor_range": (0, 15), "base_demand": 0.75},
    "2bhk_apartment": {"size_range": (650, 1100), "floor_range": (0, 20), "base_demand": 1.0},
    "3bhk_apartment": {"size_range": (1050, 1800), "floor_range": (0, 20), "base_demand": 0.85},
    "4bhk_apartment": {"size_range": (1700, 3000), "floor_range": (0, 25), "base_demand": 0.6},
    "villa":          {"size_range": (2000, 5000), "floor_range": (0, 3),  "base_demand": 0.5},
    "shop":           {"size_range": (200, 1200),  "floor_range": (0, 5),  "base_demand": 0.7},
    "office":         {"size_range": (500, 3000),  "floor_range": (0, 20), "base_demand": 0.65},
    "plot":           {"size_range": (1000, 8000), "floor_range": (0, 0),  "base_demand": 0.55},
}

PROP_TYPE_TO_CIRCLE_KEY = {
    "1bhk_apartment": "residential_apartment",
    "2bhk_apartment": "residential_apartment",
    "3bhk_apartment": "residential_apartment",
    "4bhk_apartment": "residential_apartment",
    "villa": "residential_apartment",
    "shop": "commercial_shop",
    "office": "commercial_office",
    "plot": "residential_plot",
}

def age_depreciation(age_years: float) -> float:
    """RBI-aligned depreciation: 1.25%/year, floor at 55%."""
    return max(0.55, 1.0 - age_years * 0.0125)

def floor_premium(floor: int, prop_type: str) -> float:
    """Higher floors command premium for apartments."""
    if "apartment" not in prop_type and prop_type != "office":
        return 1.0
    if floor == 0:
        return 0.93
    elif floor <= 3:
        return 0.97
    elif floor <= 10:
        return 1.0 + floor * 0.004
    else:
        return 1.04 + (floor - 10) * 0.002

def infra_premium(infra_score: float) -> float:
    """Infrastructure proximity premium: up to +32%."""
    return 1.0 + (infra_score / 100.0) * 0.32

def rental_yield_signal(prop_type: str, zone_tier: str) -> float:
    """Rental yield affects investor demand and resale certainty."""
    base = {"prime": 3.8, "mid": 3.2, "peripheral": 2.6}[zone_tier]
    noise = np.random.normal(0, 0.3)
    return max(1.5, base + noise)

def generate_record(locality: str, zone_data: dict, prop_type: str) -> dict:
    config = PROPERTY_CONFIGS[prop_type]
    circle_key = PROP_TYPE_TO_CIRCLE_KEY.get(prop_type, "residential_apartment")
    zone_tier = zone_data["zone_tier"]
    circle_rate = zone_data[circle_key]

    # Property attributes
    size_sqft = np.random.uniform(*config["size_range"])
    age_years = np.random.choice([
        np.random.uniform(0, 5),
        np.random.uniform(5, 15),
        np.random.uniform(15, 40)
    ], p=[0.3, 0.45, 0.25])
    floor_num = int(np.random.uniform(*config["floor_range"]))

    # Location signals
    mult_range = ZONE_MULTIPLIERS[zone_tier]
    location_mult = np.random.triangular(
        mult_range["min"], mult_range["mid"], mult_range["max"]
    )
    infra_score = np.random.beta(2, 2) * 100
    if zone_tier == "prime":
        infra_score = min(100, infra_score + 25)
    elif zone_tier == "peripheral":
        infra_score = max(0, infra_score - 20)

    # Gap 9: Neighbourhood quality score (planned vs unplanned zone quality)
    nq_base = {"prime": 78.0, "mid": 58.0, "peripheral": 40.0}[zone_tier]
    # Infra score is a moderate signal of NQ, with independent noise
    nq_score = nq_base + (infra_score - 50) * 0.20 + np.random.normal(0, 6)
    neighbourhood_quality_score = round(min(100, max(10, nq_score)), 1)

    # Legal and occupancy
    is_freehold = np.random.choice([1, 0], p=[0.82, 0.18])
    is_rera_registered = np.random.choice([1, 0], p=[0.75, 0.25])
    occupancy = np.random.choice(["self_occupied", "rented", "vacant"], p=[0.55, 0.30, 0.15])
    rental_yield = rental_yield_signal(prop_type, zone_tier) if occupancy == "rented" else 0.0

    # Market signals
    listing_density = np.random.uniform(0.2, 0.9)
    if zone_tier == "prime":
        listing_density = min(1.0, listing_density + 0.2)
    is_standard_config = 1 if prop_type in ["2bhk_apartment", "3bhk_apartment"] else 0

    # Compute modifiers
    depreciation = age_depreciation(age_years)
    floor_factor = floor_premium(floor_num, prop_type)
    infra_factor = infra_premium(infra_score)
    legal_factor = 1.0 if is_freehold else 0.88
    rera_factor = 1.0 if is_rera_registered else 0.94
    demand_factor = config["base_demand"]
    rental_factor = 1.0 + (rental_yield / 100.0) * 0.8 if rental_yield > 0 else 1.0

    # Market value formula (circle rate anchored)
    noise = np.random.normal(1.0, 0.07)
    price_per_sqft = (
        circle_rate
        * location_mult
        * depreciation
        * floor_factor
        * infra_factor
        * legal_factor
        * rera_factor
        * demand_factor
        * rental_factor
        * noise
    )
    total_market_value = price_per_sqft * size_sqft

    # Liquidity score (0-100)
    liquidity_raw = (
        (infra_score * 0.30) +
        (is_standard_config * 100 * 0.25) +
        (is_freehold * 100 * 0.20) +
        (listing_density * 100 * 0.15) +
        (max(0, 100 - age_years * 1.5) * 0.10)
    )
    liquidity_score = min(100, max(0, liquidity_raw + np.random.normal(0, 3)))

    # Time to liquidate (days) — derived from liquidity score
    if liquidity_score >= 75:
        ttl_min, ttl_max = int(np.random.uniform(20, 45)), int(np.random.uniform(50, 80))
    elif liquidity_score >= 50:
        ttl_min, ttl_max = int(np.random.uniform(45, 80)), int(np.random.uniform(90, 150))
    else:
        ttl_min, ttl_max = int(np.random.uniform(90, 150)), int(np.random.uniform(160, 300))

    # Distress value
    if liquidity_score >= 75:
        distress_discount = np.random.uniform(0.78, 0.88)
    elif liquidity_score >= 50:
        distress_discount = np.random.uniform(0.68, 0.80)
    else:
        distress_discount = np.random.uniform(0.55, 0.70)
    distress_value = total_market_value * distress_discount

    return {
        # Inputs
        "locality": locality,
        "zone_tier": zone_tier,
        "prop_type": prop_type,
        "size_sqft": round(size_sqft, 1),
        "age_years": round(age_years, 1),
        "floor_num": floor_num,
        "is_freehold": is_freehold,
        "is_rera_registered": is_rera_registered,
        "occupancy": occupancy,
        "rental_yield_pct": round(rental_yield, 2),
        "infra_score": round(infra_score, 1),
        "listing_density": round(listing_density, 3),
        "is_standard_config": is_standard_config,
        "circle_rate_per_sqft": circle_rate,
        # Derived features
        "location_multiplier": round(location_mult, 3),
        "age_depreciation_factor": round(depreciation, 3),
        "zone_tier_encoded": {"prime": 2, "mid": 1, "peripheral": 0}[zone_tier],
        "neighbourhood_quality_score": neighbourhood_quality_score,  # Gap 9
        # Targets
        "price_per_sqft": round(price_per_sqft, 1),
        "total_market_value": round(total_market_value, 0),
        "distress_value": round(distress_value, 0),
        "liquidity_score": round(liquidity_score, 1),
        "ttl_min_days": ttl_min,
        "ttl_max_days": ttl_max,
        "distress_discount": round(distress_discount, 3),
    }


def generate_dataset(n_per_combination: int = 12) -> pd.DataFrame:
    records = []
    for locality, zone_data in ALL_CIRCLE_RATES.items():
        for prop_type in PROPERTY_CONFIGS.keys():
            for _ in range(n_per_combination):
                records.append(generate_record(locality, zone_data, prop_type))
    df = pd.DataFrame(records)
    print(f"Generated {len(df)} records across {df['locality'].nunique()} localities, {df['prop_type'].nunique()} property types")
    print(f"Price range: ₹{df['total_market_value'].min()/1e6:.1f}L — ₹{df['total_market_value'].max()/1e6:.1f}Cr")
    print(f"Liquidity score range: {df['liquidity_score'].min():.1f} — {df['liquidity_score'].max():.1f}")
    return df


if __name__ == "__main__":
    out = Path(__file__).parent.parent.parent / "data" / "processed"
    out.mkdir(parents=True, exist_ok=True)
    df = generate_dataset(n_per_combination=14)
    df.to_csv(out / "synthetic_training_data.csv", index=False)
    print(f"Saved to {out / 'synthetic_training_data.csv'}")