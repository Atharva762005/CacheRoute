"""
PropIQ Comparable Sales Engine
Finds 3-5 comparable properties for any subject property.
Uses a SQLite database populated from the synthetic dataset + optional scraped data.
This is what real valuers do — and it makes outputs defensible.
"""

import sqlite3
import json
import math
import random
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent.parent / "data" / "comps.db"

# ── Database setup ─────────────────────────────────────────────────────────

def init_db():
    """Create comps database and populate with synthetic comparable data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS comps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            locality TEXT NOT NULL,
            city TEXT NOT NULL,
            prop_type TEXT NOT NULL,
            size_sqft REAL NOT NULL,
            age_years REAL NOT NULL,
            floor_num INTEGER,
            price_per_sqft REAL NOT NULL,
            total_price INTEGER NOT NULL,
            zone_tier TEXT NOT NULL,
            source TEXT DEFAULT 'synthetic',
            listing_date TEXT,
            distance_km REAL DEFAULT 0,
            address_hint TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_locality ON comps(locality, prop_type)")
    conn.commit()

    # Check if already populated
    count = c.execute("SELECT COUNT(*) FROM comps").fetchone()[0]
    if count > 100:
        conn.close()
        return

    # Populate with synthetic comps
    _populate_comps(conn)
    conn.close()
    print(f"Comps DB initialised at {DB_PATH}")


def _populate_comps(conn):
    """Generate realistic comparable listings for all localities."""
    from app.data.india_circle_rates import ZONE_MULTIPLIERS
    from app.core.db import SessionLocal
    from app.models.db_models import CircleRate

    rng = random.Random(42)
    rows = []
    now = datetime.now()

    PROP_CONFIGS = {
        "2bhk_apartment": (600, 1100),
        "3bhk_apartment": (1000, 1800),
        "1bhk_apartment": (350, 600),
        "villa":          (2000, 4500),
        "shop":           (200, 800),
        "office":         (500, 2500),
    }

    ADDRESS_HINTS = [
        "Opp. main market", "Near IT park", "Gated community",
        "Corner unit", "High-rise tower", "Society flat",
        "Near metro station", "Main road facing",
    ]

    db = SessionLocal()
    try:
        circle_rates = db.query(CircleRate).all()
        for rate in circle_rates:
            zone = rate.zone_tier
            city = rate.city
            mult_range = ZONE_MULTIPLIERS.get(zone, ZONE_MULTIPLIERS["mid"])
    
            for prop_type, (min_sz, max_sz) in PROP_CONFIGS.items():
                cr_key = "residential_apartment" if "apartment" in prop_type or prop_type == "villa" \
                         else "commercial_shop" if prop_type == "shop" \
                         else "commercial_office" if prop_type == "office" else "residential_apartment"
                
                circle_rate = getattr(rate, cr_key, rate.residential_apartment)

            # Generate 4-8 comps per locality+type
            for _ in range(rng.randint(4, 8)):
                size = round(rng.uniform(min_sz, max_sz))
                age = round(rng.uniform(0, 25), 1)
                floor = rng.randint(0, 15) if "apartment" in prop_type else rng.randint(0, 4)
                mult = rng.triangular(mult_range["min"], mult_range["max"], mult_range["mid"])
                depreciation = max(0.6, 1.0 - age * 0.012)
                noise = rng.gauss(1.0, 0.08)
                price_sqft = circle_rate * mult * depreciation * noise
                total_price = int(price_sqft * size)
                days_ago = rng.randint(7, 180)
                listing_date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")

                rows.append((
                    locality, city, prop_type, size, age, floor,
                    round(price_sqft, 1), total_price, zone, "synthetic",
                    listing_date, 0.0, rng.choice(ADDRESS_HINTS),
                ))

        conn.executemany("""
            INSERT INTO comps (locality, city, prop_type, size_sqft, age_years, floor_num,
                price_per_sqft, total_price, zone_tier, source, listing_date, distance_km, address_hint)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        conn.commit()
        print(f"Inserted {len(rows)} comparable records")
    finally:
        db.close()


# ── Comp finder ────────────────────────────────────────────────────────────

def find_comps(
    locality: str,
    prop_type: str,
    size_sqft: float,
    age_years: float,
    n: int = 5,
) -> List[Dict]:
    """
    Find n comparable properties for the subject property.
    Ranked by similarity score (size, age, location match).
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Broaden type for matching
    type_group = "apartment" if "apartment" in prop_type or prop_type == "villa" else prop_type

    if type_group == "apartment":
        type_filter = "prop_type LIKE '%apartment%' OR prop_type = 'villa'"
    else:
        type_filter = f"prop_type = '{type_group}'"

    rows = c.execute(f"""
        SELECT * FROM comps
        WHERE locality = ? AND ({type_filter})
        ORDER BY ABS(size_sqft - ?) ASC, ABS(age_years - ?) ASC
        LIMIT 20
    """, (locality, size_sqft, age_years)).fetchall()

    if len(rows) < 3:
        # Fallback: same zone tier, same city
        rows = c.execute(f"""
            SELECT comps.* FROM comps
            JOIN (SELECT zone_tier, city FROM comps WHERE locality = ? LIMIT 1) z
            ON comps.zone_tier = z.zone_tier AND comps.city = z.city
            WHERE ({type_filter})
            ORDER BY ABS(size_sqft - ?) ASC
            LIMIT 20
        """, (locality, size_sqft)).fetchall()

    conn.close()

    if not rows:
        return []

    # Score and rank
    def similarity_score(row):
        size_diff_pct = abs(row["size_sqft"] - size_sqft) / size_sqft
        age_diff = abs(row["age_years"] - age_years)
        same_locality = 1.0 if row["locality"] == locality else 0.5
        return -(size_diff_pct * 0.5 + age_diff * 0.02 - same_locality * 0.3)

    ranked = sorted(rows, key=similarity_score, reverse=True)[:n]

    return [
        {
            "locality": r["locality"],
            "city": r["city"],
            "prop_type": r["prop_type"],
            "size_sqft": r["size_sqft"],
            "age_years": r["age_years"],
            "floor_num": r["floor_num"],
            "price_per_sqft": r["price_per_sqft"],
            "total_price": r["total_price"],
            "listing_date": r["listing_date"],
            "address_hint": r["address_hint"],
            "source": r["source"],
            "similarity_label": _similarity_label(r["size_sqft"], size_sqft, r["age_years"], age_years),
        }
        for r in ranked
    ]


def _similarity_label(comp_size, subj_size, comp_age, subj_age):
    size_diff = abs(comp_size - subj_size) / subj_size
    age_diff = abs(comp_age - subj_age)
    if size_diff < 0.1 and age_diff < 3:
        return "Very similar"
    elif size_diff < 0.2 and age_diff < 6:
        return "Similar"
    else:
        return "Comparable"


def get_comp_stats(locality: str, prop_type: str) -> Dict:
    """Get aggregate stats for comps in a locality."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    type_group = "apartment" if "apartment" in prop_type or prop_type == "villa" else prop_type
    type_filter = "prop_type LIKE '%apartment%' OR prop_type = 'villa'" \
        if type_group == "apartment" else f"prop_type = '{type_group}'"

    stats = c.execute(f"""
        SELECT
            COUNT(*) as count,
            ROUND(AVG(price_per_sqft), 0) as avg_price_sqft,
            ROUND(MIN(price_per_sqft), 0) as min_price_sqft,
            ROUND(MAX(price_per_sqft), 0) as max_price_sqft,
            ROUND(AVG(size_sqft), 0) as avg_size
        FROM comps WHERE locality = ? AND ({type_filter})
    """, (locality,)).fetchone()
    conn.close()

    if not stats or stats[0] == 0:
        return {}
    return {
        "count": stats[0],
        "avg_price_sqft": stats[1],
        "min_price_sqft": stats[2],
        "max_price_sqft": stats[3],
        "avg_size": stats[4],
    }


if __name__ == "__main__":
    init_db()
    comps = find_comps("Baner", "2bhk_apartment", 850, 8, n=5)
    print(f"\nFound {len(comps)} comps for Baner 2BHK 850sqft:")
    for c in comps:
        print(f"  {c['address_hint']} | {c['size_sqft']:.0f}sqft | {c['age_years']:.0f}yrs | ₹{c['price_per_sqft']:,.0f}/sqft | {c['similarity_label']}")
    stats = get_comp_stats("Baner", "2bhk_apartment")
    print(f"\nMarket stats: avg ₹{stats.get('avg_price_sqft',0):,.0f}/sqft, range ₹{stats.get('min_price_sqft',0):,.0f}–₹{stats.get('max_price_sqft',0):,.0f}")