"""
PropIQ Valuation Model
- XGBoost quantile regression (P10, P50, P90) for honest price ranges
- SHAP explainability for every prediction
- Liquidity scoring model
- Fraud/anomaly detection via Isolation Forest
"""

import numpy as np
import pandas as pd
# import shap  <-- Moved inside methods for lazy loading
import pickle
import json
from pathlib import Path
from xgboost import XGBRegressor
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error

FEATURE_COLS = [
    "size_sqft", "age_years", "floor_num", "is_freehold", "is_rera_registered",
    "rental_yield_pct", "infra_score", "listing_density", "is_standard_config",
    "circle_rate_per_sqft", "location_multiplier", "age_depreciation_factor",
    "zone_tier_encoded",
]

PROP_TYPE_ENCODING = {
    "1bhk_apartment": 0, "2bhk_apartment": 1, "3bhk_apartment": 2,
    "4bhk_apartment": 3, "villa": 4, "shop": 5, "office": 6, "plot": 7,
}


class PropIQModel:
    def __init__(self):
        self.model_p10 = None
        self.model_p50 = None
        self.model_p90 = None
        self.model_liquidity = None
        self.anomaly_detector = None
        self.shap_explainer = None
        self.feature_cols_full = FEATURE_COLS + ["prop_type_encoded"]
        self.mape_validation = None

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "prop_type" in df.columns:
            df["prop_type_encoded"] = df["prop_type"].map(PROP_TYPE_ENCODING).fillna(1)
        return df[self.feature_cols_full]

    def train(self, df: pd.DataFrame):
        df = df.copy()
        df["prop_type_encoded"] = df["prop_type"].map(PROP_TYPE_ENCODING).fillna(1)
        X = df[self.feature_cols_full]
        y_price = np.log1p(df["price_per_sqft"])
        y_liq = df["liquidity_score"]

        X_train, X_val, y_train_p, y_val_p = train_test_split(X, y_price, test_size=0.15, random_state=42)
        _, _, y_train_l, y_val_l = train_test_split(X, y_liq, test_size=0.15, random_state=42)

        xgb_params = dict(
            n_estimators=400,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
        )

        print("Training P10 model...")
        self.model_p10 = XGBRegressor(objective="reg:quantileerror", quantile_alpha=0.10, **xgb_params)
        self.model_p10.fit(X_train, y_train_p, eval_set=[(X_val, y_val_p)], verbose=False)

        print("Training P50 model...")
        self.model_p50 = XGBRegressor(objective="reg:quantileerror", quantile_alpha=0.50, **xgb_params)
        self.model_p50.fit(X_train, y_train_p, eval_set=[(X_val, y_val_p)], verbose=False)

        print("Training P90 model...")
        self.model_p90 = XGBRegressor(objective="reg:quantileerror", quantile_alpha=0.90, **xgb_params)
        self.model_p90.fit(X_train, y_train_p, eval_set=[(X_val, y_val_p)], verbose=False)

        print("Training liquidity model...")
        self.model_liquidity = XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.06, random_state=42)
        self.model_liquidity.fit(X_train, y_train_l, verbose=False)

        print("Training anomaly detector...")
        self.anomaly_detector = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
        self.anomaly_detector.fit(X)

        print("Building SHAP explainer...")
        import shap
        self.shap_explainer = shap.TreeExplainer(self.model_p50)

        # Validation MAPE
        y_pred_val = np.expm1(self.model_p50.predict(X_val))
        y_true_val = np.expm1(y_val_p)
        self.mape_validation = mean_absolute_percentage_error(y_true_val, y_pred_val)
        print(f"Validation MAPE: {self.mape_validation*100:.1f}%")

        return self

    def predict(self, input_data: dict) -> dict:
        """Full prediction with ranges, SHAP, liquidity, fraud flags."""
        row = self._build_feature_row(input_data)
        X = pd.DataFrame([row])

        log_p10 = self.model_p10.predict(X)[0]
        log_p50 = self.model_p50.predict(X)[0]
        log_p90 = self.model_p90.predict(X)[0]

        p10_sqft = np.expm1(log_p10)
        p50_sqft = np.expm1(log_p50)
        p90_sqft = np.expm1(log_p90)
        size = input_data.get("size_sqft", 800)

        mv_low  = round(p10_sqft * size)
        mv_mid  = round(p50_sqft * size)
        mv_high = round(p90_sqft * size)

        liq_score = float(np.clip(self.model_liquidity.predict(X)[0], 0, 100))

        if liq_score >= 75:
            distress_factor = 0.83
            ttl = [25, 60]
        elif liq_score >= 50:
            distress_factor = 0.74
            ttl = [60, 120]
        else:
            distress_factor = 0.63
            ttl = [120, 240]

        dv_low  = round(mv_low  * distress_factor)
        dv_high = round(mv_high * distress_factor)

        confidence = self._confidence_score(input_data, liq_score, mv_high - mv_low, mv_mid)

        # SHAP values
        import shap
        shap_vals = self.shap_explainer.shap_values(X)
        shap_dict = {
            feat: round(float(np.expm1(val)) * p50_sqft * size)
            for feat, val in zip(self.feature_cols_full, shap_vals[0])
        }
        top_drivers = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:5]

        # Fraud / anomaly flags
        anomaly_score = float(self.anomaly_detector.decision_function(X)[0])
        risk_flags = self._compute_risk_flags(input_data, anomaly_score, p50_sqft)

        return {
            "market_value_range": [mv_low, mv_high],
            "market_value_mid": mv_mid,
            "distress_value_range": [dv_low, dv_high],
            "resale_potential_index": round(liq_score, 1),
            "estimated_time_to_sell_days": ttl,
            "confidence_score": round(confidence, 2),
            "price_per_sqft_estimate": round(p50_sqft),
            "key_drivers": [
                {"feature": k, "impact_inr": v, "direction": "positive" if v > 0 else "negative"}
                for k, v in top_drivers
            ],
            "shap_values": {k: round(v) for k, v in shap_dict.items()},
            "risk_flags": risk_flags,
            "anomaly_score": round(anomaly_score, 3),
            "model_mape_pct": round(self.mape_validation * 100, 1) if self.mape_validation else None,
        }

    def _build_feature_row(self, d: dict) -> dict:
        prop_type = d.get("prop_type", "2bhk_apartment").lower().replace(" ", "_")
        zone_tier = d.get("zone_tier", "mid")
        return {
            "size_sqft": float(d.get("size_sqft", 800)),
            "age_years": float(d.get("age_years", 10)),
            "floor_num": int(d.get("floor_num", 3)),
            "is_freehold": int(d.get("is_freehold", 1)),
            "is_rera_registered": int(d.get("is_rera_registered", 1)),
            "rental_yield_pct": float(d.get("rental_yield_pct", 0.0)),
            "infra_score": float(d.get("infra_score", 50.0)),
            "listing_density": float(d.get("listing_density", 0.5)),
            "is_standard_config": int(d.get("is_standard_config", 1)),
            "circle_rate_per_sqft": float(d.get("circle_rate_per_sqft", 7500)),
            "location_multiplier": float(d.get("location_multiplier", 1.4)),
            "age_depreciation_factor": max(0.55, 1.0 - float(d.get("age_years", 10)) * 0.0125),
            "zone_tier_encoded": {"prime": 2, "mid": 1, "peripheral": 0}.get(zone_tier, 1),
            "prop_type_encoded": PROP_TYPE_ENCODING.get(prop_type, 1),
        }

    def _confidence_score(self, d: dict, liq: float, price_range: float, price_mid: float) -> float:
        completeness = sum([
            1 if d.get("size_sqft") else 0,
            1 if d.get("age_years") is not None else 0,
            0.5 if d.get("rental_yield_pct") else 0,
            0.5 if d.get("is_freehold") is not None else 0,
            0.3 if d.get("infra_score") else 0,
        ]) / 3.3
        range_tightness = 1.0 - min(1.0, (price_range / max(price_mid, 1)) * 2)
        liquidity_factor = liq / 100.0
        return min(0.97, (completeness * 0.5 + range_tightness * 0.3 + liquidity_factor * 0.2))

    def _compute_risk_flags(self, d: dict, anomaly_score: float, price_sqft: float) -> list:
        flags = []
        cr = d.get("circle_rate_per_sqft", 7500)
        if price_sqft < cr * 0.85:
            flags.append({"flag": "price_below_circle_rate", "severity": "high",
                          "detail": f"Estimated price ₹{price_sqft:.0f}/sqft is below circle rate ₹{cr}/sqft"})
        if anomaly_score < -0.1:
            flags.append({"flag": "anomalous_input_combination", "severity": "medium",
                          "detail": "Property attributes combination is statistically unusual for this zone"})
        age = d.get("age_years", 10)
        if age > 30:
            flags.append({"flag": "high_building_age", "severity": "medium",
                          "detail": f"Building age {age:.0f} years — increased maintenance and depreciation risk"})
        if not d.get("is_freehold", 1):
            flags.append({"flag": "leasehold_title", "severity": "high",
                          "detail": "Leasehold property — resale liquidity significantly impacted"})
        if not d.get("is_rera_registered", 1):
            flags.append({"flag": "not_rera_registered", "severity": "medium",
                          "detail": "Project not RERA registered — legal risk flag for collateral"})
        size = d.get("size_sqft", 800)
        zone = d.get("zone_tier", "mid")
        size_ceilings = {"prime": 6000, "mid": 4000, "peripheral": 3000}
        if size > size_ceilings.get(zone, 4000):
            flags.append({"flag": "oversized_for_zone", "severity": "low",
                          "detail": f"Size {size:.0f} sqft is unusually large for {zone} zone — verify"})
        return flags

    def save(self, path: str):
        Path(path).mkdir(parents=True, exist_ok=True)
        with open(f"{path}/propiq_model.pkl", "wb") as f:
            pickle.dump(self, f)
        meta = {"mape_validation_pct": round(self.mape_validation * 100, 2) if self.mape_validation else None,
                "feature_cols": self.feature_cols_full,
                "prop_type_encoding": PROP_TYPE_ENCODING}
        with open(f"{path}/model_meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        print(f"Model saved to {path}/")

    @classmethod
    def load(cls, path: str) -> "PropIQModel":
        import importlib, sys
        import __main__
        if not hasattr(__main__, "PropIQModel"):
            setattr(__main__, "PropIQModel", cls)
            
        # Register module under its canonical name so pickle can resolve
        # PropIQModel regardless of how the process was launched
        # (pytest, uvicorn, python -m, etc.)
        try:
            mod = importlib.import_module("app.ml.valuation_model")
            sys.modules["app.ml.valuation_model"] = mod
            sys.modules["valuation_model"] = mod
        except Exception:
            pass
        with open(f"{path}/propiq_model.pkl", "rb") as f:
            return pickle.load(f)

if __name__ == "__main__":
    _here = Path(__file__).parent.parent.parent   # → backend/
    data_path = _here / "data" / "processed" / "synthetic_training_data.csv"
    model_path = str(_here / "data" / "models")
    df = pd.read_csv(data_path)
    print(f"Loaded {len(df)} training records")
    model = PropIQModel()
    model.train(df)
    model.save(model_path)

    # Quick sanity check
    test_input = {
        "locality": "Baner", "zone_tier": "prime", "prop_type": "2bhk_apartment",
        "size_sqft": 850, "age_years": 8, "floor_num": 5,
        "is_freehold": 1, "is_rera_registered": 1, "rental_yield_pct": 3.5,
        "infra_score": 72, "listing_density": 0.65, "is_standard_config": 1,
        "circle_rate_per_sqft": 10800, "location_multiplier": 2.0,
    }
    result = model.predict(test_input)
    mv = result["market_value_range"]
    print(f"\nSanity check — Baner 2BHK 850sqft:")
    print(f"  Market value: ₹{mv[0]/1e6:.1f}L — ₹{mv[1]/1e6:.1f}L")
    print(f"  Resale index: {result['resale_potential_index']}")
    print(f"  Confidence:   {result['confidence_score']}")
    print(f"  Risk flags:   {len(result['risk_flags'])}")
    print(f"  Top driver:   {result['key_drivers'][0]['feature']}")