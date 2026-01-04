import sys
from datetime import datetime
from src.utils.logger import setup_logger
from src.jobs.daily_summary import run_daily_pipeline

logger = setup_logger()

def main():
    """
    Main Entry Point.
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
            # FIXED: Passing the required argument
            run_daily_pipeline(target_date_str)
        else:
            logger.warning(f"Job {job_name} not recognized.")
            
    except Exception as e:
        logger.exception("Critical Job Failure")
        sys.exit(1)

if __name__ == "__main__":
    main()