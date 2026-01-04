import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# --- Path Resolution ---
# Base = services/service-c-orchestrator
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Service B = services/service-b-analytics
SERVICE_B_DIR = BASE_DIR / "service-b-analytics"

def get_venv_python(service_dir: Path) -> str:
    """
    Locates the Python executable inside a service's virtual environment.
    Supports Linux/Mac (bin/python) and Windows (Scripts/python.exe).
    """
    venv_names = ["venv", ".venv", "env"]
    
    for venv in venv_names:
        # Check Linux/Mac path
        unix_py = service_dir / venv / "bin" / "python"
        if unix_py.exists():
            return str(unix_py)
            
        # Check Windows path
        win_py = service_dir / venv / "Scripts" / "python.exe"
        if win_py.exists():
            return str(win_py)
    
    # Fail-safe: Fallback to system python if venv not found (Log warning in prod)
    print(f"⚠️  WARNING: No virtual environment found in {service_dir}. Using system 'python'.")
    return "python"

# The absolute path to Service B's Python executable
SERVICE_B_PYTHON = get_venv_python(SERVICE_B_DIR)

# Validation
if not SERVICE_B_DIR.exists():
    raise FileNotFoundError(f"CRITICAL: Service B directory not found at {SERVICE_B_DIR}")