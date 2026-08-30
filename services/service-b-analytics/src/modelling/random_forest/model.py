import os
import joblib
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.modelling.base import BaseGroundwaterModel

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = [
    'effective_rainfall', 
    'log_extraction', 
    'feat_net_flux_1d_lag', 
    'feat_net_flux_window_sum', 
    'feat_water_trend_7d', 
    'feat_soil_permeability', 
    'feat_sin_day', 
    'feat_cos_day'
]

class RandomForestModel(BaseGroundwaterModel):
    """
    Random Forest Regressor model implementation.
    Ported directly from feature/random-forest branch.
    """
    model_type = "random-forest"
    version = "1.0-rf"

    def __init__(
        self, 
        region_id: str, 
        features: Optional[List[str]] = None,
        n_estimators: int = 100,
        max_depth: int = 15,
        random_state: int = 42,
        n_jobs: int = -1
    ):
        super().__init__(region_id=region_id)
        self.features = features or DEFAULT_FEATURES
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
            n_jobs=self.n_jobs
        )

    def fit(self, df: pd.DataFrame, train_split_ratio: float = 0.80, min_history_days: int = 30, **kwargs) -> Dict[str, Any]:
        """
        Trains Random Forest model using chronological split for evaluation, then refits on full dataset.
        """
        df_region = df.sort_values('date').reset_index(drop=True)
        missing_features = [f for f in self.features if f not in df_region.columns]
        if missing_features:
            logger.warning(
                f"⚠️ Region {self.region_id}: Missing expected features {missing_features} in input dataframe. "
                f"Training on available subset: {[f for f in self.features if f in df_region.columns]}"
            )
        active_features = [f for f in self.features if f in df_region.columns]
        if not active_features:
            raise ValueError(f"No valid features found in dataframe for region {self.region_id}")
        self.features = active_features
        
        df_region = df_region.dropna(subset=self.features + [self.target])

        if len(df_region) < min_history_days:
            logger.warning(f"⚠️ Region {self.region_id}: Insufficient history ({len(df_region)} < {min_history_days} days)")
            return {}

        # 1. Time-series aware split for validation
        split_idx = int(len(df_region) * train_split_ratio)
        train_df = df_region.iloc[:split_idx]
        test_df = df_region.iloc[split_idx:]

        X_train = train_df[self.features]
        y_train = train_df[self.target]
        X_test = test_df[self.features]
        y_test = test_df[self.target]

        # 2. Evaluate candidate model on validation set
        val_model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
            n_jobs=self.n_jobs
        )
        val_model.fit(X_train, y_train)
        predictions = val_model.predict(X_test)
        mae = float(mean_absolute_error(y_test, predictions))
        rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))

        # Baseline persistence
        persistence_pred = test_df[self.target].shift(1)
        valid_indices = persistence_pred.dropna().index
        persistence_mae = float(mean_absolute_error(test_df.loc[valid_indices, self.target], persistence_pred.loc[valid_indices])) if len(valid_indices) > 0 else mae

        # 3. Fit production model on full data for maximum recency
        X_full = df_region[self.features]
        y_full = df_region[self.target]
        self.model.fit(X_full, y_full)
        self.is_fitted = True

        self.metrics = {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "baseline_mae": round(persistence_mae, 4),
            "train_size": len(train_df),
            "test_size": len(test_df)
        }

        logger.info(f"✅ Trained RandomForest [{self.region_id}] | MAE: {mae:.4f} | RMSE: {rmse:.4f}")
        return self.get_metadata()

    def predict_horizon(
        self, 
        history_df: pd.DataFrame, 
        horizon_days: int = 7, 
        planned_extraction_schedule: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates recursive multi-step forecasting over horizon_days.
        """
        if not self.is_fitted:
            raise RuntimeError(f"RandomForestModel for region {self.region_id} is not fitted.")

        if history_df.empty:
            return []

        region_df = history_df.sort_values('date').copy()
        sim_buffer = region_df.to_dict('records')
        permeability = region_df['feat_soil_permeability'].iloc[-1] if 'feat_soil_permeability' in region_df.columns else 0.15
        last_date = pd.to_datetime(region_df['date'].iloc[-1])

        forecasts = []
        is_scenario = planned_extraction_schedule is not None

        for i in range(1, horizon_days + 1):
            next_date = last_date + timedelta(days=i)
            eff_rain = 0.0

            current_planned_extraction = 0.0
            if planned_extraction_schedule and (i - 1) < len(planned_extraction_schedule):
                current_planned_extraction = planned_extraction_schedule[i - 1]

            log_ext = np.log1p(current_planned_extraction) if is_scenario else 0.0
            current_net_flux = eff_rain - (log_ext * 0.1)

            prev_row = sim_buffer[-1]
            feat_flux_lag_1 = prev_row.get('net_flux_proxy', prev_row.get('effective_rainfall', 0) - (prev_row.get('log_extraction', 0) * 0.1))

            recent_fluxes = [
                r.get('net_flux_proxy', r.get('effective_rainfall', 0) - (r.get('log_extraction', 0) * 0.1))
                for r in sim_buffer[-7:]
            ]
            feat_flux_window = sum(recent_fluxes)

            val_t_minus_1 = sim_buffer[-1].get('target_water_level', sim_buffer[-1].get('avg_water_level', 0))
            val_t_minus_8 = sim_buffer[-8].get('target_water_level', sim_buffer[-8].get('avg_water_level', 0)) if len(sim_buffer) >= 8 else val_t_minus_1
            feat_trend_7d = val_t_minus_1 - val_t_minus_8

            day_of_year = next_date.dayofyear
            feat_sin = np.sin(2 * np.pi * day_of_year / 365.0)
            feat_cos = np.cos(2 * np.pi * day_of_year / 365.0)

            row_dict = {
                'effective_rainfall': eff_rain,
                'log_extraction': log_ext,
                'feat_net_flux_1d_lag': feat_flux_lag_1,
                'feat_net_flux_window_sum': feat_flux_window,
                'feat_water_trend_7d': feat_trend_7d,
                'feat_soil_permeability': permeability,
                'feat_sin_day': feat_sin,
                'feat_cos_day': feat_cos
            }
            input_row = pd.DataFrame([[row_dict.get(f, 0.0) for f in self.features]], columns=self.features)
            prediction = float(self.model.predict(input_row)[0])

            sim_buffer.append({
                'date': next_date,
                'region_id': self.region_id,
                'target_water_level': prediction,
                'net_flux_proxy': current_net_flux,
                'effective_rainfall': eff_rain,
                'log_extraction': log_ext
            })

            forecasts.append({
                "region_id": self.region_id,
                "forecast_date": next_date.normalize().to_pydatetime(),
                "predicted_level": float(round(prediction, 4)),
                "model_version": f"v1.0-{self.model_type}",
                "created_at": pd.Timestamp.now(timezone.utc).to_pydatetime(),
                "horizon_step": i,
                "scenario_extraction": current_planned_extraction if is_scenario else 0.0
            })

        return forecasts

    def predict_scenario(self, history_df: pd.DataFrame, rainfall_mod: float, extraction_mod: float) -> Dict[str, Any]:
        """
        Runs single-step sensitivity simulation using Random Forest.
        """
        if not self.is_fitted:
            raise RuntimeError(f"RandomForestModel for region {self.region_id} is not fitted.")

        if history_df.empty:
            raise ValueError(f"No history data available for region {self.region_id}")

        last_row = history_df.iloc[-1].to_dict()

        def prepare_vector(row_data: Dict[str, Any], apply_mods: bool = False) -> pd.DataFrame:
            eff_rain = row_data.get('effective_rainfall', 0.0)
            log_ext = row_data.get('log_extraction', 0.0)

            if apply_mods:
                eff_rain *= rainfall_mod
                current_vol = np.expm1(log_ext)
                new_vol = max(0.0, current_vol * extraction_mod)
                log_ext = np.log1p(new_vol)

            vec_dict = {
                'effective_rainfall': eff_rain,
                'log_extraction': log_ext,
                'feat_net_flux_1d_lag': row_data.get('feat_net_flux_1d_lag', 0.0),
                'feat_net_flux_window_sum': row_data.get('feat_net_flux_window_sum', 0.0),
                'feat_water_trend_7d': row_data.get('feat_water_trend_7d', 0.0),
                'feat_soil_permeability': row_data.get('feat_soil_permeability', 0.15),
                'feat_sin_day': row_data.get('feat_sin_day', 0.0),
                'feat_cos_day': row_data.get('feat_cos_day', 0.0)
            }
            return pd.DataFrame([[vec_dict.get(f, 0.0) for f in self.features]], columns=self.features)

        vec_baseline = prepare_vector(last_row, apply_mods=False)
        pred_baseline = float(self.model.predict(vec_baseline)[0])

        vec_sim = prepare_vector(last_row, apply_mods=True)
        pred_sim = float(self.model.predict(vec_sim)[0])

        b_level = round(pred_baseline, 4)
        s_level = round(pred_sim, 4)

        return {
            "region_id": self.region_id,
            "baseline_level": b_level,
            "simulated_level": s_level,
            "delta": round(s_level - b_level, 4),
            "modifiers": {
                "rainfall": rainfall_mod,
                "extraction": extraction_mod
            }
        }

    def get_feature_importance(self) -> List[Dict[str, Any]]:
        """
        Returns feature importances extracted from the Random Forest model.
        """
        if not self.is_fitted or not hasattr(self.model, 'feature_importances_'):
            return []

        importances = self.model.feature_importances_
        result = [
            {"feature": feat, "importance": float(round(imp, 4))}
            for feat, imp in zip(self.features, importances)
        ]
        return sorted(result, key=lambda x: x['importance'], reverse=True)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.model, filepath, compress=3)
        logger.info(f"💾 Saved RandomForestModel artifact to {filepath}")

    def load(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact not found at {filepath}")
        self.model = joblib.load(filepath)
        self.is_fitted = True
        logger.info(f"📂 Loaded RandomForestModel from {filepath}")
