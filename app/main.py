from fastapi import FastAPI
from sqlalchemy import text


from app.user import router as user

from app.db import engine

app = FastAPI()

app.include_router(user)

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}