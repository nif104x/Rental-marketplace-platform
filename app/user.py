from fastapi import FastAPI, APIRouter


router = APIRouter(prefix="/user", tags=["User"])


@router.get("/ola")
def login():
    return {"message": "hello user"}