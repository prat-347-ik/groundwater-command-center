import sys
from src.utils.logger import setup_logger
from src.jobs.daily_summary import run_daily_pipeline

logger = setup_logger()

def main():
    """
    Main Entry Point.
    Usage: python main.py [job_name] [date_arg]
    """
    if len(sys.argv) < 2:
        logger.error("No job specified. Usage: python main.py <job_name>")
        sys.exit(1)

    job_name = sys.argv[1]
    
    logger.info(f"Starting Service B Analytics. Job: {job_name}")

    try:
        if job_name == "daily_summary":
            # Example trigger
            run_daily_pipeline() 
        else:
            logger.warning(f"Job {job_name} not recognized.")
            
    except Exception as e:
        logger.exception("Critical Job Failure")
        sys.exit(1)

if __name__ == "__main__":
    main()