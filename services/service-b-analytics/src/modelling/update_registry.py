import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

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

def promote_models(registry_path: str = REGISTRY_PATH, evaluation_path: str = EVALUATION_PATH) -> Dict[str, Any]:
    """
    Evaluates candidate models from the latest training run and promotes the best candidate
    per region into the registry if it outperforms the baseline (and current active model).
    """
    logger.info("🛡️ Starting Model Promotion Gate...")

    # 1. Load Current Registry
    current_registry: List[Dict[str, Any]] = load_json_file(registry_path, default=[])
    if not isinstance(current_registry, list):
        raise ValueError(f"Registry format error: Expected list, got {type(current_registry)}")
        
    # Index current active models by region_id
    active_by_region: Dict[str, Dict[str, Any]] = {}
    for entry in current_registry:
        if entry.get("status") in ("active", "prod"):
            active_by_region[entry["region_id"]] = entry

    logger.info(f"📋 Current Registry contains {len(active_by_region)} active models across {len(current_registry)} total entries.")

    # 2. Load Evaluation Candidates
    try:
        candidates: List[Dict[str, Any]] = load_json_file(evaluation_path)
    except FileNotFoundError:
        logger.warning("⚠️ No evaluation summary found. Skipping promotion.")
        return {"promoted": 0, "rejected": 0, "active_count": len(active_by_region)}

    if not candidates:
        logger.warning("⚠️ Evaluation summary is empty. No candidates to promote.")
        return {"promoted": 0, "rejected": 0, "active_count": len(active_by_region)}

    # 3. Group candidates by region and find the best candidate per region
    candidates_by_region: Dict[str, List[Dict[str, Any]]] = {}
    for c in candidates:
        rid = c.get("region_id")
        if rid:
            candidates_by_region.setdefault(rid, []).append(c)

    promoted_count = 0
    rejected_count = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    # Create working copy of registry
    updated_registry = list(current_registry)

    for region_id, region_candidates in candidates_by_region.items():
        # Sort candidates by MAE ascending
        best_candidate = min(region_candidates, key=lambda x: x.get("metrics", {}).get("mae", 999.0))
        candidate_mae = best_candidate.get("metrics", {}).get("mae", 999.0)
        baseline_mae = best_candidate.get("metrics", {}).get("baseline_mae", 999.0)
        model_type = best_candidate.get("model_type", "unknown")

        current_active = active_by_region.get(region_id)
        current_active_mae = (
            current_active.get("metrics", {}).get("mae", 999.0)
            if current_active and current_active.get("metrics")
            else baseline_mae
        )

        # Promotion Gate Condition:
        # Candidate MAE must be strictly less than baseline MAE AND <= current active MAE
        is_promotable = (candidate_mae < baseline_mae) and (candidate_mae <= current_active_mae)

        if is_promotable:
            logger.info(
                f"✅ Promoting {region_id} [{model_type}]: "
                f"MAE {candidate_mae:.4f} < Baseline {baseline_mae:.4f} (Prev Active: {current_active_mae:.4f})"
            )
            
            # Archive previous active entry for this region
            for entry in updated_registry:
                if entry.get("region_id") == region_id and entry.get("status") in ("active", "prod"):
                    entry["status"] = "archived"

            # Construct standardized registry record
            promoted_entry = {
                "region_id": region_id,
                "model_type": model_type,
                "version": best_candidate.get("version", "v1.0"),
                "status": "active",
                "artifact_path": best_candidate["artifact_path"],
                "metadata_path": best_candidate.get("metadata_path"),
                "registered_at": best_candidate.get("registered_at", now_iso),
                "promoted_at": now_iso,
                "metrics": best_candidate.get("metrics")
            }
            
            updated_registry.append(promoted_entry)
            promoted_count += 1
        else:
            logger.warning(
                f"⛔ Rejecting {region_id} [{model_type}]: "
                f"MAE {candidate_mae:.4f} >= Baseline {baseline_mae:.4f} or higher than active {current_active_mae:.4f}"
            )
            rejected_count += 1

    # 4. Atomic Write Strategy
    if promoted_count > 0:
        tmp_path = registry_path + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(updated_registry, f, indent=2)
            
        os.replace(tmp_path, registry_path)
        logger.info(
            f"🚀 Registry updated atomically. Promoted: {promoted_count}, "
            f"Rejected: {rejected_count}, Total Entries: {len(updated_registry)}"
        )
    else:
        logger.info("💤 No models met promotion criteria. Registry remains unchanged.")

    return {
        "promoted": promoted_count,
        "rejected": rejected_count,
        "total_entries": len(updated_registry)
    }

if __name__ == "__main__":
    promote_models()