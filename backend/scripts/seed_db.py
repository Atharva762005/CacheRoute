"""
Database seeding script.
Run this to create the DB tables and migrate the static circle rates.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to sys.path so we can import app modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from app.core.db import engine, Base, SessionLocal
from app.models.db_models import CircleRate
from app.data.india_circle_rates import ALL_CIRCLE_RATES

def seed_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(CircleRate).first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding circle rates...")
        records = []
        for locality, data in ALL_CIRCLE_RATES.items():
            rate = CircleRate(
                city=data.get("city", "Pune"),
                locality=locality,
                zone_tier=data["zone_tier"],
                residential_apartment=data["residential_apartment"],
                commercial_shop=data["commercial_shop"],
                commercial_office=data["commercial_office"],
                industrial=data["industrial"],
                residential_plot=data["residential_plot"],
                lat=data.get("lat"),
                lon=data.get("lon"),
            )
            records.append(rate)
        
        db.bulk_save_objects(records)
        db.commit()
        print(f"Successfully seeded {len(records)} circle rates.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
