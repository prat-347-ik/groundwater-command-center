# Known Issues & Tracked Enhancements

This document tracks technical debt, open investigative hypotheses, and deferred validation items for the Analytics & ML Machine Learning Engine (`service-b-analytics`).

---

## 📌 Tracked Items & Open Hypotheses

### 1. Random Forest Sensitivity & Tree Split Boundaries
- **Status**: Open / Unconfirmed Hypothesis
- **Context**: During initial model sensitivity testing on reduced feature subsets, Random Forest exhibited positive output deltas under increased extraction. Expanding to the full 8-feature schema restored correct directional sensitivity ($\Delta < 0$).
- **Follow-up Action**: Verify whether leaf split boundaries or node sample statistics (`.decision_path()`) caused the step-discontinuity under reduced feature sets on real regional datasets.

### 2. Multi-Model Sign Agreement Validation on Real Feature Store
- **Status**: Pending Historical Ingestion Run
- **Context**: Hydrological directional consistency ($\text{Rainfall} \uparrow \implies \text{Water Level} \uparrow$, $\text{Extraction} \uparrow \implies \text{Water Level} \downarrow$) across Linear Regression, Random Forest, and PyTorch LSTM was verified using seeded synthetic datasets.
- **Follow-up Action**: Re-run the three-model sign-agreement validation suite against historical MongoDB `region_feature_store` records during production `/jobs/promote` executions across non-stationary regions.

### 3. Linear Regression Feature Expansion Metric Baseline
- **Status**: Pending Evaluation
- **Context**: Linear Regression was updated from 5 features to the standardized 8-feature production schema to maintain polymorphic parity with Random Forest and LSTM models.
- **Follow-up Action**: Benchmark MAE and RMSE performance metrics for 8-feature Linear Regression against historical 5-feature baseline metrics during candidate evaluation in `/jobs/promote`.
