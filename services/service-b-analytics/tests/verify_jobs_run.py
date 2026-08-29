import json
import os
import sys
import tempfile
import numpy as np
import pandas as pd
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("."))
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from app import app
from src.modelling.training import run_training_pipeline
from src.modelling.update_registry import promote_models
from src.modelling.registry import load_raw_registry

def run_jobs_pipeline_e2e():
    print("=" * 80)
    print("🎬 FASTAPI PIPELINE RUN: MODEL GATING & PROMOTION gate VERIFICATION")
    print("=" * 80)

    # 1. Create a dummy feature store dataframe for one region
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2025-01-01', periods=n, freq='D')
    # Generate data where RandomForest will outperform LinearRegression
    rain = np.random.exponential(scale=2.0, size=n)
    ext = np.random.uniform(500, 1000, size=n)
    log_ext = np.log1p(ext)
    flux = rain - (log_ext * 0.1)
    
    # Non-linear target function (quadratic on rain + noise)
    water = 25.0 + 1.2 * (rain ** 1.8) - 0.9 * log_ext + np.random.normal(0, 0.05, n)

    df = pd.DataFrame({
        'date': dates,
        'region_id': '65f4fc28-a5f9-47e0-b326-962b20bb35b1',
        'target_water_level': water,
        'effective_rainfall': rain,
        'log_extraction': log_ext,
        'feat_net_flux_1d_lag': pd.Series(flux).shift(1).fillna(0),
        'feat_net_flux_window_sum': pd.Series(flux).shift(1).rolling(7, min_periods=1).sum(),
        'feat_water_trend_7d': pd.Series(water).diff(7).bfill().fillna(0),
        'feat_soil_permeability': 0.15,
        'feat_sin_day': np.sin(2 * np.pi * np.arange(n) / 365.0),
        'feat_cos_day': np.cos(2 * np.pi * np.arange(n) / 365.0)
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        reg_path = os.path.join(tmpdir, "model_registry.json")
        eval_path = os.path.join(tmpdir, "evaluation_summary.json")

        # Initial baseline registry state
        initial_registry = [
            {
                "region_id": "65f4fc28-a5f9-47e0-b326-962b20bb35b1",
                "model_type": "linear-regression",
                "version": "1.0-lr-baseline",
                "status": "active",
                "artifact_path": os.path.join(tmpdir, "legacy_lr.pkl"),
                "metadata_path": None,
                "registered_at": "2026-01-01T12:00:00+00:00",
                "promoted_at": "2026-01-01T12:00:00+00:00",
                "metrics": {
                    "mae": 1.2500,
                    "rmse": 1.5000,
                    "baseline_mae": 2.0000
                }
            }
        ]
        with open(reg_path, 'w') as f:
            json.dump(initial_registry, f, indent=2)

        print("\n--- [1] INITIAL REGISTRY STATE (Baseline Model: linear-regression) ---")
        print(json.dumps(initial_registry, indent=2))

        # Patch ARTIFACTS directories and database calls
        with patch("src.modelling.training.ARTIFACTS_ROOT", tmpdir), \
             patch("src.modelling.update_registry.ARTIFACTS_DIR", tmpdir), \
             patch("src.modelling.training.fetch_training_data", return_value=df):

            # 2. Trigger candidate training
            print("\n--- [2] TRAINING CANDIDATES (model_type='all') ---")
            candidates = run_training_pipeline(model_type="all")
            print(f"Generated {len(candidates)} candidates.")
            for c in candidates:
                print(f" -> Candidate: {c['model_type']} | MAE: {c['metrics']['mae']:.4f} | Baseline Persistence MAE: {c['metrics']['baseline_mae']:.4f}")

            # 3. Trigger promotion gate
            print("\n--- [3] RUNNING PROMOTION GATE ---")
            summary = promote_models(registry_path=reg_path, evaluation_path=eval_path)
            print(f"Promotion Summary: {summary}")

            # 4. View final registry state
            final_registry = load_raw_registry(reg_path)
            print("\n--- [4] FINAL REGISTRY STATE (After Promotion Gate) ---")
            print(json.dumps(final_registry, indent=2))

            # Verify that the candidate with the lowest MAE won
            best_candidate = min(candidates, key=lambda x: x["metrics"]["mae"])
            active_model = [e for e in final_registry if e["status"] == "active" and e["region_id"] == "65f4fc28-a5f9-47e0-b326-962b20bb35b1"][0]
            
            print(f"\n🏆 WINNER DETERMINATION:")
            print(f" Best candidate trained: {best_candidate['model_type']} (MAE: {best_candidate['metrics']['mae']:.4f})")
            print(f" Previous active model: linear-regression (MAE: 1.2500)")
            print(f" Promoted active model: {active_model['model_type']} (MAE: {active_model['metrics']['mae']:.4f})")

            assert active_model["model_type"] == best_candidate["model_type"]
            assert active_model["metrics"]["mae"] == best_candidate["metrics"]["mae"]

    print("\n" + "=" * 80)
    print("✅ E2E PIPELINE RUN SUCCESSFUL: Standardized registry gating confirmed")
    print("=" * 80)

if __name__ == "__main__":
    run_jobs_pipeline_e2e()
