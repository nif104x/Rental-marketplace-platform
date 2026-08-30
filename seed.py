from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models.booking import Booking, BookingStatus
from app.models.listing import Listing, ListingStatus, RateType
from app.models.user import User, UserProfile, UserRole


def seed_data():
    # 1. Ensure all SQL tables are created in NeonDB
    print("Creating tables in NeonDB...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if dummy data already exists to avoid duplicates
        if db.query(User).filter(User.email == "lessor@example.com").first():
            print("Database is already seeded!")
            return

        print("Seeding users...")
        # 2. Seed Users
        lessor = User(
            email="lessor@example.com",
            hashed_password=get_password_hash("password123"),
            role=UserRole.LESSOR,
        )
        lessee = User(
            email="lessee@example.com",
            hashed_password=get_password_hash("password123"),
            role=UserRole.LESSEE,
        )
        db.add_all([lessor, lessee])
        db.commit()
        db.refresh(lessor)
        db.refresh(lessee)

        # User Profiles
        db.add(UserProfile(user_id=lessor.id, full_name="Alice Owner", location="Downtown"))
        db.add(UserProfile(user_id=lessee.id, full_name="Bob Renter", location="Uptown"))
        db.commit()

        print("Seeding listings...")
        # 3. Seed Sample Listings
        listing1 = Listing(
            lessor_id=lessor.id,
            title="Sony Alpha A7 III Camera Kit",
            description="Includes 24-70mm f/2.8 Lens, 2 extra batteries, and 128GB SD Card.",
            category="Electronics",
            rental_rate=35.0,
            rate_type=RateType.DAILY,
            security_deposit=150.0,
            status=ListingStatus.ACTIVE,
            location="Downtown",
        )
        listing2 = Listing(
            lessor_id=lessor.id,
            title="Mountain Bike (21 Speed)",
            description="Lightweight aluminum frame, dual disc brakes. Great for weekend trail rides.",
            category="Sports",
            rental_rate=15.0,
            rate_type=RateType.DAILY,
            security_deposit=50.0,
            status=ListingStatus.ACTIVE,
            location="Northside",
        )
        db.add_all([listing1, listing2])
        db.commit()
        db.refresh(listing1)

        print("Seeding completed successfully!")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()