# 🌊 Groundwater Management Command Center

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Node.js](https://img.shields.io/badge/Node.js-v18+-339933?logo=node.js&logoColor=white)](services/service-a-operations)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](services/service-b-analytics)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-000000?logo=next.js&logoColor=white)](frontend)

A **production-ready, enterprise microservices architecture** designed for real-time groundwater monitoring, predictive analytics, climate ingestion, and scenario simulation across multi-regional water basins.

---

## 🏗️ Architecture Overview

The system consists of **4 decoupled services** communicating over HTTP APIs and structured data pipelines:

```text
                                  +-----------------------+
                                  |   Next.js Frontend    |
                                  |   Command Center      |
                                  |    (Port 3000)        |
                                  +-----------+-----------+
                                              |
                     +------------------------+------------------------+
                     |                        |                        |
                     v                        v                        v
          +--------------------+    +--------------------+    +--------------------+
          |    Service A       |    |    Service B       |    |    Service C       |
          | Operations Gateway |    | Analytics & ML     |    | Climate & Weather  |
          |    (Port 4000)     |    |   Engine (8000)    |    |   Ingestion (8100) |
          +---------+----------+    +---------+----------+    +---------+----------+
                    |                         |                         |
                    +-------------------------+-------------------------+
                                              |
                                              v
                                   +---------------------+
                                   |    MongoDB Atlas    |
                                   |  (Multi-Collection) |
                                   +---------------------+
```

### Microservice Directory Breakdown

```text
groundwater-command-center/
│
├── frontend/                       # Next.js 14 Dashboard UI (React 18, Tailwind CSS, Recharts)
│   ├── src/
│   │   ├── app/                    # App Router pages and navigation
│   │   ├── components/             # Reusable UI widgets (Charts, Maps, Simulation Lab)
│   │   └── lib/                    # API client layer & utility helpers
│   ├── Dockerfile
│   └── package.json
│
├── services/
│   ├── service-a-operations/       # Node.js / Express Operational API & Gateway
│   │   ├── src/
│   │   │   ├── config/             # MongoDB database connection
│   │   │   ├── models/             # Mongoose schemas (Region, Well, Reading, Extraction, etc.)
│   │   │   ├── modules/            # Domain controllers, services, and route definitions
│   │   │   ├── app.js              # Express application configuration & proxy routes
│   │   │   └── server.js           # Server bootstrap
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   ├── service-b-analytics/        # Python / FastAPI Analytics & Machine Learning Engine
│   │   ├── src/
│   │   │   ├── extract/            # Data extraction loaders from MongoDB
│   │   │   ├── transform/          # Time-series feature engineering & lag features
│   │   │   ├── modelling/          # Linear Regression, Random Forest & LSTM polymorphic models
│   │   │   ├── inference/          # 12-month predictive forecasting engine & model registry
│   │   │   └── jobs/               # Daily summary, training, and ETL execution routines
│   │   ├── app.py                  # FastAPI background worker & job endpoints
│   │   ├── main.py                 # CLI entry point for scheduled tasks
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── service-c-climate/          # Python / FastAPI Climate & Satellite Ingestion Service
│       ├── src/
│       │   ├── api/                # Endpoints for rainfall, weather, and satellite data
│       │   ├── config/             # Database connection & index provisioning
│       │   └── main.py             # FastAPI entry point
│       ├── Dockerfile
│       └── requirements.txt
│
└── docs/                           # Architecture, ports, and API specifications
```

---

## ⚡ Quick Start with Docker

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24.0+)
* [Git](https://git-scm.com/)

### 1. Clone & Configure
```bash
git clone https://github.com/prat-347-ik/groundwater-command-center.git
cd groundwater-command-center
cp .env.example .env
```

### 2. Build & Launch
```bash
docker compose up --build -d
```

### 3. Verify Deployment
Open your browser and navigate to:
* **Frontend Command Center:** [http://localhost:3000](http://localhost:3000)
* **Service A Health Check:** [http://localhost:4000/health](http://localhost:4000/health)
* **Service B Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
* **Service C Health Check:** [http://localhost:8100/health](http://localhost:8100/health)

---

## 💻 Manual Local Development

If you prefer running services directly on your host machine without Docker:

### 1. Start MongoDB
Ensure MongoDB is running locally on port `27017` or use a MongoDB Atlas connection string.

### 2. Service A (Operations Layer)
```bash
cd services/service-a-operations
npm install
npm run dev
# Starts on http://localhost:4000
```

### 3. Service B (Analytics Engine)
```bash
cd services/service-b-analytics
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Service C (Climate Layer)
```bash
cd services/service-c-climate
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8100 --reload
```

### 5. Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
# Starts on http://localhost:3000
```

---

## ⚙️ Environment Variables

### Root `.env` (Used by Docker Compose)
```env
NODE_ENV=production
MONGO_ATLAS_URI=mongodb://localhost:27017/groundwater_db
DB_NAME_OPS=groundwater_db
DB_NAME_ANALYTICS=groundwater_db
DB_NAME_CLIMATE=groundwater_db

# Host address for remote access (change from localhost if needed)
HOST_IP=localhost
ALLOWED_ORIGINS=http://localhost:3000
```

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL_A=http://localhost:4000
NEXT_PUBLIC_API_URL_B=http://localhost:8000
NEXT_PUBLIC_API_URL_C=http://localhost:8100
```

---

## 📡 Remote & LAN Access

To allow other devices or team members on your local network (LAN) to access the dashboard:

1. **Find your Host LAN IP** (e.g., `192.168.1.50` on Windows using `ipconfig` or Linux/macOS using `ifconfig`).
2. **Update the root `.env`:**
   ```env
   HOST_IP=192.168.1.50
   ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.50:3000
   ```
3. **Ensure Firewall Inbound Rules** permit ports `3000`, `4000`, `8000`, and `8100`.
4. **Rebuild & Start Containers:**
   ```bash
   docker compose up --build -d
   ```
5. **Access from any device on the LAN:**
   ```text
   http://192.168.1.50:3000
   ```

---

## 🔌 API Reference

### Service A — Operations & Gateway (`http://localhost:4000/api/v1`)
* `GET /health` — Service health & gateway status
* `GET /stats/counts` — System-wide totals (regions, wells, readings)
* `GET /regions` — Retrieve all monitored regional zones
* `POST /regions` — Register a new geographical region
* `GET /wells` — Query wells with region filtering
* `POST /water-readings` — Log single or batch water level readings (mbgl)
* `GET /forecasts/:regionId` — Fetch 12-month ML forecast points
* `POST /extraction/logs` — Record regional water extraction events
* `GET /extraction/compliance/:regionId` — Retrieve regional threshold compliance metrics
* `POST /pipeline/trigger` — Proxy trigger to execute Service B analytics pipeline

### Service B — Analytics & ML Engine (`http://localhost:8000`)
* `GET /health` — Analytics engine status & active model metadata
* `POST /jobs/daily-summary` — Trigger asynchronous ETL aggregation
* `POST /jobs/train` — Train Random Forest, Linear Regression, & LSTM models on feature store
* `POST /jobs/promote` — Evaluate candidate model metrics (MAE/RMSE) and promote the best-performing model to production registry
* `POST /jobs/forecast` — Run batch inference and write 12-month projections to database
* `POST /jobs/pipeline` — Master orchestrator: runs ETL $\to$ Train $\to$ Promote $\to$ Forecast

### Service C — Climate Intelligence (`http://localhost:8100`)
* `GET /health` — Climate service health check
* `GET /api/v1/rainfall/:regionId` — Historical and recent precipitation records
* `POST /api/v1/rainfall/ingest/csv` — Batch ingest rainfall CSV records
* `GET /api/v1/weather/:regionId` — Fetch temperature, humidity, and atmospheric metrics
* `GET /api/v1/satellite/:regionId` — Fetch soil moisture and satellite telemetry

---

## 🧪 Machine Learning & Simulation Engine

### Feature Engineering Pipeline
The platform transforms raw water level logs and weather events into predictive feature representations:
- **Temporal Lags:** $t-1, t-7, t-30$ day water depth variations.
- **Rolling Aggregations:** 7-day and 30-day moving averages and standard deviations.
- **Climate Interaction Features:** Cumulative rainfall deficit indices and seasonal precipitation spikes.

### Model Registry & Polymorphism
Service B supports pluggable algorithms via `BaseGroundwaterModel`:
- **Linear Regression**: Fast baseline model for linear trend estimation.
- **Random Forest**: Non-linear ensemble model capturing complex feature interactions.
- **PyTorch LSTM**: Deep recurrent neural network for long-term temporal dependencies.

### Interactive Simulation Sandbox
The Simulation Lab allows domain experts to adjust operational variables and view projected aquifer behavior:
$$\text{Projected Depth}_{t+k} = f(\text{Historical Baseline}, \Delta\text{Extraction Rate}, \Delta\text{Precipitation})$$
- **High Stress Scenario:** Simulates severe drought combined with elevated extraction.
- **Conservation Scenario:** Models the impact of mandated extraction reduction targets.

---

## 📌 Known Issues & Tracked Items

See [docs/known-issues.md](docs/known-issues.md) for tracked hypotheses, multi-model sign-agreement validation items, and feature set performance benchmarks.

---

## 👨‍💻 Author & License

Developed with passion by **Pratik**  
*Engineering Student & Full-Stack / ML Developer*

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.