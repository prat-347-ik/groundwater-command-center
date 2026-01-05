import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

# Import your existing logic
# These imports match the file structure you provided
from src.jobs.daily_summary import run_daily_pipeline
from src.modelling.training import run_training_pipeline
from src.modelling.update_registry import promote_models
from src.inference.predictor import run_inference

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service-b-api")

app = FastAPI(title="Service B - Analytics Worker", version="1.0.0")

# --- Pydantic Models ---
class PipelineRequest(BaseModel):
    date: str = None  # Optional YYYY-MM-DD

# --- Helper ---
def run_job_safe(job_func, job_name, *args):
    """
    Wraps job execution to catch errors and log them 
    without crashing the background thread silently.
    """
    logger.info(f"▶️ Starting Background Job: {job_name}")
    try:
        job_func(*args)
        logger.info(f"✅ Job Completed: {job_name}")
    except Exception as e:
        logger.error(f"❌ Job Failed: {job_name} | Error: {e}")

# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "ready", "service": "Service B - Analytics"}

@app.post("/jobs/daily-summary")
def trigger_daily_summary(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Triggers the ETL pipeline.
    Payload: {"date": "2025-01-01"} (Optional, defaults to today in the script)
    """
    target_date = request.date or "today"
    logger.info(f"Received trigger for Daily Summary (Date: {target_date})")
    
    # Run in background so API returns immediately
    background_tasks.add_task(run_job_safe, run_daily_pipeline, "Daily Summary", target_date)
    return {"status": "queued", "job": "daily_summary", "target_date": target_date}

@app.post("/jobs/train")
def trigger_training(background_tasks: BackgroundTasks):
    """
    Triggers Model Training (Linear Regression).
    """
    logger.info("Received trigger for Model Training")
    background_tasks.add_task(run_job_safe, run_training_pipeline, "Training")
    return {"status": "queued", "job": "training"}

@app.post("/jobs/promote")
def trigger_promotion(background_tasks: BackgroundTasks):
    """
    Triggers the Gating/Promotion logic.
    """
    logger.info("Received trigger for Model Promotion")
    background_tasks.add_task(run_job_safe, promote_models, "Promotion")
    return {"status": "queued", "job": "promotion"}

@app.post("/jobs/forecast")
def trigger_forecast(background_tasks: BackgroundTasks):
    """
    Triggers Inference (Forecasting).
    """
    logger.info("Received trigger for Forecasting")
    background_tasks.add_task(run_job_safe, run_inference, "Forecasting")
    return {"status": "queued", "job": "forecast"}

if __name__ == "__main__":
    import uvicorn
    # Run on port 8200 to keep it distinct from Service A (8000) and Service C (8100)
    uvicorn.run(app, host="0.0.0.0", port=8200)