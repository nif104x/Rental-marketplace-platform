from sqlalchemy import text
from app.core.database import engine

def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1;"))
            print("Successfully connected to NeonDB!")
            print(f"Database response: {result.fetchone()}")
    except Exception as e:
        print("Failed to connect to NeonDB.")
        print(f"Error details: {e}")

if __name__ == "__main__":
    test_connection()