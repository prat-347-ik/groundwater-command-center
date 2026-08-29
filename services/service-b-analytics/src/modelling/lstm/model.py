import os
import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.modelling.base import BaseGroundwaterModel
from src.modelling.lstm.architecture import GroundwaterLSTM

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = [
    'effective_rainfall', 
    'log_extraction', 
    'feat_net_flux_1d_lag', 
    'feat_soil_permeability', 
    'feat_sin_day', 
    'feat_cos_day'
]

class LSTMModel(BaseGroundwaterModel):
    """
    PyTorch Deep Learning Recurrent Model implementation (LSTM).
    Ported from feature/deep-learning branch with native feature scaling.
    """
    model_type = "lstm"
    version = "1.0-lstm"

    def __init__(
        self, 
        region_id: str, 
        features: Optional[List[str]] = None,
        sequence_length: int = 30,
        hidden_dim: int = 50,
        num_layers: int = 2,
        epochs: int = 100,
        learning_rate: float = 0.01,
        random_seed: Optional[int] = 42
    ):
        super().__init__(region_id=region_id)
        self.features = features or DEFAULT_FEATURES
        self.sequence_length = sequence_length
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.random_seed = random_seed

        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()

        if self.random_seed is not None:
            torch.manual_seed(self.random_seed)
            np.random.seed(self.random_seed)

        self.model = GroundwaterLSTM(
            input_dim=len(self.features),
            hidden_dim=self.hidden_dim,
            output_dim=1,
            num_layers=self.num_layers
        )

    def _create_sequences(self, data_scaled: np.ndarray, target_scaled: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Creates sliding window input sequences and next-step targets from scaled matrices."""
        xs, ys = [], []
        for i in range(len(data_scaled) - self.sequence_length):
            x = data_scaled[i : i + self.sequence_length]
            y = target_scaled[i + self.sequence_length]
            xs.append(x)
            ys.append(y)

        return np.array(xs), np.array(ys)

    def fit(self, df: pd.DataFrame, train_split_ratio: float = 0.80, min_history_days: int = 35, **kwargs) -> Dict[str, Any]:
        """
        Trains PyTorch LSTM model using scaled feature sequences and chronological split.
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
        df_region = df_region.fillna(0)

        min_required = self.sequence_length + 5
        if len(df_region) < min_required:
            logger.warning(f"⚠️ Region {self.region_id}: Insufficient history ({len(df_region)} < {min_required} rows)")
            return {}

        if self.random_seed is not None:
            torch.manual_seed(self.random_seed)
            np.random.seed(self.random_seed)

        # 1. Fit standard scalers on features and target
        X_raw = df_region[self.features].values
        y_raw = df_region[[self.target]].values

        X_scaled = self.scaler_X.fit_transform(X_raw)
        y_scaled = self.scaler_y.fit_transform(y_raw)

        # 2. Create sequences
        X_all, y_all = self._create_sequences(X_scaled, y_scaled)
        if len(X_all) == 0:
            return {}

        # 3. Chronological Train/Test Split on Sequences
        split_idx = max(1, int(len(X_all) * train_split_ratio))
        X_train, X_test = X_all[:split_idx], X_all[split_idx:]
        y_train, y_test = y_all[:split_idx], y_all[split_idx:]

        X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
        y_train_tensor = torch.tensor(y_train, dtype=torch.float32)

        # 4. Training Loop
        self.model = GroundwaterLSTM(
            input_dim=len(self.features),
            hidden_dim=self.hidden_dim,
            output_dim=1,
            num_layers=self.num_layers
        )
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

        self.model.train()
        for epoch in range(self.epochs):
            optimizer.zero_grad()
            outputs = self.model(X_train_tensor)
            loss = criterion(outputs, y_train_tensor)
            loss.backward()
            optimizer.step()

        self.is_fitted = True
        self.model.eval()

        # 5. Evaluation on Validation Sequences (in original water level units)
        if len(X_test) > 0:
            X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
            with torch.no_grad():
                scaled_preds = self.model(X_test_tensor).numpy()
            test_preds = self.scaler_y.inverse_transform(scaled_preds).flatten()
            y_test_orig = self.scaler_y.inverse_transform(y_test).flatten()
            mae = float(mean_absolute_error(y_test_orig, test_preds))
            rmse = float(np.sqrt(mean_squared_error(y_test_orig, test_preds)))
        else:
            with torch.no_grad():
                scaled_preds = self.model(X_train_tensor).numpy()
            train_preds = self.scaler_y.inverse_transform(scaled_preds).flatten()
            y_train_orig = self.scaler_y.inverse_transform(y_train).flatten()
            mae = float(mean_absolute_error(y_train_orig, train_preds))
            rmse = float(np.sqrt(mean_squared_error(y_train_orig, train_preds)))

        self.metrics = {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "train_size": len(X_train),
            "test_size": len(X_test)
        }

        logger.info(f"✅ Trained LSTM [{self.region_id}] | MAE: {mae:.4f} | RMSE: {rmse:.4f}")
        return self.get_metadata()

    def predict_horizon(
        self, 
        history_df: pd.DataFrame, 
        horizon_days: int = 7, 
        planned_extraction_schedule: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates recursive 7-day forecast using sliding 30-day tensor window.
        """
        if not self.is_fitted:
            raise RuntimeError(f"LSTMModel for region {self.region_id} is not fitted.")

        if history_df.empty:
            return []

        region_df = history_df.sort_values('date').copy()
        if len(region_df) < self.sequence_length:
            logger.warning(f"⚠️ Insufficient history for region {self.region_id} (Need {self.sequence_length}, Got {len(region_df)})")
            return []

        permeability = region_df['feat_soil_permeability'].iloc[-1] if 'feat_soil_permeability' in region_df.columns else 0.15
        last_date = pd.to_datetime(region_df['date'].iloc[-1])

        # Prepare initial 3D Tensor: scale raw inputs, shape (1, 30, len(features))
        raw_tail = region_df[self.features].fillna(0).values[-self.sequence_length:]
        scaled_tail = self.scaler_X.transform(raw_tail)
        current_seq = torch.tensor(scaled_tail, dtype=torch.float32).unsqueeze(0)

        forecasts = []
        is_scenario = planned_extraction_schedule is not None
        self.model.eval()

        for i in range(1, horizon_days + 1):
            with torch.no_grad():
                scaled_pred = self.model(current_seq).item()
                prediction = float(self.scaler_y.inverse_transform([[scaled_pred]])[0, 0])

            next_date = last_date + timedelta(days=i)
            day_of_year = next_date.dayofyear
            feat_sin = np.sin(2 * np.pi * day_of_year / 365.0)
            feat_cos = np.cos(2 * np.pi * day_of_year / 365.0)

            eff_rain = 0.0
            curr_ext = 0.0
            if planned_extraction_schedule and (i - 1) < len(planned_extraction_schedule):
                curr_ext = planned_extraction_schedule[i - 1]

            log_ext = np.log1p(curr_ext) if is_scenario else 0.0

            # Construct step feature row (6 features) and scale it
            next_raw_row = np.array([[
                eff_rain,
                log_ext,
                0.0, # net flux lag proxy
                permeability,
                feat_sin,
                feat_cos
            ]])
            next_scaled_row = self.scaler_X.transform(next_raw_row)

            # Slide window: drop oldest day, append new step context
            next_tensor = torch.tensor(next_scaled_row, dtype=torch.float32).unsqueeze(0)
            current_seq = torch.cat((current_seq[:, 1:, :], next_tensor), dim=1)

            forecasts.append({
                "region_id": self.region_id,
                "forecast_date": next_date.normalize().to_pydatetime(),
                "predicted_level": float(round(prediction, 4)),
                "model_version": f"v1.0-{self.model_type}",
                "created_at": pd.Timestamp.now(timezone.utc).to_pydatetime(),
                "horizon_step": i,
                "scenario_extraction": curr_ext if is_scenario else 0.0
            })

        return forecasts

    def predict_scenario(self, history_df: pd.DataFrame, rainfall_mod: float, extraction_mod: float) -> Dict[str, Any]:
        """
        Evaluates sensitivity simulation by perturbing latest step in sequence tensor.
        """
        if not self.is_fitted:
            raise RuntimeError(f"LSTMModel for region {self.region_id} is not fitted.")

        if len(history_df) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} history rows for LSTM scenario")

        region_df = history_df.sort_values('date').copy()
        raw_vals = region_df[self.features].fillna(0).values[-self.sequence_length:].copy()

        self.model.eval()

        # 1. Baseline sequence (scaled)
        base_scaled = self.scaler_X.transform(raw_vals)
        base_seq = torch.tensor(base_scaled, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            scaled_p_base = float(self.model(base_seq).item())
            pred_base = float(self.scaler_y.inverse_transform([[scaled_p_base]])[0, 0])

        # 2. Perturbed sequence (modify last day rainfall & extraction)
        sim_vals = raw_vals.copy()
        if 'effective_rainfall' in self.features:
            rain_idx = self.features.index('effective_rainfall')
            sim_vals[-1, rain_idx] = sim_vals[-1, rain_idx] * rainfall_mod

        if 'log_extraction' in self.features:
            ext_idx = self.features.index('log_extraction')
            curr_vol = np.expm1(sim_vals[-1, ext_idx])
            sim_vals[-1, ext_idx] = np.log1p(max(0.0, curr_vol * extraction_mod))

        sim_scaled = self.scaler_X.transform(sim_vals)
        sim_seq = torch.tensor(sim_scaled, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            scaled_p_sim = float(self.model(sim_seq).item())
            pred_sim = float(self.scaler_y.inverse_transform([[scaled_p_sim]])[0, 0])

        b_level = round(pred_base, 4)
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
        Computes feature importance via L1 weight norm attribution across LSTM input layer gates.
        """
        if not self.is_fitted:
            return []

        w_ih = self.model.lstm.weight_ih_l0.detach().abs().numpy()
        feature_scores = w_ih.sum(axis=0)
        total_score = feature_scores.sum() if feature_scores.sum() > 0 else 1.0
        normalized_scores = feature_scores / total_score

        result = [
            {"feature": feat, "importance": float(round(score, 4))}
            for feat, score in zip(self.features, normalized_scores)
        ]
        return sorted(result, key=lambda x: x['importance'], reverse=True)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        checkpoint = {
            'state_dict': self.model.state_dict(),
            'scaler_X_mean': self.scaler_X.mean_,
            'scaler_X_scale': self.scaler_X.scale_,
            'scaler_y_mean': self.scaler_y.mean_,
            'scaler_y_scale': self.scaler_y.scale_,
            'features': self.features,
            'hidden_dim': self.hidden_dim,
            'num_layers': self.num_layers,
            'sequence_length': self.sequence_length,
            'metrics': self.metrics
        }
        torch.save(checkpoint, filepath)
        logger.info(f"💾 Saved LSTMModel checkpoint to {filepath}")

    def load(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact not found at {filepath}")
        checkpoint = torch.load(filepath, map_location=torch.device('cpu'), weights_only=False)
        
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            self.features = checkpoint.get('features', self.features)
            self.hidden_dim = checkpoint.get('hidden_dim', self.hidden_dim)
            self.num_layers = checkpoint.get('num_layers', self.num_layers)
            self.sequence_length = checkpoint.get('sequence_length', self.sequence_length)
            self.metrics = checkpoint.get('metrics', self.metrics)

            self.scaler_X.mean_ = checkpoint['scaler_X_mean']
            self.scaler_X.scale_ = checkpoint['scaler_X_scale']
            self.scaler_y.mean_ = checkpoint['scaler_y_mean']
            self.scaler_y.scale_ = checkpoint['scaler_y_scale']

            self.model = GroundwaterLSTM(
                input_dim=len(self.features),
                hidden_dim=self.hidden_dim,
                output_dim=1,
                num_layers=self.num_layers
            )
            self.model.load_state_dict(checkpoint['state_dict'])
        else:
            # Fallback for raw state_dict
            self.model.load_state_dict(checkpoint)

        self.is_fitted = True
        self.model.eval()
        logger.info(f"📂 Loaded LSTMModel from {filepath}")
