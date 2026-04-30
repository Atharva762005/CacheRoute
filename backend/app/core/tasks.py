"""
Celery tasks for PropIQ background processing.
These tasks run in worker processes, separate from the FastAPI web server.
"""

import time
import uuid
from app.core.celery_app import celery_app
from app.data.india_circle_rates import get_circle_rate, ZONE_MULTIPLIERS
from app.services.comps_engine import find_comps, get_comp_stats
from app.services.price_trends import generate_price_trend, get_trend_summary
from app.services.ltv_audit import calculate_ltv, log_assessment
from app.services.llm_narration import generate_credit_memo as _generate_credit_memo_async
from app.core.config import settings
from app.ml.valuation_model import PropIQModel

# Module-level model cache for the worker process
_worker_model = None

def _get_worker_model() -> PropIQModel:
    global _worker_model
    if _worker_model is None:
        _worker_model = PropIQModel.load(str(settings.MODEL_DIR))
    return _worker_model


@celery_app.task(bind=True, name="propiq.assess_single")
def assess_single_task(self, property_data: dict) -> dict:
    """
    Celery task that processes a single property assessment.
    Mirrors _run_assessment() but runs synchronously in a worker process.
    """
    try:
        t0 = time.time()
        request_id = str(uuid.uuid4())[:8].upper()

        locality = property_data["locality"]
        prop_type = property_data["prop_type"]
        size_sqft = property_data["size_sqft"]
        age_years = property_data["age_years"]
        floor_num = property_data.get("floor_num", 3)
        is_freehold = property_data.get("is_freehold", 1)
        is_rera_registered = property_data.get("is_rera_registered", 1)
        occupancy = property_data.get("occupancy", "self_occupied")
        rental_yield_pct = property_data.get("rental_yield_pct", 0.0)

        cr_data = get_circle_rate(locality, prop_type)
        zone_tier = cr_data["zone_tier"]

        # Simplified enrichment (no async in worker)
        infra_score = settings.INFRA_SCORE_FALLBACK.get(zone_tier, 50.0)
        listing_density = {"prime": 0.75, "mid": 0.55, "peripheral": 0.35}.get(zone_tier, 0.5)
        location_mult = ZONE_MULTIPLIERS[zone_tier]["mid"]
        is_standard = 1 if prop_type in ["2bhk_apartment", "3bhk_apartment"] else 0

        model_input = {
            "locality": locality, "zone_tier": zone_tier, "prop_type": prop_type,
            "size_sqft": size_sqft, "age_years": age_years, "floor_num": floor_num,
            "is_freehold": is_freehold, "is_rera_registered": is_rera_registered,
            "rental_yield_pct": rental_yield_pct, "infra_score": infra_score,
            "listing_density": listing_density, "is_standard_config": is_standard,
            "circle_rate_per_sqft": cr_data["circle_rate_per_sqft"],
            "location_multiplier": location_mult,
        }

        prediction = _get_worker_model().predict(model_input)

        result = {
            "request_id": request_id, "locality": cr_data["locality"],
            "city": cr_data.get("city", "Pune"),
            "prop_type": prop_type, "size_sqft": size_sqft,
            "age_years": age_years, "floor_num": floor_num,
            "is_freehold": is_freehold, "is_rera_registered": is_rera_registered,
            "occupancy": occupancy, "rental_yield_pct": rental_yield_pct,
            **prediction,
            "enrichment": {
                "zone_tier": zone_tier,
                "circle_rate_per_sqft": cr_data["circle_rate_per_sqft"],
                "infra_score": infra_score, "listing_density": listing_density,
                "city": cr_data.get("city", "Pune"),
            },
            "cv_assessment": None,
        }

        # Comps and trends (synchronous in worker)
        comps = find_comps(locality, prop_type, size_sqft, age_years)
        trend_data = generate_price_trend(
            locality, zone_tier, cr_data.get("city", "Pune"),
            result["price_per_sqft_estimate"], months=24)

        result["comps"] = comps
        result["comp_stats"] = get_comp_stats(locality, prop_type)
        result["price_trend"] = trend_data
        result["trend_summary"] = get_trend_summary(trend_data)
        result["ltv_analysis"] = calculate_ltv(
            result["market_value_mid"], result["distress_value_range"],
            cr_data["property_type_key"], zone_tier, result.get("risk_flags", []))
        result["credit_memo"] = None  # Skip LLM in batch workers to save API calls
        result["processing_time_ms"] = int((time.time() - t0) * 1000)
        result["status"] = "success"

        log_assessment(result, "/assess/batch")
        return result

    except Exception as e:
        return {
            "locality": property_data.get("locality", "unknown"),
            "prop_type": property_data.get("prop_type", "unknown"),
            "status": "error",
            "error": str(e),
        }


@celery_app.task(bind=True, name="propiq.assess_batch")
def assess_batch_task(self, properties: list) -> dict:
    """
    Celery task that processes a batch of properties sequentially in a worker.
    Updates task state with progress for polling.
    """
    total = len(properties)
    results = []

    for idx, prop_data in enumerate(properties):
        self.update_state(
            state="PROGRESS",
            meta={"current": idx, "total": total, "percent": int((idx / total) * 100)}
        )
        result = assess_single_task.apply(args=[prop_data]).get()
        results.append(result)

    success_count = sum(1 for r in results if r.get("status") == "success")
    return {
        "batch_size": total,
        "results": results,
        "success_count": success_count,
        "status": "completed",
    }
