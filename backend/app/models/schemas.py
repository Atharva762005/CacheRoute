"""
PropIQ Pydantic Models
All request and response schemas for the API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


# ── Request Models ─────────────────────────────────────────────────────────

class PropertyInput(BaseModel):
    locality: str = Field(
        ..., example="Baner",
        description="Pune locality. Supported: Baner, Kothrud, Koregaon Park, Wakad, Hinjewadi, Hadapsar, Wagholi, Viman Nagar, Shivajinagar, Aundh, Pimpri, Chinchwad, Katraj, Talegaon, Chakan, Ambegaon"
    )
    prop_type: Literal[
        "1bhk_apartment", "2bhk_apartment", "3bhk_apartment", "4bhk_apartment",
        "villa", "shop", "office", "plot"
    ] = Field(
        ..., example="2bhk_apartment",
        description="One of: 1bhk_apartment, 2bhk_apartment, 3bhk_apartment, 4bhk_apartment, villa, shop, office, plot"
    )
    size_sqft: float = Field(..., gt=100, lt=50000, example=850, description="Carpet/built-up area in sqft")
    age_years: float = Field(..., ge=0, le=80, example=8, description="Building age in years")
    floor_num: int = Field(default=3, ge=0, le=50, example=3, description="Floor number (0 = ground)")
    is_freehold: int = Field(default=1, ge=0, le=1, example=1, description="1=Freehold, 0=Leasehold")
    is_rera_registered: int = Field(default=1, ge=0, le=1, example=1, description="1=RERA registered, 0=Not registered")
    occupancy: Literal["self_occupied", "rented", "vacant"] = Field(
        default="self_occupied", example="self_occupied", description="self_occupied | rented | vacant"
    )
    rental_yield_pct: float = Field(default=0.0, ge=0, le=15, example=3.5, description="Annual rental yield % (if rented)")
    # Gap 5 fix: Accept coordinates directly to skip geocoding
    geo_lat: Optional[float] = Field(default=None, example=18.559, description="Latitude (optional — skips geocoding if provided)")
    geo_lon: Optional[float] = Field(default=None, example=73.787, description="Longitude (optional — skips geocoding if provided)")

    class Config:
        json_schema_extra = {
            "example": {
                "locality": "Baner",
                "prop_type": "2bhk_apartment",
                "size_sqft": 850,
                "age_years": 8,
                "floor_num": 5,
                "is_freehold": 1,
                "is_rera_registered": 1,
                "occupancy": "self_occupied",
                "rental_yield_pct": 0.0,
                "geo_lat": None,
                "geo_lon": None,
            }
        }


# ── Response Models ────────────────────────────────────────────────────────

class KeyDriver(BaseModel):
    feature: str
    impact_inr: int
    direction: str  # "positive" | "negative"

class RiskFlag(BaseModel):
    flag: str
    severity: str  # "high" | "medium" | "low"
    detail: str

class EnrichmentData(BaseModel):
    zone_tier: str
    circle_rate_per_sqft: int
    infra_score: float
    listing_density: float
    neighbourhood_quality_score: Optional[float]
    geo: Dict[str, Any]

class CVAssessment(BaseModel):
    condition: str
    quality_score: float
    condition_probabilities: Dict[str, float]
    valuation_adjustment_factor: float
    adjustment_description: str
    cv_confidence: float
    image_analyzed: bool

class ValuationResponse(BaseModel):
    request_id: str
    locality: str
    prop_type: str
    size_sqft: float
    market_value_range: List[int]
    market_value_mid: int
    distress_value_range: List[int]
    resale_potential_index: float
    estimated_time_to_sell_days: List[int]
    confidence_score: float
    price_per_sqft_estimate: int
    key_drivers: List[Dict[str, Any]]
    # Gap 7 fix: flat string list matching problem statement sample format
    key_drivers_summary: List[str]
    shap_values: Dict[str, float]
    risk_flags: List[Dict[str, Any]]
    # Gap 8 fix: flat string list matching problem statement sample format
    risk_flags_summary: List[str]
    enrichment: Dict[str, Any]
    cv_assessment: Optional[Dict[str, Any]]
    processing_time_ms: int
    model_mape_pct: Optional[float]

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "A1B2C3D4",
                "locality": "Baner",
                "prop_type": "2bhk_apartment",
                "size_sqft": 850,
                "market_value_range": [17200000, 20800000],
                "market_value_mid": 19000000,
                "distress_value_range": [14276000, 17264000],
                "resale_potential_index": 85.2,
                "estimated_time_to_sell_days": [25, 60],
                "confidence_score": 0.87,
                "price_per_sqft_estimate": 22353,
                "key_drivers": [
                    {"feature": "circle_rate_per_sqft", "impact_inr": 4200000, "direction": "positive"},
                    {"feature": "infra_score", "impact_inr": 1800000, "direction": "positive"},
                    {"feature": "age_years", "impact_inr": -600000, "direction": "negative"},
                ],
                "key_drivers_summary": ["proximity_to_metro", "standard_2bhk_configuration", "mid_age_building"],
                "risk_flags": [],
                "risk_flags_summary": [],
                "processing_time_ms": 312,
                "model_mape_pct": 8.3
            }
        }


class LocalityInfo(BaseModel):
    locality: str
    zone_tier: str
    residential_apartment_circle_rate: int

class LocalitiesResponse(BaseModel):
    localities: List[LocalityInfo]
    city: str
    total: int

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str