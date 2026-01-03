import os
import json
import logging
from typing import Dict, List, Any

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
ARTIFACTS_DIR = "models/v1"
REGISTRY_PATH = os.path.join(ARTIFACTS_DIR, "model_registry.json")
EXPLAINABILITY_REPORT_PATH = os.path.join(ARTIFACTS_DIR, "model_explainability.md")

# Feature dictionary for translating technical terms to Hydrologist-friendly language
FEATURE_GLOSSARY = {
    "feat_rainfall_1d_lag": {
        "name": "Immediate Rainfall (Yesterday)",
        "physics": "Surface Recharge Shock",
        "unit": "mm"
    },
    "feat_rainfall_7d_sum": {
        "name": "Weekly Rainfall Sum",
        "physics": "Soil Saturation / Deep Recharge",
        "unit": "mm"
    },
    "feat_water_trend_7d": {
        "name": "7-Day Water Trend",
        "physics": "System Momentum",
        "unit": "meters"
    },
    "feat_sin_day": {
        "name": "Seasonality (Sine component)",
        "physics": "Cyclical Climate Pattern",
        "unit": "unitless"
    },
    "feat_cos_day": {
        "name": "Seasonality (Cosine component)",
        "physics": "Cyclical Climate Pattern",
        "unit": "unitless"
    }
}

def load_registry() -> List[Dict[str, Any]]:
    """Loads the trained model registry."""
    if not os.path.exists(REGISTRY_PATH):
        logger.error(f"❌ Registry not found at {REGISTRY_PATH}. Train models first.")
        return []
    
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def interpret_coefficient(feature_name: str, value: float) -> str:
    """
    Generates a natural language explanation for a single coefficient.
    
    Logic:
    - Direction: Positive (+) vs Negative (-)
    - Magnitude: Interpreted as impact per unit change.
    """
    meta = FEATURE_GLOSSARY.get(feature_name, {"name": feature_name, "physics": "Unknown", "unit": "units"})
    
    direction = "INCREASES" if value > 0 else "DECREASES"
    
    return (
        f"  * **{meta['name']}** ({meta['physics']}):\n"
        f"    - Weight: `{value:.4f}`\n"
        f"    - Interpretation: A 1 {meta['unit']} increase in this feature "
        f"**{direction}** the predicted water level by **{abs(value):.4f} meters**."
    )

def generate_region_explanation(metadata: Dict[str, Any]) -> str:
    """
    Composes the full explanation block for a region.
    """
    region_id = metadata['region_id']
    coeffs = metadata.get('coefficients', {})
    intercept = metadata.get('intercept', 0.0)
    
    # Header
    lines = [
        f"## Region: {region_id}",
        f"**Base Water Level (Intercept):** `{intercept:.4f} meters`",
        "",
        "### Feature Drivers:"
    ]
    
    # Sort coefficients by absolute impact (Magnitude) to highlight drivers
    sorted_coeffs = sorted(coeffs.items(), key=lambda item: abs(item[1]), reverse=True)
    
    for feature, value in sorted_coeffs:
        lines.append(interpret_coefficient(feature, value))
        
    lines.append("\n---")
    return "\n".join(lines)

def run_explainability_report():
    """
    Main orchestrator. Reads registry -> Generates Markdown Report.
    """
    logger.info("🧠 Generating Explainability Report...")
    
    registry = load_registry()
    if not registry:
        return

    report_content = [
        "# 🧠 Model Explainability Report (v1.0)",
        f"**Generated:** {os.path.basename(REGISTRY_PATH)}",
        "**Model Type:** Linear Regression (Per-Region)",
        "",
        "This report breaks down the 'why' behind the model predictions by interpreting the linear weights.",
        "---"
    ]
    
    for region_meta in registry:
        report_content.append(generate_region_explanation(region_meta))
        
    # Save Report
    with open(EXPLAINABILITY_REPORT_PATH, 'w') as f:
        f.write("\n".join(report_content))
        
    logger.info(f"✅ Report saved to: {EXPLAINABILITY_REPORT_PATH}")
    
    # Print a sample to console for immediate feedback
    if registry:
        print("\n--- SAMPLE EXPLANATION ---\n")
        print(generate_region_explanation(registry[0]))
        print("\n--------------------------\n")

if __name__ == "__main__":
    run_explainability_report()