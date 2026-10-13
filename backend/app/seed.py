"""Optional LOCAL demo data:  cd backend && python -m app.seed
Adds clearly-labelled DEMO donors and one verified demo ambulance (Siliguri area) so the
matching and map features can be tried immediately. Do NOT run against a real production DB."""
from app.db import Base, SessionLocal, engine
from app import models
from app.models import Ambulance, Donor

DEMO = [("O-", 26.7271, 88.3953), ("O+", 26.7100, 88.4300), ("A+", 26.7200, 88.4100),
        ("B+", 26.7400, 88.4200), ("AB+", 26.7000, 88.4000), ("A-", 26.7300, 88.4400)]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for i, (g, la, lo) in enumerate(DEMO, 1):
        phone = f"900000000{i}"
        if not db.query(Donor).filter(Donor.phone == phone).first():
            db.add(Donor(name=f"DEMO Donor {i}", phone=phone, blood_group=g, city="Siliguri", lat=la, lon=lo, consent=True))
    if not db.query(Ambulance).filter(Ambulance.phone == "9000000100").first():
        db.add(Ambulance(operator="DEMO Ambulance Service", phone="9000000100", vehicle_type="ALS", city="Siliguri",
                         lat=26.7250, lon=88.4000, verified=True))
    db.commit()
    print("Demo data added.")


if __name__ == "__main__":
    main()
