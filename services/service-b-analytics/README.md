# 🧠 Service B - Groundwater Analytics Engine

This microservice provides the analytical intelligence for the Groundwater Command Center. It handles feature engineering, multi-model candidate training, automated gating/promotion, and polymorphic scenario forecasts.

---

## 📑 Table of Contents
- [Architecture & Registry Factory](#-architecture--registry-factory)
- [Promotion Gating Logic](#-promotion-gating-logic)
- [Endpoints & Jobs](#-endpoints--jobs)
- [Local Development & Tests](#-local-development--tests)

---

## 🏗 Architecture & Registry Factory

The analytics engine defines a unified model interface contract (`BaseGroundwaterModel`) that abstracts model interactions. This allows different model architectures (**Linear Regression**, **Random Forest**, **LSTM**) to be wired interchangeably without modifying downstream API or forecasting paths.

### Priority Resolution Order
When resolving the active model for a region, `registry.py` strictly respects the following priority:
1. **Explicit Override (`requested_type`)**: Direct API parameter override (ad-hoc slider simulation).
2. **Authoritative Active Entry**: The model promoted per-region by the gated pipeline in `model_registry.json`.
3. **Artifact Path Inference**: Inferred from artifact suffix (`.pkl` vs `.pth`) if specified in the registry.
4. **Environment Fallback (`ACTIVE_MODEL`)**: Debug override when no region entry exists, emitting a loud warning log.
5. **Default Fallback**: Defaults to `random-forest`.

---

## 🛡 Promotion Gating Logic

When `/jobs/train` is triggered, the engine trains candidate architectures on historical region data. The gating pipeline in `update_registry.py` executes the following evaluation:

$$\text{Candidate MAE} < \text{Baseline Persistence MAE}$$
$$\text{Candidate MAE} \le \text{Current Active Model MAE}$$

If both conditions pass, the winning candidate is set to `status: "active"`, and prior models are marked `status: "archived"`.

---

## 🔌 Endpoints & Jobs

### ML Pipeline Tasks
- **POST `/jobs/train`**: Retrain region candidate models. Supports payload filtering:
  ```json
  { "model_type": "all" } // "all" | "random-forest" | "linear-regression"
  ```
- **POST `/jobs/promote`**: Run the gating pipeline to promote candidates.
- **POST `/jobs/forecast`**: Run batch predictions on all active models.

### Inference & Simulations
- **POST `/api/v1/forecasts/simulate`**: What-If single-step hydrological simulation.
- **POST `/api/v1/forecasts/generate`**: 7-day scheduled scenario forecasting.
- **GET `/api/v1/forecasts/importance/{region_id}`**: List feature importances (drivers).

---

## 🧪 Local Development & Tests

Run all modelling, registry, and pipeline tests:
```bash
pytest tests/ -v
```
