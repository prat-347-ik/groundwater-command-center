import os
import json
import logging
from typing import Dict, Any, List, Optional, Type

from src.modelling.base import BaseGroundwaterModel
from src.modelling.linear_regression.model import LinearRegressionModel
from src.modelling.random_forest.model import RandomForestModel
from src.modelling.lstm.model import LSTMModel

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "models/v1"
DEFAULT_REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")

# Canonical model type identifiers mapped to implementation classes
CANONICAL_TYPES: Dict[str, Type[BaseGroundwaterModel]] = {
    "linear-regression": LinearRegressionModel,
    "random-forest": RandomForestModel,
    "lstm": LSTMModel,
}

# Alias dictionary used strictly for normalizing legacy keys to canonical keys
MODEL_TYPE_ALIASES: Dict[str, str] = {
    "linear-regression": "linear-regression",
    "linear_regression": "linear-regression",
    "linear-regression-sklearn": "linear-regression",
    "lr": "linear-regression",
    "random-forest": "random-forest",
    "random_forest": "random-forest",
    "random-forest-sklearn": "random-forest",
    "rf": "random-forest",
    "lstm": "lstm",
    "lstm-pytorch": "lstm",
    "lstm_pytorch": "lstm",
}

class ModelNotFoundError(Exception):
    """Raised when no model entry exists for a given region in the registry."""
    pass

class ModelArtifactNotFoundError(FileNotFoundError):
    """Raised when a registered model's artifact file is missing on disk."""
    pass

def normalize_model_type(raw_type: str) -> str:
    """Normalizes any model type alias into its canonical key."""
    cleaned = raw_type.strip().lower()
    if cleaned in MODEL_TYPE_ALIASES:
        return MODEL_TYPE_ALIASES[cleaned]
    raise ValueError(f"Unknown model_type '{raw_type}'. Supported: {list(CANONICAL_TYPES.keys())}")

def resolve_model_type(
    region_id: Optional[str] = None,
    requested_type: Optional[str] = None,
    registry_entry: Optional[Dict[str, Any]] = None,
    artifact_path: Optional[str] = None,
    default_type: str = "random-forest"
) -> str:
    """
    Resolves the model type using strict production hierarchy:
    1. Explicit requested_type (API / ad-hoc scenario simulation override)
    2. Active registry record's model_type field (authoritative per-region promotion state)
    3. Inferred type from artifact file path / extension (if record exists on disk)
    4. ACTIVE_MODEL environment variable (manual debug fallback with loud warning)
    5. Default fallback ('random-forest')
    """
    # 1. Caller / request parameter override
    if requested_type:
        return normalize_model_type(requested_type)

    # 2. Authoritative per-region active registry decision
    if registry_entry and registry_entry.get("model_type"):
        return normalize_model_type(registry_entry["model_type"])

    # 3. Inferred from artifact file path / extension
    if artifact_path:
        ext = os.path.splitext(artifact_path)[1].lower()
        base_name = os.path.basename(artifact_path).lower()
        if ext in ('.pth', '.pt') or 'lstm' in base_name:
            return "lstm"
        if 'rf' in base_name or 'random_forest' in base_name:
            return "random-forest"
        if 'lr' in base_name or 'linear_regression' in base_name or 'linear-regression' in base_name:
            return "linear-regression"

    # 4. ACTIVE_MODEL environment variable (Manual debug fallback)
    env_override = os.getenv("ACTIVE_MODEL")
    if env_override:
        logger.warning(
            f"⚠️ ACTIVE_MODEL environment variable '{env_override}' is active and overriding "
            f"default fallback for region '{region_id or 'unknown'}'. Per-region registry record was not found."
        )
        return normalize_model_type(env_override)

    # 5. Default fallback
    return normalize_model_type(default_type)

def load_raw_registry(registry_path: str = DEFAULT_REGISTRY_PATH) -> List[Dict[str, Any]]:
    """Loads the model registry JSON file safely."""
    if not os.path.exists(registry_path):
        logger.warning(f"⚠️ Model registry not found at {registry_path}")
        return []
    try:
        with open(registry_path, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"❌ Failed to parse model registry at {registry_path}: {e}")
        return []

def get_model_entry(region_id: str, registry_path: str = DEFAULT_REGISTRY_PATH) -> Dict[str, Any]:
    """
    Finds the active or promoted model entry for a given region_id.
    Prioritizes status in ('active', 'prod').
    """
    entries = load_raw_registry(registry_path)
    # Search in reverse to prefer latest promotions/registrations
    for entry in reversed(entries):
        if entry.get("region_id") == region_id and entry.get("status") in ("active", "prod"):
            return entry
    
    # Fallback to any entry for this region
    for entry in reversed(entries):
        if entry.get("region_id") == region_id:
            return entry

    raise ModelNotFoundError(f"No registered model found for region: '{region_id}'")

def get_model(
    region_id: str, 
    requested_type: Optional[str] = None,
    registry_path: str = DEFAULT_REGISTRY_PATH
) -> BaseGroundwaterModel:
    """
    Factory function: Loads and returns the active BaseGroundwaterModel instance for a region.
    Raises:
        ModelNotFoundError: If region is not registered.
        ModelArtifactNotFoundError: If artifact file is missing on disk.
    """
    entry = get_model_entry(region_id, registry_path=registry_path)
    artifact_path = entry.get("artifact_path", "")
    
    normalized_path = os.path.normpath(artifact_path)
    
    if not os.path.exists(normalized_path):
        raise ModelArtifactNotFoundError(
            f"Model artifact for region '{region_id}' not found at '{normalized_path}'."
        )

    canonical_type = resolve_model_type(
        region_id=region_id,
        requested_type=requested_type,
        registry_entry=entry,
        artifact_path=normalized_path
    )
    model_cls = CANONICAL_TYPES[canonical_type]
    model = model_cls(region_id=region_id)
    model.load(normalized_path)
    return model

def load_active_models(
    requested_type: Optional[str] = None,
    registry_path: str = DEFAULT_REGISTRY_PATH
) -> Dict[str, BaseGroundwaterModel]:
    """
    Loads all active/prod models across all regions.
    Returns:
        Dict mapping region_id -> BaseGroundwaterModel instance.
    """
    entries = load_raw_registry(registry_path)
    loaded_models: Dict[str, BaseGroundwaterModel] = {}
    
    active_entries = [e for e in entries if e.get("status") in ("active", "prod")]
    for entry in active_entries:
        region_id = entry.get("region_id")
        if not region_id or region_id in loaded_models:
            continue
        try:
            model = get_model(region_id, requested_type=requested_type, registry_path=registry_path)
            loaded_models[region_id] = model
        except (ModelNotFoundError, ModelArtifactNotFoundError) as e:
            logger.warning(f"⚠️ Skipping region {region_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error loading model for {region_id}: {e}")
            
    return loaded_models
