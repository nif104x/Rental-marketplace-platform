from fastapi import FastAPI
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles

from app.user import router as user
from app.db import engine

app = FastAPI()

# app.mount("/images", StaticFiles(directory="../frontend/images"), name="images")
app.include_router(user)

@app.get("/")
def home():
    return {"message": "API is running"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}