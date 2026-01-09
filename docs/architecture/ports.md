# 🌐 System Port Configuration

This document serves as the **Single Source of Truth** for network ports used in the Groundwater Prediction Command Center.

> **Status:** Locked 🔒
> **Last Updated:** 02/01/2026

---

## 🟦 Service A — Operational Layer (OLTP)
**Type:** REST API (Node.js + Express)  
**Port:** `4000`  
**Purpose:** System of record. Handles all CRUD operations, CSV ingestion, and raw data retrieval.  
**Access:**
- Local: `http://localhost:4000`
- API Root: `http://localhost:4000/api/v1`

## 🟩 Service B — Analytics & Feature Pipeline (OLAP)
**Type:** Batch / Job Runner (Python)  
**Port:** `N/A` (Initially)  
**Purpose:** Offline processing. Runs deterministic pipelines (ETL) to aggregate data from Service A into Analytics collections.  
**Execution:**
- Triggered via CLI or Scheduler (e.g., `python main.py daily_summary`)
- Direct MongoDB connection (No HTTP listener)

> **🔮 Future Reservation:**
> If a Prediction API (`/forecast`) is exposed later, use Port **5001**.

## 🟪 Frontend — Command Center Dashboard
**Type:** SPA (React + Vite)  
**Port:** `5173`  
**Purpose:** User interface for visualization and decision support.  
**Access:**
- Local: `http://localhost:5173`

## 🟨 Service C — Climate / Environmental (Future)
**Type:** External Integration Service (Python + FastAPI)  
**Port:** `5002` (Reserved)  
**Purpose:** Dedicated service for fetching satellite data and 3rd party climate APIs.

---

## 🧾 Summary Table

| Component | Port | Protocol | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | `3000` | HTTP | ✅ Active | Default Vite Server |
| **Service A** | `8100` | HTTP | ✅ Active | Operational API |
| **Service B** | — | — | ✅ Active | Batch Job (No Port) |
| **Service B API**| `5001` | HTTP | 🔒 Reserved | For future ML inference |
| **Service C** | `8200` | HTTP | 🔒 Reserved | For future Climate service |
| **MongoDB** | `27017` | TCP | ✅ Active | Local Development |

---

## 🧠 Why this architecture?
1.  **Decoupling:** Analytics (Service B) is strictly a background process. It does not compete for network sockets or HTTP threads with the Operational API (Service A).
2.  **Standards:** `4000` and `5000+` are standard conventions for Node and Python backends respectively, reducing developer cognitive load.
3.  **Conflict Prevention:** Explicit reservations for future services (Service C) prevent "port collision" refactoring later.