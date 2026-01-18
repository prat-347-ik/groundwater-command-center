from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import db
from api.rainfall import router as rainfall_router
from api.weather import router as weather_router # 🆕 Import
from api.satellite import router as satellite_router  # <--- 🆕 Import

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager: Connects to DB on startup, closes on shutdown.
    """
    db.connect()
    # Ensure indexes
    db.get_rainfall_collection().create_index([("region_id", 1), ("timestamp", -1)])
    # 🆕 Weather Indexes
    db.get_weather_collection().create_index([("region_id", 1), ("timestamp", -1)])
    # <--- 🆕 Satellite Indexes
    db.get_satellite_collection().create_index([("region_id", 1), ("timestamp", -1)]) # <--- 🆕 Index
    yield
    db.close()

app = FastAPI(
    title="Service C - Climate Intelligence",
    version="1.1.0", # Bumped version
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(rainfall_router)
app.include_router(weather_router) # 🆕 Register
app.include_router(satellite_router)  # <--- 🆕 Register

@app.get("/health")
def health_check():
    return {"status": "Service C is Online (Climate + Weather) 🟢"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)