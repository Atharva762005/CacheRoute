"""
PropIQ Test Suite — Day 1
Tests: circle rates, data generator, ML model, enrichment, PDF, API endpoints
Run: cd backend && pytest tests/ -v
"""
import sys
import asyncio
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Circle Rate Tests ──────────────────────────────────────────────────────

def test_circle_rate_known_locality():
    from app.data.india_circle_rates import get_circle_rate
    result = get_circle_rate("Baner", "2bhk_apartment")
    assert result["zone_tier"] == "prime"
    assert result["circle_rate_per_sqft"] > 5000
    assert result["locality"] == "Baner"

def test_circle_rate_unknown_locality():
    from app.data.india_circle_rates import get_circle_rate
    result = get_circle_rate("Unknown Area XYZ", "2bhk_apartment")
    assert result["circle_rate_per_sqft"] == 6000
    assert result["zone_tier"] == "mid"

def test_circle_rate_all_property_types():
    from app.data.india_circle_rates import get_circle_rate
    prop_types = ["2bhk_apartment", "villa", "shop", "office", "plot"]
    for pt in prop_types:
        r = get_circle_rate("Kothrud", pt)
        assert r["circle_rate_per_sqft"] > 0, f"Failed for {pt}"

def test_all_localities_covered():
    from app.data.india_circle_rates import ALL_CIRCLE_RATES
    assert len(ALL_CIRCLE_RATES) >= 10
    for name, data in ALL_CIRCLE_RATES.items():
        assert "zone_tier" in data
        assert data["zone_tier"] in ["prime", "mid", "peripheral"]
        assert data["residential_apartment"] > 0


# ── Data Generator Tests ───────────────────────────────────────────────────

def test_data_generator_output_shape():
    from app.ml.data_generator import generate_dataset
    df = generate_dataset(n_per_combination=2)
    assert len(df) > 100
    required_cols = ["locality", "zone_tier", "prop_type", "size_sqft", "age_years",
                     "price_per_sqft", "total_market_value", "liquidity_score"]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"

def test_data_generator_value_ranges():
    from app.ml.data_generator import generate_dataset
    df = generate_dataset(n_per_combination=3)
    assert df["total_market_value"].min() > 0
    assert df["total_market_value"].max() < 1e9   # < 100 Cr sanity check
    assert df["liquidity_score"].between(0, 100).all()
    assert df["price_per_sqft"].min() > 500      # > ₹500/sqft minimum

def test_circle_rate_anchoring():
    from app.ml.data_generator import generate_dataset
    from app.data.india_circle_rates import ALL_CIRCLE_RATES
    df = generate_dataset(n_per_combination=5)
    # Market price should always be above circle rate (no discount below floor)
    above_floor = df["price_per_sqft"] >= df["circle_rate_per_sqft"] * 0.5
    assert above_floor.mean() > 0.9, "Most prices should be above 50% of circle rate"


# ── ML Model Tests ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def trained_model():
    from app.ml.valuation_model import PropIQModel
    model_path = str(Path(__file__).parent.parent / "data" / "models")
    return PropIQModel.load(model_path)

def test_model_loads(trained_model):
    assert trained_model is not None
    assert trained_model.model_p50 is not None
    assert trained_model.model_liquidity is not None
    assert trained_model.anomaly_detector is not None
    assert trained_model.shap_explainer is not None

def test_model_mape_acceptable(trained_model):
    assert trained_model.mape_validation is not None
    assert trained_model.mape_validation < 0.25, f"MAPE {trained_model.mape_validation*100:.1f}% is too high"

def test_prediction_output_structure(trained_model):
    test_input = {
        "locality": "Baner", "zone_tier": "prime", "prop_type": "2bhk_apartment",
        "size_sqft": 850, "age_years": 8, "floor_num": 5,
        "is_freehold": 1, "is_rera_registered": 1, "rental_yield_pct": 3.5,
        "infra_score": 72, "listing_density": 0.65, "is_standard_config": 1,
        "circle_rate_per_sqft": 10800, "location_multiplier": 2.0,
    }
    result = trained_model.predict(test_input)
    assert "market_value_range" in result
    assert "distress_value_range" in result
    assert "resale_potential_index" in result
    assert "confidence_score" in result
    assert "key_drivers" in result
    assert "risk_flags" in result
    assert "shap_values" in result
    assert len(result["market_value_range"]) == 2
    assert result["market_value_range"][0] <= result["market_value_range"][1]

def test_prediction_value_sanity(trained_model):
    test_input = {
        "locality": "Baner", "zone_tier": "prime", "prop_type": "2bhk_apartment",
        "size_sqft": 850, "age_years": 8, "floor_num": 5,
        "is_freehold": 1, "is_rera_registered": 1, "rental_yield_pct": 0,
        "infra_score": 72, "listing_density": 0.65, "is_standard_config": 1,
        "circle_rate_per_sqft": 10800, "location_multiplier": 2.0,
    }
    result = trained_model.predict(test_input)
    mv_mid = result["market_value_mid"]
    assert mv_mid > 5_000_000,   f"Value too low: ₹{mv_mid/1e5:.1f}L for prime Pune 850sqft"
    assert mv_mid < 100_000_000, f"Value too high: ₹{mv_mid/1e7:.1f}Cr"
    assert 0 <= result["resale_potential_index"] <= 100
    assert 0 <= result["confidence_score"] <= 1

def test_leasehold_gets_flagged(trained_model):
    test_input = {
        "locality": "Baner", "zone_tier": "prime", "prop_type": "2bhk_apartment",
        "size_sqft": 850, "age_years": 8, "floor_num": 5,
        "is_freehold": 0,   # Leasehold
        "is_rera_registered": 1, "rental_yield_pct": 0,
        "infra_score": 72, "listing_density": 0.65, "is_standard_config": 1,
        "circle_rate_per_sqft": 10800, "location_multiplier": 2.0,
    }
    result = trained_model.predict(test_input)
    flag_names = [f["flag"] for f in result["risk_flags"]]
    assert "leasehold_title" in flag_names

def test_prime_vs_peripheral_ordering(trained_model):
    base = {
        "prop_type": "2bhk_apartment", "size_sqft": 800, "age_years": 5,
        "floor_num": 3, "is_freehold": 1, "is_rera_registered": 1,
        "rental_yield_pct": 0, "infra_score": 60, "listing_density": 0.5,
        "is_standard_config": 1, "location_multiplier": 2.0,
    }
    prime_input = {**base, "locality": "Koregaon Park", "zone_tier": "prime", "circle_rate_per_sqft": 12500}
    peripheral_input = {**base, "locality": "Chakan", "zone_tier": "peripheral", "circle_rate_per_sqft": 4500}
    prime_result = trained_model.predict(prime_input)
    peripheral_result = trained_model.predict(peripheral_input)
    assert prime_result["market_value_mid"] > peripheral_result["market_value_mid"], \
        "Prime zone should have higher value than peripheral"


# ── Enrichment Tests ───────────────────────────────────────────────────────

def test_geocode_known_locality():
    import asyncio
    from app.services.enrichment import enrich_property
    result = asyncio.run(enrich_property("Baner", zone_tier="prime"))
    assert "geo" in result
    assert result["geo"]["lat"] > 18.0
    assert result["geo"]["lon"] > 73.0
    assert result["listing_density"] > 0

def test_listing_density_by_zone():
    from app.services.enrichment import estimate_listing_density
    prime = estimate_listing_density("prime", "Koregaon Park")
    peripheral = estimate_listing_density("peripheral", "Chakan")
    assert prime["listing_density"] > peripheral["listing_density"]


# ── PDF Tests ──────────────────────────────────────────────────────────────

def test_pdf_generates_bytes():
    from app.services.pdf_report import generate_pdf_report
    sample = {
        "request_id": "TEST001",
        "locality": "Baner", "prop_type": "2bhk_apartment", "size_sqft": 850,
        "market_value_range": [17200000, 20800000], "market_value_mid": 19000000,
        "distress_value_range": [14276000, 17264000],
        "resale_potential_index": 85.2, "estimated_time_to_sell_days": [25, 60],
        "confidence_score": 0.87, "price_per_sqft_estimate": 22353, "model_mape_pct": 8.3,
        "key_drivers": [{"feature": "circle_rate_per_sqft", "impact_inr": 4200000, "direction": "positive"}],
        "risk_flags": [],
        "enrichment": {"zone_tier": "prime", "circle_rate_per_sqft": 10800,
                       "infra_score": 72.0, "listing_density": 0.811, "geo": {}},
        "cv_assessment": None, "version": "1.0.0",
    }
    pdf = generate_pdf_report(sample)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf[:4] == b"%PDF"  # Valid PDF magic bytes

def test_pdf_with_risk_flags():
    from app.services.pdf_report import generate_pdf_report
    sample = {
        "request_id": "TEST002",
        "locality": "Wagholi", "prop_type": "villa", "size_sqft": 2200,
        "market_value_range": [8000000, 10000000], "market_value_mid": 9000000,
        "distress_value_range": [6000000, 7500000],
        "resale_potential_index": 42.0, "estimated_time_to_sell_days": [90, 180],
        "confidence_score": 0.61, "price_per_sqft_estimate": 4090, "model_mape_pct": 8.3,
        "key_drivers": [],
        "risk_flags": [
            {"flag": "leasehold_title", "severity": "high", "detail": "Leasehold — resale impacted"},
            {"flag": "high_building_age", "severity": "medium", "detail": "35 year old building"},
        ],
        "enrichment": {"zone_tier": "peripheral", "circle_rate_per_sqft": 5500,
                       "infra_score": 32.0, "listing_density": 0.35, "geo": {}},
        "cv_assessment": None, "version": "1.0.0",
    }
    pdf = generate_pdf_report(sample)
    assert len(pdf) > 1000


# ── CV Module Tests ────────────────────────────────────────────────────────

def test_cv_fallback_works():
    from app.ml.cv_module import PropertyCVAnalyzer
    analyzer = PropertyCVAnalyzer()
    # Will use fallback since CLIP can't load in sandbox
    result = analyzer.analyze_image(b"fake_image_bytes")
    assert "condition" in result
    assert "valuation_adjustment_factor" in result
    assert result["valuation_adjustment_factor"] > 0

def test_cv_adjustment_factors():
    from app.ml.cv_module import CONDITION_ADJUSTMENTS
    assert CONDITION_ADJUSTMENTS["excellent"]["factor"] > 1.0
    assert CONDITION_ADJUSTMENTS["good"]["factor"] == 1.0
    assert CONDITION_ADJUSTMENTS["fair"]["factor"] < 1.0
    assert CONDITION_ADJUSTMENTS["poor"]["factor"] < CONDITION_ADJUSTMENTS["fair"]["factor"]