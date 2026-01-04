import os
import json
import logging
import shutil
from datetime import datetime, timezone
from typing import List, Dict, Any

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")
EVALUATION_PATH = os.path.join(ARTIFACTS_DIR, "evaluation_summary.json")

def load_json_file(filepath: str, default: Any = None) -> Any:
    """Helper to load JSON safely."""
    if not os.path.exists(filepath):
        if default is not None:
            return default
        raise FileNotFoundError(f"Required file not found: {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted JSON in {filepath}: {e}")

def promote_models():
    """
    Evaluates candidates from the latest run and promotes them to the registry
    if they outperform the baseline.
    """
    logger.info("🛡️ Starting Model Promotion Gate...")

    # 1. Load Current Registry
    # We use a Dict for O(1) access and to enforce "One active model per region"
    current_registry_list = load_json_file(REGISTRY_PATH, default=[])
    
    # Validation: Fail fast if registry is malformed
    if not isinstance(current_registry_list, list):
        raise ValueError(f"Registry format error: Expected list, got {type(current_registry_list)}")
        
    registry_map = {entry['region_id']: entry for entry in current_registry_list}
    logger.info(f"📋 Current Registry: {len(registry_map)} active models.")

    # 2. Load Evaluation Candidates
    try:
        candidates = load_json_file(EVALUATION_PATH)
    except FileNotFoundError:
        logger.warning("⚠️ No evaluation summary found. Skipping promotion.")
        return

    promoted_count = 0
    rejected_count = 0

    # 3. Evaluate Candidates
    for candidate in candidates:
        region_id = candidate['region_id']
        mae = candidate['mae']
        baseline = candidate['baseline_mae']
        
        # LOGIC: Gated Promotion
        # Only promote if Model Error < Baseline Error
        if mae < baseline:
            logger.info(f"✅ Promoting {region_id}: MAE {mae} < Baseline {baseline}")
            
            # Construct Registry Entry
            # We preserve specific fields required by predictor.py and audit trails
            new_entry = {
                "region_id": region_id,
                "artifact_path": candidate['artifact_path'],
                "metadata_path": candidate.get('metadata_path', ''), # robust get
                "promoted_at": datetime.now(timezone.utc).isoformat(),
                "metrics": {
                    "mae": mae,
                    "rmse": candidate.get('rmse'),
                    "baseline_mae": baseline
                },
                "status": "prod"
            }
            
            # Update/Insert (Overwrites previous model for this region)
            registry_map[region_id] = new_entry
            promoted_count += 1
        else:
            logger.warning(f"⛔ Rejecting {region_id}: MAE {mae} >= Baseline {baseline}")
            rejected_count += 1

    # 4. Atomic Write Strategy
    if promoted_count > 0:
        # Convert map back to list (stable sorting for readability)
        new_registry_list = sorted(registry_map.values(), key=lambda x: x['region_id'])
        
        # Write to temp file first
        tmp_path = REGISTRY_PATH + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(new_registry_list, f, indent=2)
            
        # Atomic Swap
        os.replace(tmp_path, REGISTRY_PATH)
        logger.info(f"🚀 Registry updated. Promoted: {promoted_count}, Rejected: {rejected_count}, Total Active: {len(new_registry_list)}")
    else:
        logger.info("💤 No models promoted. Registry remains unchanged.")

if __name__ == "__main__":
    try:
        promote_models()
    except Exception as e:
        logger.exception(f"❌ Promotion Failed: {e}")
        exit(1)