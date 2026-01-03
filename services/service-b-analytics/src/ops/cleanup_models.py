import os
import json
import shutil
import logging
from datetime import datetime
from collections import defaultdict
from typing import List, Set, Dict

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Paths relative to the script execution or absolute paths
BASE_DIR = "models/v1"
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")
REGISTRY_PATH = os.path.join(BASE_DIR, "model_registry.json")
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")

# Retention Policy
RETENTION_COUNT = 3  # Keep the last N artifacts per region, regardless of active status

def load_active_artifacts() -> Set[str]:
    """
    Reads the registry to build a strict 'Do Not Touch' list.
    """
    if not os.path.exists(REGISTRY_PATH):
        logger.error(f"❌ Registry not found at {REGISTRY_PATH}. Aborting cleanup.")
        return set()

    try:
        with open(REGISTRY_PATH, 'r') as f:
            registry = json.load(f)
            
        # Extract the filenames from the full paths
        active_files = set()
        for entry in registry:
            if entry.get('status') == 'active':
                full_path = entry.get('artifact_path', '')
                filename = os.path.basename(full_path)
                active_files.add(filename)
                
        return active_files
    except Exception as e:
        logger.error(f"❌ Failed to read registry: {e}")
        raise e

def parse_artifact_filename(filename: str):
    """
    Parses {region_id}_{timestamp}_{hash}.pkl
    Returns (region_id, timestamp_obj) or None if invalid.
    """
    try:
        # Strip extension
        name_body = os.path.splitext(filename)[0]
        parts = name_body.split('_')
        
        # We expect at least region (variable length), date, time, hash
        # Standard: region_id_YYYYMMDD_HHMMSS_hash
        # Robust parsing: Look for the date/time pattern from the end
        
        if len(parts) < 4:
            return None
            
        timestamp_str = f"{parts[-3]}_{parts[-2]}"
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        
        # Region is everything before the date
        region_id = "_".join(parts[:-3])
        
        return region_id, timestamp
    except (ValueError, IndexError):
        return None

def run_cleanup():
    logger.info("🧹 Starting Model Artifact Cleanup...")
    
    # 1. Setup Archive
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # 2. Build Safety Allowlist (Active Models)
    active_artifacts = load_active_artifacts()
    if not active_artifacts and os.path.exists(REGISTRY_PATH):
        logger.warning("⚠️ Registry exists but no active models found. Proceeding with caution.")
    
    logger.info(f"🛡️ Protected Active Artifacts: {active_artifacts}")

    # 3. Scan Artifacts Directory
    if not os.path.exists(ARTIFACTS_DIR):
        logger.info("No artifacts directory found. Exiting.")
        return

    all_files = [f for f in os.listdir(ARTIFACTS_DIR) if f.endswith('.pkl')]
    
    # 4. Group by Region for Retention Policy
    region_groups = defaultdict(list)
    unknown_files = []

    for f in all_files:
        parsed = parse_artifact_filename(f)
        if parsed:
            r_id, ts = parsed
            region_groups[r_id].append({'file': f, 'ts': ts})
        else:
            unknown_files.append(f)

    # 5. Determine Files to Move
    files_to_move = []

    # Process structured files
    for region, artifacts in region_groups.items():
        # Sort by time descending (newest first)
        sorted_artifacts = sorted(artifacts, key=lambda x: x['ts'], reverse=True)
        
        # Keep Top N
        keep_list = sorted_artifacts[:RETENTION_COUNT]
        candidate_cleanup = sorted_artifacts[RETENTION_COUNT:]
        
        # Check candidates against Active List
        for item in candidate_cleanup:
            fname = item['file']
            if fname in active_artifacts:
                logger.info(f"  🔒 Keeping {fname} (Active in Registry, despite being old)")
            else:
                files_to_move.append(fname)

    # Process unknown files (Safest to move them if they aren't active)
    for fname in unknown_files:
        if fname not in active_artifacts:
            logger.warning(f"  ❓ Moving unrecognized file: {fname}")
            files_to_move.append(fname)

    # 6. Execute Move (Cleanup)
    if not files_to_move:
        logger.info("✅ No artifacts to clean up.")
        return

    logger.info(f"📦 Moving {len(files_to_move)} artifacts to {ARCHIVE_DIR}...")
    
    for fname in files_to_move:
        src = os.path.join(ARTIFACTS_DIR, fname)
        dst = os.path.join(ARCHIVE_DIR, fname)
        try:
            shutil.move(src, dst)
            logger.info(f"  Moved: {fname}")
        except Exception as e:
            logger.error(f"  ❌ Error moving {fname}: {e}")

    logger.info("✨ Cleanup Complete.")

if __name__ == "__main__":
    run_cleanup()