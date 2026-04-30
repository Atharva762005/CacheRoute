"""
PropIQ Enrichment Services
- GeoEnricher: geocoding via Nominatim (skipped if lat/lon provided directly)
- InfraScorer: infrastructure proximity via OSM Overpass API
- NeighbourhoodQualityScorer: planned vs unplanned zone quality signal
- MarketSignalService: listing density proxy
- All services are async and fire in parallel
"""

import asyncio
import aiohttp
import json
import math
from typing import Optional
from functools import lru_cache

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

INFRA_QUERIES = {
    "metro_station": ('node["railway"="station"]', 2000, 15),
    "metro_halt":    ('node["railway"="halt"]', 1500, 10),
    "hospital":      ('node["amenity"="hospital"]', 3000, 12),
    "school":        ('node["amenity"="school"]', 1500, 8),
    "college":       ('node["amenity"="college"]', 2000, 8),
    "supermarket":   ('node["shop"="supermarket"]', 1000, 5),
    "mall":          ('node["shop"="mall"]', 3000, 7),
    "it_park":       ('node["office"="it"]', 5000, 10),
    "highway":       ('way["highway"="primary"]', 1000, 6),
    "bus_stop":      ('node["highway"="bus_stop"]', 500, 4),
}

# Gap 1: OSM queries for neighbourhood quality scoring
NEIGHBOURHOOD_QUERIES = {
    "residential_land":  ('way["landuse"="residential"]', 1000, 20),
    "commercial_land":   ('way["landuse"="commercial"]', 1000, -10),
    "industrial_land":   ('way["landuse"="industrial"]', 2000, -20),
    "park":              ('way["leisure"="park"]', 1500, 10),
    "religious":         ('node["amenity"="place_of_worship"]', 500, 3),
    "slum":              ('way["landuse"="slum"]', 1000, -25),
}

PUNE_COORDS = {
    "Koregaon Park":  (18.5362, 73.8938),
    "Baner":          (18.5590, 73.7868),
    "Kothrud":        (18.5074, 73.8077),
    "Wakad":          (18.5975, 73.7614),
    "Hinjewadi":      (18.5912, 73.7380),
    "Hadapsar":       (18.5018, 73.9260),
    "Wagholi":        (18.5617, 73.9757),
    "Talegaon":       (18.7332, 73.6723),
    "Chakan":         (18.7601, 73.8637),
    "Shivajinagar":   (18.5308, 73.8474),
    "Aundh":          (18.5578, 73.8073),
    "Viman Nagar":    (18.5679, 73.9143),
    "Pimpri":         (18.6279, 73.7997),
    "Chinchwad":      (18.6436, 73.7983),
    "Katraj":         (18.4601, 73.8669),
    "Ambegaon":       (18.4489, 73.8526),
    # Mumbai
    "Bandra West":    (19.0596, 72.8295),
    "Worli":          (19.0178, 72.8148),
    "Powai":          (19.1197, 72.9052),
    "Andheri West":   (19.1365, 72.8304),
    "Andheri East":   (19.1197, 72.8697),
    "Thane":          (19.2183, 72.9781),
    "Navi Mumbai":    (19.0330, 73.0297),
    "Dadar":          (19.0178, 72.8452),
    "Borivali":       (19.2323, 72.8563),
    "Mira Road":      (19.2876, 72.8689),
    "Virar":          (19.4588, 72.7987),
    "Kharghar":       (19.0478, 73.0760),
    # Bangalore
    "Koramangala":    (12.9352, 77.6245),
    "Indiranagar":    (12.9716, 77.6412),
    "Whitefield":     (12.9698, 77.7499),
    "HSR Layout":     (12.9116, 77.6474),
    "Electronic City":(12.8450, 77.6601),
    "Marathahalli":   (12.9591, 77.6974),
    "Sarjapur Road":  (12.9102, 77.6789),
    "Yelahanka":      (13.1006, 77.5963),
    "Bannerghatta":   (12.8636, 77.5994),
    "Devanahalli":    (13.2467, 77.7108),
    "Tumkur Road":    (13.0230, 77.5540),
}

# Gap 1: Baseline neighbourhood quality scores per zone tier (deterministic fallback)
ZONE_NEIGHBOURHOOD_BASE = {
    "prime":      78.0,
    "mid":        58.0,
    "peripheral": 40.0,
}

LISTING_DENSITY_ESTIMATES = {
    "prime":      {"density": 0.75, "median_asking_premium": 1.18},
    "mid":        {"density": 0.55, "median_asking_premium": 1.06},
    "peripheral": {"density": 0.35, "median_asking_premium": 0.95},
}


async def geocode_address(address: str, session: aiohttp.ClientSession) -> dict:
    """Convert address to lat/long using Nominatim."""
    # Check known localities first (fast path)
    for locality, coords in PUNE_COORDS.items():
        if locality.lower() in address.lower():
            return {
                "lat": coords[0], "lon": coords[1],
                "display_name": f"{locality}, Maharashtra",
                "locality": locality, "source": "lookup",
            }
    # Nominatim fallback
    try:
        params = {"q": f"{address}, Maharashtra, India", "format": "json", "limit": 1}
        headers = {"User-Agent": "PropIQ/1.0 (hackathon project)"}
        async with session.get(NOMINATIM_URL, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as r:
            data = await r.json()
            if data:
                return {
                    "lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]),
                    "display_name": data[0].get("display_name", address),
                    "locality": address, "source": "nominatim",
                }
    except Exception:
        pass
    # Last resort: Pune city center
    return {"lat": 18.5204, "lon": 73.8567, "display_name": address, "locality": address, "source": "default"}


async def compute_infra_score(lat: float, lon: float, session: aiohttp.ClientSession, zone_tier: str = "mid") -> dict:
    """Score infrastructure proximity using OSM Overpass API. Uses zone-based fallback on failure."""
    scores = {}
    total_score = 0.0
    total_weight = 0.0

    async def query_feature(feature_name: str, query_part: str, radius: int, weight: int):
        overpass_q = f"[out:json][timeout:8];{query_part}(around:{radius},{lat},{lon});out count;"
        try:
            async with session.post(
                OVERPASS_URL, data={"data": overpass_q},
                timeout=aiohttp.ClientTimeout(total=8)
            ) as r:
                data = await r.json()
                count = data.get("elements", [{}])[0].get("tags", {}).get("total", 0)
                count = int(count) if count else 0
                return feature_name, min(count, 5), weight
        except Exception:
            return feature_name, 0, weight

    tasks = [query_feature(name, qp, radius, weight) for name, (qp, radius, weight) in INFRA_QUERIES.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            continue
        fname, count, weight = result
        feature_score = min(1.0, count / 3.0) * 100
        scores[fname] = {"count": count, "score": round(feature_score, 1), "weight": weight}
        total_score += feature_score * weight
        total_weight += weight

    if total_weight > 0:
        infra_score = (total_score / total_weight)
    else:
        # Fallback if API fails to prevent massive distress discounts (Error #1)
        infra_score = {"prime": 75.0, "mid": 55.0, "peripheral": 35.0}.get(zone_tier, 55.0)
        
    infra_score = min(100.0, max(0.0, infra_score))

    return {
        "infra_score": round(infra_score, 1),
        "breakdown": scores,
        "data_source": "openstreetmap_overpass",
    }


# Gap 1: Neighbourhood quality score
async def compute_neighbourhood_quality(
    lat: float, lon: float, zone_tier: str, session: aiohttp.ClientSession
) -> float:
    """
    Score neighbourhood quality: planned vs unplanned zones, land-use mix.
    Returns 0-100 score. Higher = more premium/planned residential neighbourhood.
    Falls back to zone_tier baseline if OSM unavailable.
    """
    base_score = ZONE_NEIGHBOURHOOD_BASE.get(zone_tier, 58.0)
    adjustment = 0.0

    async def query_nq(feature_name: str, query_part: str, radius: int, weight: int):
        overpass_q = f"[out:json][timeout:6];{query_part}(around:{radius},{lat},{lon});out count;"
        try:
            async with session.post(
                OVERPASS_URL, data={"data": overpass_q},
                timeout=aiohttp.ClientTimeout(total=6)
            ) as r:
                data = await r.json()
                count = data.get("elements", [{}])[0].get("tags", {}).get("total", 0)
                count = int(count) if count else 0
                return weight if count > 0 else 0
        except Exception:
            return 0

    tasks = [query_nq(name, qp, radius, weight) for name, (qp, radius, weight) in NEIGHBOURHOOD_QUERIES.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, (int, float)):
            adjustment += r

    final = min(100.0, max(10.0, base_score + adjustment))
    return round(final, 1)


def estimate_listing_density(zone_tier: str, locality: str) -> dict:
    """Proxy for market listing density — based on zone tier + locality signals."""
    base = LISTING_DENSITY_ESTIMATES.get(zone_tier, LISTING_DENSITY_ESTIMATES["mid"])
    import random, hashlib
    # Deterministic noise per locality
    seed = int(hashlib.md5(locality.encode()).hexdigest()[:6], 16) % 1000
    rng = random.Random(seed)
    noise = rng.uniform(-0.08, 0.08)
    density = round(min(0.95, max(0.1, base["density"] + noise)), 3)
    return {
        "listing_density": density,
        "median_asking_premium": base["median_asking_premium"],
        "zone_tier": zone_tier,
        "data_source": "proxy_estimate",
    }


async def enrich_property(
    address: str,
    zone_tier: str = "mid",
    geo_lat: Optional[float] = None,
    geo_lon: Optional[float] = None,
) -> dict:
    """
    Main enrichment function — fires all services in parallel.
    Gap 6 fix: If geo_lat/geo_lon are provided, skip geocoding entirely.
    Returns a consolidated enrichment dict ready for the ML model.
    """
    async with aiohttp.ClientSession() as session:
        # Gap 6 fix: bypass geocoding if coordinates are already known
        if geo_lat is not None and geo_lon is not None:
            geo_result = {
                "lat": geo_lat, "lon": geo_lon,
                "display_name": address,
                "locality": address, "source": "user_provided",
            }
        else:
            geo_result = await geocode_address(address, session)

        lat, lon = geo_result["lat"], geo_result["lon"]

        # Fire infra score and neighbourhood quality in parallel
        infra_task = compute_infra_score(lat, lon, session, zone_tier)
        nq_task = compute_neighbourhood_quality(lat, lon, zone_tier, session)
        infra_result, nq_score = await asyncio.gather(infra_task, nq_task)

    listing_result = estimate_listing_density(zone_tier, geo_result.get("locality", address))

    return {
        "geo": geo_result,
        "infra": infra_result,
        "market": listing_result,
        "infra_score": infra_result["infra_score"],
        "listing_density": listing_result["listing_density"],
        "neighbourhood_quality_score": nq_score,  # Gap 1
    }


if __name__ == "__main__":
    result = asyncio.run(enrich_property("Baner, Pune", zone_tier="prime"))
    print(json.dumps(result, indent=2))