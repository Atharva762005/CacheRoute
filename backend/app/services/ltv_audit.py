"""
PropIQ LTV Calculator — RBI LAP Guidelines
Computes max Loan-to-Value ratio per RBI Master Circular on Loans & Advances.
"""

from typing import Dict


# RBI LAP LTV limits (Master Circular 2024)
RBI_LTV_LIMITS = {
    "residential_apartment": {
        "up_to_30L":     {"max_ltv": 0.90, "note": "Up to ₹30L: 90% LTV permitted"},
        "30L_to_75L":    {"max_ltv": 0.80, "note": "₹30L–75L: 80% LTV"},
        "above_75L":     {"max_ltv": 0.75, "note": "Above ₹75L: 75% LTV (RBI cap)"},
    },
    "commercial_shop":   {"all": {"max_ltv": 0.65, "note": "Commercial: max 65% LTV"}},
    "commercial_office": {"all": {"max_ltv": 0.65, "note": "Commercial: max 65% LTV"}},
    "residential_plot":  {"all": {"max_ltv": 0.70, "note": "Plot: max 70% LTV"}},
    "industrial":        {"all": {"max_ltv": 0.55, "note": "Industrial: max 55% LTV"}},
}

# PFL conservative internal limits (tighter than RBI max)
PFL_CONSERVATIVE_LTV = {
    "prime":      0.70,
    "mid":        0.65,
    "peripheral": 0.55,
}


def calculate_ltv(
    market_value_mid: int,
    distress_value_range: list,
    prop_type_key: str,
    zone_tier: str,
    risk_flags: list,
    resale_potential_index: float = 50.0,
) -> Dict:
    """
    Compute LTV recommendation with RBI compliance rationale.
    """
    prop_key = prop_type_key if prop_type_key in RBI_LTV_LIMITS else "residential_apartment"
    limits = RBI_LTV_LIMITS[prop_key]

    # Get RBI LTV
    if "all" in limits:
        rbi_max = limits["all"]["max_ltv"]
        rbi_note = limits["all"]["note"]
    else:
        if market_value_mid <= 3_000_000:
            rbi_max = limits["up_to_30L"]["max_ltv"]
            rbi_note = limits["up_to_30L"]["note"]
        elif market_value_mid <= 7_500_000:
            rbi_max = limits["30L_to_75L"]["max_ltv"]
            rbi_note = limits["30L_to_75L"]["note"]
        else:
            rbi_max = limits["above_75L"]["max_ltv"]
            rbi_note = limits["above_75L"]["note"]

    # PFL conservative LTV
    pfl_ltv = PFL_CONSERVATIVE_LTV.get(zone_tier, 0.65)

    # Adjust for risk flags
    high_flags = [f for f in risk_flags if f.get("severity") == "high"]
    if len(high_flags) >= 2:
        pfl_ltv = min(pfl_ltv, 0.50)
        flag_note = f"{len(high_flags)} high-severity flags — LTV capped at 50%"
    elif len(high_flags) == 1:
        pfl_ltv = min(pfl_ltv, 0.60)
        flag_note = f"1 high-severity flag — conservative LTV applied"
    elif len(risk_flags) > 0:
        pfl_ltv = pfl_ltv - 0.05
        flag_note = f"{len(risk_flags)} risk flag(s) — 5% LTV haircut applied"
    else:
        flag_note = "No risk flags — standard LTV"

    # Dynamic LTV Pricing based on Liquidity (RPI)
    if resale_potential_index >= 75:
        # Highly Liquid: +10% LTV boost (capped at 85% internal max)
        pfl_ltv = min(pfl_ltv + 0.10, 0.85)
        flag_note += f" | Dynamic LTV: +10% boost for Highly Liquid property (RPI {resale_potential_index:.1f})"
    elif resale_potential_index < 50:
        # Illiquid: -10% LTV penalty
        pfl_ltv = max(pfl_ltv - 0.10, 0.40)
        flag_note += f" | Dynamic LTV: -10% penalty for Illiquid property (RPI {resale_potential_index:.1f})"

    # Use distress value as security (conservative approach)
    distress_mid = int((distress_value_range[0] + distress_value_range[1]) / 2)

    recommended_ltv = min(rbi_max, pfl_ltv)
    max_loan_on_market = round(market_value_mid * recommended_ltv)
    max_loan_on_distress = round(distress_mid * recommended_ltv)

    return {
        "recommended_ltv_pct": round(recommended_ltv * 100, 1),
        "rbi_max_ltv_pct": round(rbi_max * 100, 1),
        "pfl_internal_ltv_pct": round(pfl_ltv * 100, 1),
        "max_loan_amount": max_loan_on_market,
        "max_loan_on_distress_value": max_loan_on_distress,
        "rbi_rationale": rbi_note,
        "pfl_rationale": flag_note,
        "zone_tier": zone_tier,
        "ltv_zone": (
            "green" if recommended_ltv >= 0.70 else
            "amber" if recommended_ltv >= 0.55 else
            "red"
        ),
        "disclaimer": "LTV computed per RBI Master Circular on Housing Loans 2024. Subject to internal credit policy and borrower creditworthiness assessment.",
    }


# ── Audit Log ──────────────────────────────────────────────────────────────

import sqlite3
import json
from pathlib import Path
from datetime import datetime

AUDIT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "audit.db"


def init_audit_db():
    AUDIT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            locality TEXT,
            city TEXT,
            prop_type TEXT,
            size_sqft REAL,
            market_value_mid INTEGER,
            resale_potential_index REAL,
            confidence_score REAL,
            risk_flag_count INTEGER,
            processing_time_ms INTEGER,
            has_image INTEGER DEFAULT 0,
            endpoint TEXT DEFAULT '/assess'
        )
    """)
    conn.commit()
    conn.close()


def log_assessment(result: dict, endpoint: str = "/assess", has_image: bool = False):
    try:
        init_audit_db()
        conn = sqlite3.connect(AUDIT_DB_PATH)
        enrich = result.get("enrichment", {})
        conn.execute("""
            INSERT INTO audit_log (request_id, timestamp, locality, city, prop_type,
                size_sqft, market_value_mid, resale_potential_index, confidence_score,
                risk_flag_count, processing_time_ms, has_image, endpoint)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            result.get("request_id", ""),
            datetime.utcnow().isoformat(),
            result.get("locality", ""),
            enrich.get("city", "Pune"),
            result.get("prop_type", ""),
            result.get("size_sqft", 0),
            result.get("market_value_mid", 0),
            result.get("resale_potential_index", 0),
            result.get("confidence_score", 0),
            len(result.get("risk_flags", [])),
            result.get("processing_time_ms", 0),
            1 if has_image else 0,
            endpoint,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error (non-fatal): {e}")


def get_recent_assessments(limit: int = 20) -> list:
    try:
        init_audit_db()
        conn = sqlite3.connect(AUDIT_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM audit_log
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_audit_stats() -> dict:
    try:
        init_audit_db()
        conn = sqlite3.connect(AUDIT_DB_PATH)
        stats = conn.execute("""
            SELECT
                COUNT(*) as total_assessments,
                ROUND(AVG(processing_time_ms), 0) as avg_processing_ms,
                ROUND(AVG(confidence_score), 2) as avg_confidence,
                SUM(risk_flag_count) as total_flags_raised,
                SUM(has_image) as cv_assessments,
                COUNT(DISTINCT locality) as unique_localities
            FROM audit_log
        """).fetchone()
        conn.close()
        if stats:
            return {
                "total_assessments": stats[0],
                "avg_processing_ms": stats[1],
                "avg_confidence": stats[2],
                "total_flags_raised": stats[3],
                "cv_assessments": stats[4],
                "unique_localities": stats[5],
            }
    except Exception:
        pass
    return {}