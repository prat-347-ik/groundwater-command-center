import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd

class BaseGroundwaterModel(ABC):
    """
    Standard abstract base class for groundwater forecasting models.
    Supports Linear Regression (OLS), Random Forest, and PyTorch LSTM architectures.
    """
    model_type: str
    version: str
    features: List[str]
    target: str = "target_water_level"

    def __init__(self, region_id: str):
        self.region_id = region_id
        self.is_fitted = False
        self.metrics: Dict[str, float] = {}

    @abstractmethod
    def fit(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Trains the model on chronological feature store dataframe for the region.
        
        Args:
            df: Historical DataFrame containing FEATURES and TARGET columns sorted by date.
            
        Returns:
            Dict containing training metadata and evaluation metrics (MAE, RMSE, sizes).
        """
        pass

    @abstractmethod
    def predict_horizon(
        self, 
        history_df: pd.DataFrame, 
        horizon_days: int = 7, 
        planned_extraction_schedule: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates a multi-day recursive forecast horizon.
        
        Args:
            history_df: Historical feature DataFrame for the region.
            horizon_days: Number of days forward to predict (default: 7).
            planned_extraction_schedule: Optional list of extraction volumes for Scenario mode.
            
        Returns:
            List of forecast dicts conforming to ForecastResponse schema.
        """
        pass

    @abstractmethod
    def predict_scenario(
        self, 
        history_df: pd.DataFrame, 
        rainfall_mod: float, 
        extraction_mod: float
    ) -> Dict[str, Any]:
        """
        Runs single-step sensitivity simulation with rainfall and extraction multipliers.
        
        Args:
            history_df: Historical DataFrame for the region.
            rainfall_mod: Multiplier for rainfall (e.g., 0.8 for -20%, 1.2 for +20%).
            extraction_mod: Multiplier for extraction (e.g., 1.1 for +10%).
            
        Returns:
            Dict with keys: region_id, baseline_level, simulated_level, delta, modifiers.
        """
        pass

    @abstractmethod
    def get_feature_importance(self) -> List[Dict[str, Any]]:
        """
        Returns ranked list of feature drivers and relative weights/importance.
        
        Returns:
            List of dicts: [{"feature": str, "importance": float}, ...] sorted descending.
        """
        pass

    @abstractmethod
    def save(self, filepath: str) -> None:
        """Serializes model artifact to disk (.pkl or .pth)."""
        pass

    @abstractmethod
    def load(self, filepath: str) -> None:
        """Deserializes model artifact from disk."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Returns standard metadata for model registry and candidate gating."""
        return {
            "region_id": self.region_id,
            "model_type": self.model_type,
            "version": self.version,
            "features": self.features,
            "target": self.target,
            "metrics": self.metrics,
            "is_fitted": self.is_fitted
        }
