from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine

import app.models

from app.routers import auth, posts, topics


# Code before "yield" runs once at startup; code after it runs at shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create any missing table from models.py. Existing tables are untouched.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Piazza", lifespan=lifespan)

# The "/auth" prefix is set inside routers/auth.py.
app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(posts.router)


# Public liveness check, also used later by Docker and GKE.
@app.get("/health")
def health():
    return {"status": "ok"}
