"""
SQLAlchemy ORM models for properties, valuations, and audit logs.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.db import Base

class CircleRate(Base):
    """Replacement for static india_circle_rates.py"""
    __tablename__ = "circle_rates"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True, nullable=False)
    locality = Column(String, index=True, unique=True, nullable=False)
    zone_tier = Column(String, nullable=False) # prime, mid, peripheral
    residential_apartment = Column(Float, nullable=False)
    commercial_shop = Column(Float, nullable=False)
    commercial_office = Column(Float, nullable=False)
    industrial = Column(Float, nullable=False)
    residential_plot = Column(Float, nullable=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    locality = Column(String, index=True, nullable=False)
    prop_type = Column(String, index=True, nullable=False)
    size_sqft = Column(Float, nullable=False)
    age_years = Column(Float, nullable=False)
    floor_num = Column(Integer, default=3)
    is_freehold = Column(Integer, default=1)
    is_rera_registered = Column(Integer, default=1)
    occupancy = Column(String, default="self_occupied")
    rental_yield_pct = Column(Float, default=0.0)
    geo_lat = Column(Float, nullable=True)
    geo_lon = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ValuationResult(Base):
    __tablename__ = "valuation_results"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    base_value_estimate = Column(Float, nullable=False)
    p10_estimate = Column(Float, nullable=False)
    p90_estimate = Column(Float, nullable=False)
    price_per_sqft_estimate = Column(Float, nullable=False)
    cv_condition = Column(String, nullable=True)
    cv_adjustment_factor = Column(Float, nullable=True)
    rpi_score = Column(Float, nullable=True)
    max_ltv_pct = Column(Float, nullable=True)
    shap_values = Column(JSON, nullable=True)
    credit_memo = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, index=True, nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
