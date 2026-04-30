import pytest
import pandas as pd
from app.ml.valuation_model import PropIQModel

def test_model_boundary_conditions():
    # Load an untrained or mock model, but since training requires data,
    # we'll test the boundaries of the helper methods without needing weights.
    model = PropIQModel()
    
    # Test property encoder mapping fallback
    row = model._build_feature_row({"prop_type": "unknown_type"})
    assert row["size_sqft"] == 800.0  # Should use defaults for missing fields

    # Test risk flags
    flags = model._compute_risk_flags({"age_years": 50}, anomaly_score=-0.2, price_sqft=5000)
    assert any(f["flag"] == "high_building_age" for f in flags)
    assert any(f["flag"] == "anomalous_input_combination" for f in flags)

def test_ltv_logic():
    from app.services.ltv_audit import calculate_ltv
    
    # Standard residential with no flags -> 70% LTV (PFL Conservative Cap for Prime Zone)
    ltv = calculate_ltv(10000000, [8000000, 9000000], "residential_apartment", "prime", [])
    assert ltv["recommended_ltv_pct"] == 70.0
    assert ltv["max_loan_amount"] == 7000000

    # Risk flags reduce LTV
    ltv_risk = calculate_ltv(10000000, [8000000, 9000000], "residential_apartment", "prime", [{"severity": "high"}])
    assert ltv_risk["recommended_ltv_pct"] < 80.0
