# Groundwater Prediction Command Center

The **Groundwater Prediction Command Center** is an advanced hydrological monitoring and forecasting ecosystem. It is designed to bridge the gap between raw data collection and predictive foresight by utilizing a strictly decoupled microservice architecture. The system integrates real-time operational logging with machine learning-driven analytics and satellite-fetched climate data to provide a comprehensive tool for water resource management.

---

## 🏗 System Architecture

The project is built on a three-tier microservice architecture to ensure high availability and prevent resource competition between operational tasks and heavy analytical processing:

* **Service A — Operational Layer (Node.js/Express):** Acts as the system of record, handling all CRUD operations, manual data entry, and CSV ingestions.
* **Service B — Analytics Engine (Python/FastAPI):** The "Brain" of the system, running ETL pipelines and ML models (LSTM/Random Forest) to generate 12-month water level forecasts.
* **Service C — Climate Layer (Python/FastAPI):** A dedicated service for fetching satellite data and 3rd-party climate APIs to provide environmental context to the models.
* **Frontend Dashboard (Next.js/React):** A centralized command center providing regional monitoring, simulation labs, and compliance tracking.



---

## 🚀 Key Features

* **Decoupled Processing:** Uses a "Single Source of Truth" port configuration (8100 for Ops, 5001/5002 for Analytics/Climate) to eliminate network socket competition.
* **Machine Learning Forecasts:** Implements Random Forest and LSTM architectures to predict regional water depletion trends.
* 
**Interactive Simulation Lab:** Allows users to model "what-if" scenarios by adjusting extraction rates to visualize future water level impacts.


* **Satellite Data Integration:** Automatically ingests external climate variables to enhance predictive accuracy.
* 
**Compliance Monitoring:** Real-time tracking of extraction logs against regional safety thresholds.



---

## 🛠 Tech Stack

* 
**Frontend:** Next.js 15, React 19, Tailwind CSS, Lucide React, Recharts.


* **Backend:** Node.js, Express.js (Service A); Python 3.10+, FastAPI (Service B & C).
* **Database:** MongoDB (OLTP for operations, OLAP for analytics).
* **ML/DS:** PyTorch (LSTM), Scikit-learn (Random Forest), Pandas, NumPy.
* 
**DevOps:** Docker, Docker Compose, Nginx.



---

## 🚦 Getting Started

### Prerequisites

* Docker and Docker Compose
* Node.js 20.x
* Python 3.9+

### Installation & Setup

1. **Clone the Repository:**
```bash
git clone https://github.com/prat-347-ik/groundwater-command-center/tree/feature/random-forest
cd groundwater-command-center

```


2. **Environment Configuration:**
Ensure MongoDB is running locally or update the connection strings in the service configuration files.
3. **Launch with Docker:**
```bash
docker-compose up --build

```

### **Root / Global Configuration**

```env
# --- MongoDB Configuration ---
# Single source of truth for the shared database
[cite_start]MONGO_URI=mongodb://localhost:27017/groundwater_db [cite: 3]

```

### **Frontend (Next.js)**

*File location: `/frontend/.env.local*`

```env
# URL for the Operational API (Service A)
[cite_start]NEXT_PUBLIC_API_URL=http://localhost:8100/api/v1 [cite: 3]

# URL for the Analytics Engine (Service B)
[cite_start]NEXT_PUBLIC_ANALYTICS_URL=http://localhost:5001 [cite: 3]

```

### **Service A: Operations (Node.js)**

*File location: `/services/service-a-operations/.env*`

```env
# Network configuration
[cite_start]PORT=8100 [cite: 3]
[cite_start]NODE_ENV=development [cite: 3]

# Database connection
[cite_start]MONGO_URI=mongodb://localhost:27017/groundwater_db [cite: 3]

```

### **Service B: Analytics Engine (Python)**

*File location: `/services/service-b-analytics/.env*`

```env
# API and Job configuration
[cite_start]SERVICE_B_PORT=5001 [cite: 3]
[cite_start]MODEL_PATH=./models/v1 [cite: 3]
[cite_start]TRAINING_ENABLED=true [cite: 3]

# Database and Adapter links
[cite_start]MONGO_URI=mongodb://localhost:27017/groundwater_db [cite: 3]
[cite_start]SERVICE_A_URL=http://localhost:8100/api/v1 [cite: 3]
[cite_start]SERVICE_C_URL=http://localhost:5002 [cite: 3]

```

### **Service C: Climate Layer (Python)**

*File location: `/services/service-c-climate/.env*`

```env
# Integration settings
[cite_start]SERVICE_C_PORT=5002 [cite: 3]

# External API Keys (Required for satellite data fetching)(Optional)
[cite_start]SATELLITE_API_KEY=your_satellite_provider_key_here [cite: 3]
[cite_start]WEATHER_API_URL=https://api.weather_provider.com/v3 [cite: 3]

# Local DB for climate caching
[cite_start]MONGO_URI=mongodb://localhost:27017/groundwater_db [cite: 3]

```


4. **Access the Services:**
* **Frontend Dashboard:** `http://localhost:3000`
* **Operational API (Service A):** `http://localhost:4000`
* **Analytics API (Service B):** `http://localhost:8000`
* **Climate API (Service C):** `http://localhost:8100`



---

## 📁 Project Structure

```text
├── docs/architecture/       # System design and port configurations
├── frontend/                # Next.js dashboard and simulation UI
├── services/
│   ├── service-a-operations # Node.js operational API
│   ├── service-b-analytics  # Python ML and ETL engine
│   └── service-c-climate    # Satellite and climate data fetchers
└── docker-compose.yml       # Orchestration for all microservices

```

---

## 👨‍💻 Author

**Pratik**

* 3rd Year Engineering Student
* Focus: Machine Learning, Web Development, and DevOps

---

## 📄 License

This project is licensed under the MIT License.