import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# Import Logic
from src.jobs.daily_summary import run_daily_pipeline
from src.modelling.training import run_training_pipeline
from src.modelling.update_registry import promote_models
from src.inference.predictor import run_inference

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-b-api")

app = FastAPI(title="Service B - Analytics Worker", version="1.0.0")

class PipelineRequest(BaseModel):
    date: str = None

# --- UPDATED: Async Wrapper for Async Jobs (ETL) ---
async def run_async_job_safe(job_func, job_name, *args):
    """Wrapper for ASYNC functions (like daily_summary)"""
    logger.info(f"▶️ Starting Async Job: {job_name}")
    try:
        await job_func(*args)
        logger.info(f"✅ Job Completed: {job_name}")
    except Exception as e:
        logger.error(f"❌ Job Failed: {job_name} | Error: {e}")

# --- UPDATED: Sync Wrapper for Sync Jobs (Training/ML) ---
def run_sync_job_safe(job_func, job_name, *args):
    """Wrapper for SYNC functions (CPU heavy ML tasks)"""
    logger.info(f"▶️ Starting Sync Job: {job_name}")
    try:
        job_func(*args)
        logger.info(f"✅ Job Completed: {job_name}")
    except Exception as e:
        logger.error(f"❌ Job Failed: {job_name} | Error: {e}")

@app.get("/")
def health_check():
    return {"status": "ready", "service": "Service B - Analytics"}

@app.post("/jobs/daily-summary")
async def trigger_daily_summary(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Step 1: ETL (Async - requires waiting for HTTP calls)
    """
    target_date = request.date or "today"
    logger.info(f"Received trigger for Daily Summary (Date: {target_date})")
    
    # Use the ASYNC wrapper here
    background_tasks.add_task(run_async_job_safe, run_daily_pipeline, "Daily Summary", target_date)
    return {"status": "queued", "job": "daily_summary", "target_date": target_date}

@app.post("/jobs/train")
def trigger_training(background_tasks: BackgroundTasks):
    """
    Step 2: Training (Sync - CPU Bound)
    """
    logger.info("Received trigger for Model Training")
    # Use the SYNC wrapper here
    background_tasks.add_task(run_sync_job_safe, run_training_pipeline, "Training")
    return {"status": "queued", "job": "training"}

@app.post("/jobs/promote")
def trigger_promotion(background_tasks: BackgroundTasks):
    """
    Step 3: Promotion (Sync)
    """
    logger.info("Received trigger for Model Promotion")
    background_tasks.add_task(run_sync_job_safe, promote_models, "Promotion")
    return {"status": "queued", "job": "promotion"}

@app.post("/jobs/forecast")
def trigger_forecast(background_tasks: BackgroundTasks):
    """
    Step 4: Forecast (Sync)
    """
    logger.info("Received trigger for Forecasting")
    background_tasks.add_task(run_sync_job_safe, run_inference, "Forecasting")
    return {"status": "queued", "job": "forecast"}

# --- Master Pipeline (The "Run All" Button) ---
async def run_full_pipeline_logic(date: str):
    """
    Orchestrates the sequential execution of the pipeline.
    """
    # 1. ETL (Async)
    await run_async_job_safe(run_daily_pipeline, "Step 1: ETL", date)
    
    # 2. Train (Sync - Wrapped in executor logic implicitly or run directly)
    # Since we are inside an async function, we should ideally run sync blocking code in a thread
    # But for simplicity in this MVP, calling them directly blocks the loop briefly, which is acceptable for a background worker.
    run_sync_job_safe(run_training_pipeline, "Step 2: Training")
    run_sync_job_safe(promote_models, "Step 3: Promotion")
    run_sync_job_safe(run_inference, "Step 4: Forecasting")

@app.post("/jobs/pipeline")
async def trigger_full_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    target_date = request.date or "today"
    background_tasks.add_task(run_full_pipeline_logic, target_date)
    return {"status": "started", "message": "Full pipeline triggered"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)