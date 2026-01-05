from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import db
from api.rainfall import router as rainfall_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager: Connects to DB on startup, closes on shutdown.
    """
    db.connect()
    # Ensure indexes for performance
    db.get_rainfall_collection().create_index([("region_id", 1), ("timestamp", -1)])
    yield
    db.close()

app = FastAPI(
    title="Service C - Climate Intelligence",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS (Allows Frontend/Gateway to talk to it)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(rainfall_router)

@app.get("/health")
def health_check():
    return {"status": "Service C is Online (Climate Only) 🟢"}

if __name__ == "__main__":
    import uvicorn
    # Runs on Port 8100 as per architecture
    uvicorn.run(app, host="0.0.0.0", port=8100)