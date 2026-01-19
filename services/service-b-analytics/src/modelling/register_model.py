import json
import os
import logging
import sys
from datetime import datetime,timezone

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("register")

# --- CONFIGURATION ---
REGION_ID = "65f4fc28-a5f9-47e0-b326-962b20bb35b1" # Your Region
MODEL_DIR = "models/v1"
MODEL_FILE = f"lstm_{REGION_ID}.pth"
REGISTRY_FILE = "model_registry.json"

def register():
    registry_path = os.path.join(MODEL_DIR, REGISTRY_FILE)
    model_path = os.path.join(MODEL_DIR, MODEL_FILE)

    # 1. Verify Model Exists
    if not os.path.exists(model_path):
        logger.error(f"❌ Model file not found: {model_path}")
        return

    # 2. Prepare Registry Entry
    new_entry = {
        "region_id": REGION_ID,
        "model_type": "lstm-pytorch",
        "version": "2.0",
        "status": "active", # <--- This makes it the 'Live' model
        "artifact_path": model_path,
        "registered_at": datetime.now(timezone.utc).isoformat()
    }

    # 3. Update Registry JSON
    registry = []
    if os.path.exists(registry_path):
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
        except Exception:
            registry = []

    # Deactivate old models for this region
    for entry in registry:
        if entry.get("region_id") == REGION_ID:
            entry["status"] = "archived"

    # Add new active model
    registry.append(new_entry)

    # Save
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=4)

    logger.info(f"✅ Model Registered Successfully!")
    logger.info(f"   📂 Registry: {registry_path}")
    logger.info(f"   🧠 Active Model: {MODEL_FILE}")

if __name__ == "__main__":
    register()