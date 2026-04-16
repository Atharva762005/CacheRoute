"""
PropIQ LLM Narration Service
Uses Groq API (llama-3.3-70b) to convert JSON assessment into credit memo language.
This is the feature that makes PropIQ demo-ready — a loan officer
can read this output directly into a file note.
"""

import os
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Ensure .env is loaded from project root
from dotenv import load_dotenv
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env", override=False)
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)

GROQ_MODEL = "llama-3.3-70b-versatile"


def fmt_inr(value: int) -> str:
    if value >= 10_000_000: return f"₹{value/10_000_000:.2f} Cr"
    if value >= 100_000:    return f"₹{value/100_000:.2f} L"
    return f"₹{value:,}"


async def generate_credit_memo(assessment: dict) -> dict:
    """
    Generate a plain-English credit memo from assessment JSON using Groq.
    Returns: { summary, recommendation, risk_narrative, key_points }
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return _fallback_memo(assessment)

    mv = assessment.get("market_value_range", [0, 0])
    dv = assessment.get("distress_value_range", [0, 0])
    rpi = assessment.get("resale_potential_index", 0)
    conf = assessment.get("confidence_score", 0)
    flags = assessment.get("risk_flags", [])
    drivers = assessment.get("key_drivers", [])
    enrichment = assessment.get("enrichment", {})

    prompt = f"""You are a senior credit analyst at Poonawalla Fincorp writing a collateral file note for a LAP (Loan Against Property) application.

Based on the following PropIQ AI assessment, write a concise professional credit memo. Use plain English. Be specific with numbers. Sound like an experienced banker, not an AI.

ASSESSMENT DATA:
- Property: {assessment.get('prop_type','').replace('_',' ').title()} in {assessment.get('locality','')}, Pune
- Size: {assessment.get('size_sqft',0):,} sqft
- Market Value Range: {fmt_inr(mv[0])} – {fmt_inr(mv[1])} (mid: {fmt_inr(assessment.get('market_value_mid',0))})
- Distress Value: {fmt_inr(dv[0])} – {fmt_inr(dv[1])}
- Resale Potential Index: {rpi}/100 ({'Highly Liquid' if rpi>=75 else 'Moderate' if rpi>=50 else 'Illiquid'})
- Time to Liquidate: {assessment.get('estimated_time_to_sell_days',['?','?'])[0]}–{assessment.get('estimated_time_to_sell_days',['?','?'])[1]} days
- Confidence Score: {conf:.0%}
- Zone: {enrichment.get('zone_tier','').title()} | Circle Rate: ₹{enrichment.get('circle_rate_per_sqft',0):,}/sqft
- Infra Score: {enrichment.get('infra_score',0):.0f}/100
- Risk Flags: {len(flags)} ({'none' if not flags else ', '.join(f['flag'].replace('_',' ') for f in flags[:3])})
- Top Value Drivers: {', '.join(d['feature'].replace('_',' ') for d in drivers[:3])}
- CV Condition: {assessment.get('cv_assessment',{}).get('condition','not assessed') if assessment.get('cv_assessment') else 'not assessed'}

Write EXACTLY this JSON structure (no markdown, no preamble):
{{
  "summary": "2-3 sentence summary of the collateral suitable for a credit committee presentation",
  "recommendation": "One clear recommendation sentence: acceptable/marginal/unacceptable collateral and suggested LTV",
  "risk_narrative": "2-3 sentences on the key risks specific to this property",
  "key_points": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"]
}}"""

    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)
        completion = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        text = completion.choices[0].message.content.strip()
        # Strip any accidental markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"LLM narration failed: {e} — using fallback")
        return _fallback_memo(assessment)


def _fallback_memo(assessment: dict) -> dict:
    """Deterministic fallback when API key not set."""
    mv = assessment.get("market_value_range", [0, 0])
    rpi = assessment.get("resale_potential_index", 0)
    flags = assessment.get("risk_flags", [])
    locality = assessment.get("locality", "the subject locality")
    prop_type = assessment.get("prop_type", "property").replace("_", " ")

    liq_label = "highly liquid" if rpi >= 75 else "moderately liquid" if rpi >= 50 else "relatively illiquid"
    ltv = "up to 65%" if rpi >= 75 and not flags else "up to 55%" if rpi >= 50 else "up to 45%"
    flag_note = (f"The assessment flagged {len(flags)} concern(s): "
                 + ", ".join(f['flag'].replace('_',' ') for f in flags[:2]) + ".") \
                if flags else "No automated risk flags were detected."

    return {
        "summary": (
            f"The subject property is a {prop_type} located in {locality}, Pune, "
            f"with an estimated market value range of {fmt_inr(mv[0])} to {fmt_inr(mv[1])}. "
            f"The asset is considered {liq_label} with a Resale Potential Index of {rpi:.0f}/100, "
            f"supported by infrastructure proximity and locality demand signals."
        ),
        "recommendation": (
            f"Collateral is {'acceptable' if rpi >= 50 and len(flags) == 0 else 'marginally acceptable'} "
            f"for LAP underwriting. Recommended maximum LTV: {ltv}. "
            f"{'Full title search and physical verification recommended before sanction.' if flags else 'Standard due diligence applies.'}"
        ),
        "risk_narrative": (
            f"{flag_note} "
            f"Liquidity risk is {'low' if rpi >= 75 else 'moderate' if rpi >= 50 else 'elevated'}, "
            f"with estimated time to liquidate of "
            f"{assessment.get('estimated_time_to_sell_days', [60,120])[0]}–"
            f"{assessment.get('estimated_time_to_sell_days', [60,120])[1]} days under normal market conditions."
        ),
        "key_points": [
            f"Market value range: {fmt_inr(mv[0])} – {fmt_inr(mv[1])} (AI model MAPE: {assessment.get('model_mape_pct','8.3')}%)",
            f"Resale Potential Index: {rpi:.0f}/100 — {liq_label}",
            f"Circle rate floor: ₹{assessment.get('enrichment',{}).get('circle_rate_per_sqft',0):,}/sqft (IGR Maharashtra 2024-25)",
            f"Risk flags: {len(flags)} detected — {'review required' if flags else 'clear'}",
        ],
    }
