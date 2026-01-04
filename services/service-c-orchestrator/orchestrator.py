import sys
import time
from config.settings import SERVICE_B_DIR, SERVICE_B_PYTHON
from runners.subprocess_runner import run_command
from utils.logger import setup_logger

# Initialize Logger
logger = setup_logger("orchestrator")

def run_pipeline():
    """
    Main Orchestration Workflow:
    1. ETL: Ingest & Transform Data (Daily Summary)
    2. Train: Run Model Training
    3. Gate: Evaluate & Promote Models
    4. Infer: Generate Forecasts
    """
    start_time = time.time()
    logger.info("🎼 Starting Groundwater Analytics Pipeline...")

    try:
        # --- STEP 1: ETL ---
        logger.info("--- [1/4] Running ETL (Daily Summary) ---")
        # Uses Service B's main entry point for the summary job
        run_command(
            command=[SERVICE_B_PYTHON, "main.py", "daily_summary"],
            cwd=str(SERVICE_B_DIR)
        )

        # --- STEP 2: TRAINING ---
        logger.info("--- [2/4] Running Model Training ---")
        # Uses 'python -m' to run module to ensure relative imports in Service B work
        run_command(
            command=[SERVICE_B_PYTHON, "-m", "src.modelling.training"],
            cwd=str(SERVICE_B_DIR)
        )

        # --- STEP 3: GATING ---
        logger.info("--- [3/4] Running Model Promotion Gate ---")
        run_command(
            command=[SERVICE_B_PYTHON, "-m", "src.modelling.update_registry"],
            cwd=str(SERVICE_B_DIR)
        )

        # --- STEP 4: INFERENCE ---
        logger.info("--- [4/4] Running Inference (Forecasts) ---")
        run_command(
            command=[SERVICE_B_PYTHON, "-m", "src.inference.predictor"],
            cwd=str(SERVICE_B_DIR)
        )

        duration = round(time.time() - start_time, 2)
        logger.info(f"🎉 Pipeline Completed Successfully in {duration} seconds.")

    except Exception as e:
        logger.critical(f"🛑 Pipeline Aborted: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("DEBUG: Pipeline Script Started...")
    run_pipeline()