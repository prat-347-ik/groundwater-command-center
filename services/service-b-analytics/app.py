import logging
import asyncio
from datetime import datetime, timezone  # <--- [FIX] Added imports
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
        # Re-raise exception so the main pipeline knows to stop if ETL fails
        raise e 

# --- UPDATED: Sync Wrapper for Sync Jobs (Training/ML) ---
def run_sync_job_safe(job_func, job_name, *args):
    """Wrapper for SYNC functions (CPU heavy ML tasks)"""
    logger.info(f"▶️ Starting Sync Job: {job_name}")
    try:
        job_func(*args)
        logger.info(f"✅ Job Completed: {job_name}")
    except Exception as e:
        logger.error(f"❌ Job Failed: {job_name} | Error: {e}")
        raise e

# --- [FIX] Helper to get formatted date string ---
def get_target_date_str(requested_date: str = None) -> str:
    """Returns requested date or defaults to Today (UTC) in YYYY-MM-DD"""
    if requested_date:
        return requested_date
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

@app.get("/")
def health_check():
    return {"status": "ready", "service": "Service B - Analytics"}

@app.post("/jobs/daily-summary")
async def trigger_daily_summary(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Step 1: ETL (Async - requires waiting for HTTP calls)
    """
    # [FIX] Resolve "today" to actual date string
    target_date = get_target_date_str(request.date)
    
    logger.info(f"Received trigger for Daily Summary (Date: {target_date})")
    
    background_tasks.add_task(run_async_job_safe, run_daily_pipeline, "Daily Summary", target_date)
    return {"status": "queued", "job": "daily_summary", "target_date": target_date}

@app.post("/jobs/train")
def trigger_training(background_tasks: BackgroundTasks):
    """Step 2: Training (Sync - CPU Bound)"""
    logger.info("Received trigger for Model Training")
    background_tasks.add_task(run_sync_job_safe, run_training_pipeline, "Training")
    return {"status": "queued", "job": "training"}

@app.post("/jobs/promote")
def trigger_promotion(background_tasks: BackgroundTasks):
    """Step 3: Promotion (Sync)"""
    logger.info("Received trigger for Model Promotion")
    background_tasks.add_task(run_sync_job_safe, promote_models, "Promotion")
    return {"status": "queued", "job": "promotion"}

@app.post("/jobs/forecast")
def trigger_forecast(background_tasks: BackgroundTasks):
    """Step 4: Forecast (Sync)"""
    logger.info("Received trigger for Forecasting")
    background_tasks.add_task(run_sync_job_safe, run_inference, "Forecasting")
    return {"status": "queued", "job": "forecast"}

# --- Master Pipeline (The "Run All" Button) ---
async def run_full_pipeline_logic(date: str):
    """
    Orchestrates the sequential execution of the pipeline.
    """
    try:
        # 1. ETL (Async)
        await run_async_job_safe(run_daily_pipeline, "Step 1: ETL", date)
        
        # 2. Train (Sync)
        # We run these sequentially. If ETL fails, the 'raise e' in wrapper will stop execution here.
        run_sync_job_safe(run_training_pipeline, "Step 2: Training")
        run_sync_job_safe(promote_models, "Step 3: Promotion")
        run_sync_job_safe(run_inference, "Step 4: Forecasting")
        
        logger.info("🎉 FULL PIPELINE SUCCESS")
        
    except Exception as e:
        logger.error(f"⛔ Pipeline Aborted due to failure: {e}")

@app.post("/jobs/pipeline")
async def trigger_full_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    # [FIX] Resolve "today" to actual date string
    target_date = get_target_date_str(request.date)
    
    background_tasks.add_task(run_full_pipeline_logic, target_date)
    return {"status": "started", "message": "Full pipeline triggered", "date": target_date}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8200)