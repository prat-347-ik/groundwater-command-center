import json
import os
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("register")

# --- CONFIGURATION ---
REGION_ID = "65f4fc28-a5f9-47e0-b326-962b20bb35b1"
MODEL_DIR = "models/v1"
MODEL_FILE = f"rf_{REGION_ID}.pkl"  # CHANGED: expecting .pkl now
REGISTRY_FILE = "model_registry.json"

def register():
    registry_path = os.path.join(MODEL_DIR, REGISTRY_FILE)
    model_path = os.path.join(MODEL_DIR, MODEL_FILE)

    if not os.path.exists(model_path):
        logger.error(f"❌ Model file not found: {model_path}")
        return

    new_entry = {
        "region_id": REGION_ID,
        "model_type": "random-forest-sklearn", # CHANGED
        "version": "1.0-rf",
        "status": "active",
        "artifact_path": model_path,
        "registered_at": datetime.now(timezone.utc).isoformat()
    }

    # ... (Rest of the file remains identical: Load JSON, archive old entries, append new, save) ...
    # [Copy the rest of the existing logic here]
    
    # ... 
    registry = []
    if os.path.exists(registry_path):
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
        except Exception:
            registry = []

    for entry in registry:
        if entry.get("region_id") == REGION_ID:
            entry["status"] = "archived"

    registry.append(new_entry)

    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=4)

    logger.info(f"✅ RF Model Registered Successfully!")

if __name__ == "__main__":
    register()