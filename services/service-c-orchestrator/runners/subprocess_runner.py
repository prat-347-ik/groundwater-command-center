import subprocess
import os
from typing import List, Optional
from utils.logger import setup_logger

logger = setup_logger("runner")

def run_command(command: List[str], cwd: str, env: Optional[dict] = None) -> None:
    """
    Executes a shell command in a specific directory with real-time output capturing.
    """
    cmd_str = " ".join(command)
    logger.info(f"🚀 Executing: {cmd_str}")
    logger.debug(f"    Context: {cwd}")

    try:
        # Merge current environment with overrides
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        # Execute with real-time output streaming
        with subprocess.Popen(
            command,
            cwd=cwd,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True,
            bufsize=1,
            encoding='utf-8' # Explicit encoding for Windows safety
        ) as process:
            
            # Stream output line-by-line
            for line in process.stdout:
                logger.info(f"  [Service B] {line.strip()}")
            
            # Wait for completion
            return_code = process.wait()

            if return_code != 0:
                logger.error(f"❌ Command failed with exit code {return_code}")
                raise RuntimeError(f"Step failed: {cmd_str}")

            logger.info("✅ Step completed successfully.")

    except Exception as e:
        logger.exception(f"💥 Execution Exception: {e}")
        raise e