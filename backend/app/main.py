"""
PropIQ — AI Collateral Intelligence Engine  v2.0
FastAPI Backend — Complete with all new endpoints
"""
import asyncio, time, uuid, sys, json
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response as FastAPIResponse

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.security import get_api_key
from app.models.schemas import PropertyInput, ValuationResponse, HealthResponse
from app.data.india_circle_rates import get_circle_rate, ALL_CIRCLE_RATES, ZONE_MULTIPLIERS, get_localities_by_city
from app.ml.valuation_model import PropIQModel
from app.ml.cv_module import get_cv_analyzer
from app.services.enrichment import enrich_property
from app.services.pdf_report import generate_pdf_report
from app.services.llm_narration import generate_credit_memo
from app.services.comps_engine import find_comps, get_comp_stats
from app.services.price_trends import generate_price_trend, get_trend_summary
from app.services.ltv_audit import calculate_ltv, log_assessment, get_recent_assessments, get_audit_stats

app = FastAPI(
    title="PropIQ — AI Collateral Intelligence Engine",
    description="""
## PropIQ v2.0 — Agentic Collateral Valuation for NBFC/LAP Underwriting

**3 cities · 39 localities · MAPE 8.3% · 90-second assessment**

### Authentication
Pass `X-API-Key: propiq-demo-2026` in headers. Unauthenticated requests allowed (demo mode, 50 req/min).

### Core Endpoints
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/assess` | Full valuation (JSON) |
| `POST /api/v1/assess/image` | Valuation + CV condition |
| `POST /api/v1/assess/pdf` | Valuation + PDF download |
| `POST /api/v1/assess/narrate` | Valuation + LLM credit memo |
| `POST /api/v1/assess/ltv` | Valuation + LTV calculation |
| `POST /api/v1/assess/batch` | Bulk assessment (up to 50) |
| `GET /api/v1/comps` | Comparable sales |
| `GET /api/v1/trends/{locality}` | 24-month price trend |
| `GET /api/v1/localities` | All supported localities |
| `GET /api/v1/audit/recent` | Recent assessment log |
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_model: Optional[PropIQModel] = None

def get_model() -> PropIQModel:
    global _model
    if _model is None:
        _model = PropIQModel.load(str(settings.MODEL_DIR))
    return _model

async def _run_assessment(prop: PropertyInput) -> dict:
    t0 = time.time()
    request_id = str(uuid.uuid4())[:8].upper()
    cr_data = get_circle_rate(prop.locality, prop.prop_type)
    zone_tier = cr_data["zone_tier"]
    enrichment = await enrich_property(prop.locality, zone_tier=zone_tier)
    infra_score = enrichment.get("infra_score", 0.0)
    if infra_score == 0.0:
        infra_score = settings.INFRA_SCORE_FALLBACK.get(zone_tier, 50.0)
    listing_density = enrichment.get("listing_density", 0.5)
    location_mult = ZONE_MULTIPLIERS[zone_tier]["mid"]
    is_standard = 1 if prop.prop_type in ["2bhk_apartment", "3bhk_apartment"] else 0
    model_input = {
        "locality": prop.locality, "zone_tier": zone_tier, "prop_type": prop.prop_type,
        "size_sqft": prop.size_sqft, "age_years": prop.age_years, "floor_num": prop.floor_num,
        "is_freehold": prop.is_freehold, "is_rera_registered": prop.is_rera_registered,
        "rental_yield_pct": prop.rental_yield_pct, "infra_score": infra_score,
        "listing_density": listing_density, "is_standard_config": is_standard,
        "circle_rate_per_sqft": cr_data["circle_rate_per_sqft"], "location_multiplier": location_mult,
    }
    prediction = get_model().predict(model_input)
    return {
        "request_id": request_id, "locality": cr_data["locality"],
        "city": cr_data.get("city", "Pune"),
        "prop_type": prop.prop_type, "size_sqft": prop.size_sqft,
        **prediction,
        "enrichment": {
            "zone_tier": zone_tier, "circle_rate_per_sqft": cr_data["circle_rate_per_sqft"],
            "infra_score": infra_score, "listing_density": listing_density,
            "geo": enrichment.get("geo", {}), "city": cr_data.get("city", "Pune"),
        },
        "cv_assessment": None,
        "processing_time_ms": int((time.time() - t0) * 1000),
    }

# ── System ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {"service": "PropIQ v2.0", "cities": ["Pune", "Mumbai", "Bangalore"],
            "localities": len(ALL_CIRCLE_RATES), "docs": "/docs"}

@app.get("/api/v1/health", tags=["System"])
def health():
    return {"status": "ok", "service": "PropIQ", "version": "2.0.0",
            "model_mape_pct": 8.3, "cities_supported": 3, "localities": len(ALL_CIRCLE_RATES)}

# ── Reference Data ─────────────────────────────────────────────────────────

@app.get("/api/v1/localities", tags=["Reference"])
def list_localities(city: Optional[str] = None):
    by_city = get_localities_by_city()
    if city:
        city_title = city.title()
        return {"localities": by_city.get(city_title, []), "city": city_title}
    return {"localities_by_city": by_city, "total": len(ALL_CIRCLE_RATES)}

# ── Core Valuation ─────────────────────────────────────────────────────────

@app.post("/api/v1/assess", tags=["Valuation"], summary="Full collateral assessment")
async def assess_property(prop: PropertyInput, auth=Depends(get_api_key)):
    try:
        result = await _run_assessment(prop)
        log_assessment(result, "/assess")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/assess/image", tags=["Valuation"], summary="Assessment + CV image scoring")
async def assess_with_image(
    locality: str = Form(...), prop_type: str = Form(...),
    size_sqft: float = Form(...), age_years: float = Form(...),
    floor_num: int = Form(default=3), is_freehold: int = Form(default=1),
    is_rera_registered: int = Form(default=1), occupancy: str = Form(default="self_occupied"),
    rental_yield_pct: float = Form(default=0.0),
    image: UploadFile = File(...),
    auth=Depends(get_api_key),
):
    try:
        t0 = time.time()
        prop = PropertyInput(locality=locality, prop_type=prop_type, size_sqft=size_sqft,
            age_years=age_years, floor_num=floor_num, is_freehold=is_freehold,
            is_rera_registered=is_rera_registered, occupancy=occupancy, rental_yield_pct=rental_yield_pct)
        result = await _run_assessment(prop)
        
        image_bytes = await image.read()
        cv_result = get_cv_analyzer().analyze_image(image_bytes)
        adj = cv_result.get("valuation_adjustment_factor", 1.0)
        if adj != 1.0:
            result["market_value_range"] = [round(v * adj) for v in result["market_value_range"]]
            result["market_value_mid"] = round(result["market_value_mid"] * adj)
            result["distress_value_range"] = [round(v * adj) for v in result["distress_value_range"]]
            result["price_per_sqft_estimate"] = round(result["price_per_sqft_estimate"] * adj)
        result["cv_assessment"] = cv_result

        cr_data = get_circle_rate(prop.locality, prop.prop_type)
        comps_task = asyncio.to_thread(find_comps, prop.locality, prop.prop_type, prop.size_sqft, prop.age_years)
        trend_data = generate_price_trend(
            prop.locality, cr_data["zone_tier"], cr_data.get("city", "Pune"),
            result["price_per_sqft_estimate"], months=24)
        memo_task = generate_credit_memo(result)

        comps, memo = await asyncio.gather(comps_task, memo_task)

        result["comps"] = comps
        result["comp_stats"] = get_comp_stats(prop.locality, prop.prop_type)
        result["price_trend"] = trend_data
        result["trend_summary"] = get_trend_summary(trend_data)
        result["ltv_analysis"] = calculate_ltv(
            result["market_value_mid"], result["distress_value_range"],
            cr_data["property_type_key"], cr_data["zone_tier"], result.get("risk_flags", []))
        result["credit_memo"] = memo
        result["processing_time_ms"] = int((time.time() - t0) * 1000)

        log_assessment(result, "/assess/image", has_image=True)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/assess/pdf", tags=["Valuation"], summary="Assessment + PDF report download")
async def assess_and_pdf(prop: PropertyInput, auth=Depends(get_api_key)):
    try:
        result = await _run_assessment(prop)
        log_assessment(result, "/assess/pdf")
        pdf_bytes = generate_pdf_report(result)
        filename = f"PropIQ_{result['locality']}_{result['request_id']}.pdf"
        return FastAPIResponse(content=pdf_bytes, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/assess/narrate", tags=["Valuation"], summary="Assessment + LLM credit memo")
async def assess_and_narrate(prop: PropertyInput, auth=Depends(get_api_key)):
    try:
        result = await _run_assessment(prop)
        memo = await generate_credit_memo(result)
        result["credit_memo"] = memo
        log_assessment(result, "/assess/narrate")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/assess/ltv", tags=["Valuation"], summary="Assessment + LTV calculation")
async def assess_and_ltv(prop: PropertyInput, auth=Depends(get_api_key)):
    try:
        result = await _run_assessment(prop)
        cr_data = get_circle_rate(prop.locality, prop.prop_type)
        ltv = calculate_ltv(
            market_value_mid=result["market_value_mid"],
            distress_value_range=result["distress_value_range"],
            prop_type_key=cr_data["property_type_key"],
            zone_tier=cr_data["zone_tier"],
            risk_flags=result.get("risk_flags", []),
        )
        result["ltv_analysis"] = ltv
        log_assessment(result, "/assess/ltv")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/assess/full", tags=["Valuation"], summary="Complete assessment — all outputs in one call")
async def assess_full(prop: PropertyInput, auth=Depends(get_api_key)):
    """The kitchen-sink endpoint: valuation + LTV + comps + trends + narration."""
    try:
        t0 = time.time()
        result = await _run_assessment(prop)
        cr_data = get_circle_rate(prop.locality, prop.prop_type)

        # Run all enrichments in parallel
        comps_task = asyncio.to_thread(find_comps, prop.locality, prop.prop_type, prop.size_sqft, prop.age_years)
        trend_data = generate_price_trend(
            prop.locality, cr_data["zone_tier"], cr_data.get("city", "Pune"),
            result["price_per_sqft_estimate"], months=24)
        memo_task = generate_credit_memo(result)

        comps, memo = await asyncio.gather(comps_task, memo_task)

        result["comps"] = comps
        result["comp_stats"] = get_comp_stats(prop.locality, prop.prop_type)
        result["price_trend"] = trend_data
        result["trend_summary"] = get_trend_summary(trend_data)
        result["ltv_analysis"] = calculate_ltv(
            result["market_value_mid"], result["distress_value_range"],
            cr_data["property_type_key"], cr_data["zone_tier"], result.get("risk_flags", []))
        result["credit_memo"] = memo
        result["processing_time_ms"] = int((time.time() - t0) * 1000)
        log_assessment(result, "/assess/full")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Batch ──────────────────────────────────────────────────────────────────

@app.post("/api/v1/assess/batch", tags=["Batch"], summary="Bulk assessment (up to 50 properties)")
async def assess_batch(properties: List[PropertyInput], auth=Depends(get_api_key)):
    if len(properties) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 properties per batch request")
        
    async def _process_single(prop):
        try:
            t0 = time.time()
            result = await _run_assessment(prop)
            cr_data = get_circle_rate(prop.locality, prop.prop_type)
            
            comps_task = asyncio.to_thread(find_comps, prop.locality, prop.prop_type, prop.size_sqft, prop.age_years)
            trend_data = generate_price_trend(
                prop.locality, cr_data["zone_tier"], cr_data.get("city", "Pune"),
                result["price_per_sqft_estimate"], months=24)
            memo_task = generate_credit_memo(result)

            comps, memo = await asyncio.gather(comps_task, memo_task)

            result["comps"] = comps
            result["comp_stats"] = get_comp_stats(prop.locality, prop.prop_type)
            result["price_trend"] = trend_data
            result["trend_summary"] = get_trend_summary(trend_data)
            result["ltv_analysis"] = calculate_ltv(
                result["market_value_mid"], result["distress_value_range"],
                cr_data["property_type_key"], cr_data["zone_tier"], result.get("risk_flags", []))
            result["credit_memo"] = memo
            result["processing_time_ms"] = int((time.time() - t0) * 1000)
            result["status"] = "success"
            return result
        except Exception as e:
            return {"locality": prop.locality, "prop_type": prop.prop_type,
                    "status": "error", "error": str(e)}

    results = await asyncio.gather(*[_process_single(p) for p in properties])
    
    return {"batch_size": len(properties), "results": results,
            "success_count": sum(1 for r in results if r.get("status") == "success")}

# ── Comps ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/comps", tags=["Market Data"], summary="Find comparable properties")
async def get_comps(
    locality: str, prop_type: str = "2bhk_apartment",
    size_sqft: float = 850, age_years: float = 10, n: int = 5,
):
    try:
        comps = find_comps(locality, prop_type, size_sqft, age_years, n)
        stats = get_comp_stats(locality, prop_type)
        return {"locality": locality, "prop_type": prop_type, "comps": comps,
                "market_stats": stats, "count": len(comps)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Trends ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/trends/{locality}", tags=["Market Data"], summary="24-month price trend")
async def get_trends(locality: str, prop_type: str = "2bhk_apartment", months: int = 24):
    try:
        cr = get_circle_rate(locality, prop_type)
        base_price = cr["circle_rate_per_sqft"] * ZONE_MULTIPLIERS[cr["zone_tier"]]["mid"]
        trend = generate_price_trend(
            locality, cr["zone_tier"], cr.get("city", "Pune"),
            base_price, months=min(months, 36))
        summary = get_trend_summary(trend)
        return {"locality": cr["locality"], "city": cr.get("city", "Pune"),
                "zone_tier": cr["zone_tier"], "trend": trend, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Audit ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/audit/recent", tags=["Audit"], summary="Recent assessment log (RBI audit trail)")
async def audit_recent(limit: int = 20, auth=Depends(get_api_key)):
    return {"assessments": get_recent_assessments(limit), "stats": get_audit_stats()}


# ── Chat Assistant ──────────────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional

class ChatMessage(_BaseModel):
    role: str          # "user" | "assistant"
    content: str

class ChatRequest(_BaseModel):
    messages: list[ChatMessage]
    form_context: dict = {}           # current property form state
    assessment_result: _Optional[dict] = None  # full assessment JSON if available

_CHAT_SYSTEM_PROMPT = """You are PropIQ, an expert AI property collateral assessment assistant for Poonawalla Fincorp.
You help loan officers evaluate properties for LAP (Loan Against Property) underwriting in India (Pune, Mumbai, Bangalore).

Your role:
- If assessment data is provided below, use it to answer specific questions accurately (valuations, risk, LTV, trends, etc.).
- Help users describe properties and extract: locality, type, size (sqft), building age, floor.
- Answer questions about collateral valuation, LTV norms, market trends, RERA, IGR circle rates, and risk factors.
- Be concise, professional, and precise. Use Indian real-estate terminology (₹ Cr / L, BHK, LAP, RERA, IGR, etc.).
- When a user asks about "the property" or "the assessment", refer ONLY to the assessment data provided — do not invent numbers.
- Keep replies under 150 words unless the user explicitly asks for more detail."""


def _build_assessment_context(r: dict) -> str:
    """Convert assessment JSON into a compact text grounding block for the LLM."""
    if not r:
        return ""

    def fmt(v):
        if v >= 10_000_000: return f"₹{v/10_000_000:.2f} Cr"
        if v >= 100_000:    return f"₹{v/100_000:.2f} L"
        return f"₹{v:,}"

    mv  = r.get("market_value_range", [0, 0])
    dv  = r.get("distress_value_range", [0, 0])
    mid = r.get("market_value_mid", 0)
    rpi = r.get("resale_potential_index", 0)
    conf = r.get("confidence_score", 0)
    ppsf = r.get("price_per_sqft_estimate", 0)
    flags = r.get("risk_flags", [])
    drivers = r.get("key_drivers", [])
    enr = r.get("enrichment", {})
    ltv = r.get("ltv_analysis", {})
    comps = r.get("comps", [])
    trend = r.get("trend_summary", {})
    memo = r.get("credit_memo", {})
    cv = r.get("cv_assessment", {})

    lines = [
        "=== PROPIQ ASSESSMENT RESULTS (use these numbers to answer user questions) ===",
        f"Property : {r.get('prop_type','').replace('_',' ').title()} in {r.get('locality','')}, {r.get('city','Pune')}",
        f"Size     : {r.get('size_sqft',0):,} sqft",
        f"Market Value Range : {fmt(mv[0])} – {fmt(mv[1])}  (mid: {fmt(mid)})",
        f"Distress Value     : {fmt(dv[0])} – {fmt(dv[1])}",
        f"Price/sqft estimate: ₹{ppsf:,}/sqft",
        f"Resale Potential Index (RPI): {rpi}/100  ({'Highly Liquid' if rpi>=75 else 'Moderate' if rpi>=50 else 'Illiquid'})",
        f"Confidence Score   : {conf:.0%}",
        f"Zone Tier          : {enr.get('zone_tier','').title()}",
        f"Circle Rate        : ₹{enr.get('circle_rate_per_sqft',0):,}/sqft (IGR Maharashtra)",
        f"Infra Score        : {enr.get('infra_score',0):.0f}/100",
    ]

    if flags:
        def _flag_str(fl):
            sev = fl.get('severity', '')
            suffix = f' (severity: {sev})' if sev else ''
            return fl['flag'].replace('_', ' ') + suffix
        lines.append(f"Risk Flags ({len(flags)}): " + "; ".join(_flag_str(fl) for fl in flags))
    else:
        lines.append("Risk Flags: None detected")

    if drivers:
        lines.append("Key Value Drivers: " + ", ".join(f"{d['feature'].replace('_',' ')} ({d.get('direction','+')})" for d in drivers[:5]))

    if ltv:
        lines.append(f"Recommended LTV    : {ltv.get('recommended_ltv_pct',0):.1f}%  (max loan: {fmt(ltv.get('max_loan_amount',0))})")
        lines.append(f"LTV Risk Band      : {ltv.get('risk_band','')}")

    if comps:
        lines.append(f"Comparable Sales   : {len(comps)} comps found, avg ₹{sum(c.get('price_per_sqft',0) for c in comps)//max(len(comps),1):,}/sqft")

    if trend:
        lines.append(f"Price Trend (24M)  : {trend.get('direction','').title()}, {trend.get('appreciation_pct',0):.1f}% change, momentum: {trend.get('momentum','')}")

    if cv and cv.get("condition"):
        lines.append(f"CV Image Condition : {cv.get('condition','').title()} (adjustment: {cv.get('valuation_adjustment_factor',1.0):.2f}x)")

    if memo and memo.get("summary"):
        lines.append(f"Credit Memo Summary: {memo['summary']}")
        lines.append(f"Recommendation     : {memo.get('recommendation','')}")

    lines.append("=== END OF ASSESSMENT DATA ===")
    return "\n".join(lines)


# ── Agentic Auto-Assessment — Property Field Extraction ───────────────────

_EXTRACTION_SYSTEM_PROMPT = """You are a property data extraction engine for PropIQ (India real estate).
Analyze the user message. If they describe a SPECIFIC property for valuation/assessment, extract details.
Return ONLY valid JSON.

RULES:
- Return {"found": false} if the user is greeting, asking a general question, or NOT describing a specific property
- Return {"found": true, ...} ONLY when the user provides details of a property they want valued
- You MUST extract at least: locality, prop_type, size_sqft, and age_years to return found=true
- Match locality names EXACTLY to the supported list (pick the closest match)

Supported localities:
Pune: Koregaon Park, Shivajinagar, Baner, Kothrud, Aundh, Viman Nagar, Wakad, Hinjewadi, Hadapsar, Pimpri, Chinchwad, Katraj, Wagholi, Talegaon, Chakan, Ambegaon
Mumbai: Bandra West, Worli, Powai, Andheri West, Andheri East, Thane, Navi Mumbai, Dadar, Borivali, Mira Road, Virar, Kharghar
Bangalore: Koramangala, Indiranagar, Whitefield, HSR Layout, Electronic City, Marathahalli, Sarjapur Road, Yelahanka, Bannerghatta, Devanahalli, Tumkur Road

Property types: 1bhk_apartment, 2bhk_apartment, 3bhk_apartment, 4bhk_apartment, villa, shop, office, plot
Mapping: "flat"/"apartment" without BHK → 2bhk_apartment, "3 bedroom"/"3BR"/"3BHK" → 3bhk_apartment, "bungalow" → villa, "commercial"/"showroom" → shop

For found=true return:
{"found": true, "locality": "ExactName", "prop_type": "type_key", "size_sqft": number, "age_years": number, "floor_num": number, "is_freehold": 1, "is_rera_registered": 1}

Defaults when not mentioned: floor_num=3, is_freehold=1, is_rera_registered=1
For found=false return: {"found": false}"""


async def _extract_property_fields(message: str, api_key: str):
    """Use Groq fast model to extract structured property fields from natural language."""
    if len(message.strip()) < 15:
        return None
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)
        completion = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            max_tokens=200,
            temperature=0.05,
            response_format={"type": "json_object"},
        )
        text = completion.choices[0].message.content.strip()
        result = json.loads(text)
        if (result.get("found")
                and result.get("locality")
                and result.get("prop_type")
                and result.get("size_sqft")
                and result.get("age_years") is not None):
            print(f"[Chat] Extracted property: {result.get('locality')} {result.get('prop_type')}")
            return result
    except Exception as e:
        print(f"[Chat] Extraction error (non-fatal): {e}")
    return None


@app.post("/api/v1/chat", tags=["Chat"], summary="Groq-powered chat assistant with agentic auto-assessment")
async def chat_assistant(req: ChatRequest):
    import os
    from pathlib import Path as _Path
    from dotenv import load_dotenv as _load_dotenv

    _proj_root = _Path(__file__).parent.parent.parent
    _load_dotenv(_proj_root / ".env", override=False)

    api_key = os.getenv("GROQ_API_KEY", "")
    print(f"[Chat] GROQ_API_KEY: {'SET' if api_key else 'MISSING'}")

    # ── Build system prompt ────────────────────────────────────────────────
    system_msg = _CHAT_SYSTEM_PROMPT

    # Append form context
    ctx_parts = []
    f = req.form_context
    if f.get("locality"):    ctx_parts.append(f"Locality: {f['locality']}")
    if f.get("prop_type"):   ctx_parts.append(f"Type: {f['prop_type'].replace('_',' ')}")
    if f.get("size_sqft"):   ctx_parts.append(f"Size: {f['size_sqft']} sqft")
    if f.get("age_years") is not None: ctx_parts.append(f"Age: {f['age_years']} years")
    if ctx_parts:
        system_msg += "\n\nCurrent form state: " + ", ".join(ctx_parts)

    # Append assessment grounding data if available
    assessment_ctx = _build_assessment_context(req.assessment_result or {})
    if assessment_ctx:
        system_msg += "\n\n" + assessment_ctx

    if not api_key:
        return {"reply": "⚠️ GROQ_API_KEY not found. Please add it to your .env file and restart the server."}

    try:
        # ── Step 1: Agentic extraction — detect property descriptions ──────
        last_user_msg = ""
        for m in reversed(req.messages):
            if m.role == "user":
                last_user_msg = m.content
                break

        extraction = await _extract_property_fields(last_user_msg, api_key)

        if extraction:
            fields = {k: v for k, v in extraction.items() if k != "found" and v is not None}
            pt = fields.get("prop_type", "").replace("_", " ").title()
            loc = fields.get("locality", "")
            sz = fields.get("size_sqft", 0)
            age = fields.get("age_years", 0)
            reply = (
                f"🎯 **Auto-detected property:**\n"
                f"• **{pt}** in **{loc}**\n"
                f"• {sz:,.0f} sqft · {age} years old\n"
                f"• Floor {fields.get('floor_num', 3)} · "
                f"{'Freehold' if fields.get('is_freehold', 1) else 'Leasehold'} · "
                f"{'RERA ✓' if fields.get('is_rera_registered', 1) else 'No RERA'}\n\n"
                f"⚡ **Running full assessment automatically...**"
            )
            return {"reply": reply, "action": "auto_assess", "extracted_fields": fields}

        # ── Step 2: Normal Groq chat ───────────────────────────────────────
        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)
        messages_payload = [{"role": "system", "content": system_msg}]
        for m in req.messages[-12:]:   # last 12 turns for good context
            messages_payload.append({"role": m.role, "content": m.content})

        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
            max_tokens=250,
            temperature=0.4,
        )
        reply = completion.choices[0].message.content.strip()
        return {"reply": reply}
    except Exception as e:
        error_detail = str(e)
        print(f"[Chat] LLM error: {error_detail}")
        return {"reply": f"I'm having trouble connecting to the AI right now. Error: {error_detail[:120]}"}