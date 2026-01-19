import sys
from datetime import datetime
from fastapi import FastAPI
from src.utils.logger import setup_logger
from src.jobs.daily_summary import run_daily_pipeline
from src.api.forecasts import router as forecast_router

logger = setup_logger()

# --- 1. API CONFIGURATION (Accessed by Uvicorn) ---
app = FastAPI(title="Groundwater Analytics Engine", version="2.0")

# Register the Forecasts Router (Connects the Brain to the API)
app.include_router(forecast_router)

@app.get("/health")
def health_check():
    """Health check for the Analytics Service"""
    return {"status": "active", "service": "Service B (Analytics)", "model_type": "LSTM/RF"}

# --- 2. CLI JOB RUNNER (Accessed by Python command) ---
def main():
    """
    Main Entry Point for Background Jobs.
    Usage: python main.py [job_name] [optional: YYYY-MM-DD]
    """
    if len(sys.argv) < 2:
        logger.error("No job specified. Usage: python main.py <job_name> [date]")
        sys.exit(1)

    job_name = sys.argv[1]
    
    # Logic: If date provided in args, use it. Otherwise, use Today.
    if len(sys.argv) > 2:
        target_date_str = sys.argv[2]
    else:
        target_date_str = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Starting Service B Analytics. Job: {job_name} | Date: {target_date_str}")

    try:
        if job_name == "daily_summary":
            # Running the Pipeline
            run_daily_pipeline(target_date_str)
        else:
            logger.warning(f"Job {job_name} not recognized.")
            
    except Exception as e:
        logger.exception("Critical Job Failure")
        sys.exit(1)

if __name__ == "__main__":
    main()