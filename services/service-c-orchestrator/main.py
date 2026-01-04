import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from orchestrator import run_pipeline

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# --- Global State (Simple In-Memory Lock) ---
# In a real distributed system, use Redis for this.
pipeline_state = {
    "is_running": False,
    "last_run_status": "unknown",
    "last_run_time": None
}

def pipeline_wrapper():
    """
    Wraps the synchronous orchestrator to manage state flags.
    """
    global pipeline_state
    try:
        logger.info("🚀 API triggered pipeline execution.")
        pipeline_state["is_running"] = True
        pipeline_state["last_run_status"] = "running"
        
        # Run the actual heavy-lifting
        run_pipeline()
        
        pipeline_state["last_run_status"] = "success"
    except Exception as e:
        logger.error(f"💥 Pipeline failed: {e}")
        pipeline_state["last_run_status"] = "failed"
    finally:
        pipeline_state["is_running"] = False
        logger.info("🏁 Pipeline execution finished.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Service C Orchestrator API...")
    yield
    # Shutdown logic
    logger.info("Shutting down Service C...")

app = FastAPI(title="Groundwater Orchestrator", version="1.0.0", lifespan=lifespan)

# --- Endpoints ---

@app.get("/")
def root():
    return {"message": "Service C Orchestrator is Online 🟢"}

@app.get("/pipeline/status")
def get_status():
    """
    Check if the pipeline is currently running.
    """
    return pipeline_state

@app.post("/pipeline/trigger")
def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Manually triggers the groundwater analytics pipeline.
    """
    if pipeline_state["is_running"]:
        raise HTTPException(status_code=409, detail="Pipeline is already running.")
    
    # Run in background so the API responds immediately
    background_tasks.add_task(pipeline_wrapper)
    return {"message": "Pipeline triggered successfully", "status": "started"}

if __name__ == "__main__":
    import uvicorn
    # Run on port 8002 to avoid conflict with Service A (8000/8001)
    uvicorn.run(app, host="0.0.0.0", port=8002)