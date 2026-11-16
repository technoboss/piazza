from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine

import app.models 
from app.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any table that does not exist yet in piazza.db.
    # Tables that already exist are left untouched.
    Base.metadata.create_all(bind=engine) # Uses the models.py file to create the tables
    yield


# Create the application and attach the startup logic above.
app = FastAPI(title="Piazza", lifespan=lifespan)

app.include_router(auth.router)

# A simple route to check that the server is running.
@app.get("/health")
def health():
    return {"status": "ok"}