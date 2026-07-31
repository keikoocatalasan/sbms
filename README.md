# Argo Subscription Management System

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A production-grade, multi-tenant subscription management platform with FastAPI backend, React dashboard, SQLite/PostgreSQL support, JWT authentication, financial allocation rules, full lifecycle processing, audit trails, and comprehensive reporting.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Mock Data](#mock-data)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Argo is a subscription billing and customer lifecycle management system built for SaaS businesses, digital agencies, and service providers. It handles the complete subscription lifecycle — from trial onboarding through billing, payment collection, plan changes, renewals, and cancellations — with full financial allocation rules and audit compliance.

The system is designed as a **multi-tenant architecture** where all data is scoped by organization, making it suitable for white-label deployments or multi-branch operations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  React 18   │  │  Vite 7     │  │  Recharts / Lucide /    │  │
│  │  TypeScript │  │  Dev Server │  │  React Router DOM       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                         http://localhost:5173                     │
└────────────────────────┬──────────────────────────────────────────┘
                         │ REST API + JWT
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  FastAPI    │  │  SQLAlchemy │  │  Pydantic Schemas       │  │
│  │  Uvicorn    │  │  SQLite/    │  │  JWT Auth (demo mode)   │  │
│  │  Python 3.11│  │  PostgreSQL │  │  Idempotency Keys       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                         http://127.0.0.1:8000                     │
│                         /docs (OpenAPI)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Modules

| Module | Description |
|--------|-------------|
| **Customers** | Full CRUD with unique codes, tax IDs, multiple addresses, archive support |
| **Plans** | Tiered subscription plans with trial days, feature flags, display ordering |
| **Pricing** | Per-plan monthly/yearly pricing with setup fees, effective date ranges |
| **Features** | Plan feature matrices (boolean, numeric, text values) |
| **Subscriptions** | Complete lifecycle: trial → pending → active → past_due → suspended → cancelled/expired |
| **Invoices** | Auto-generated from subscriptions with draft/open/paid/overdue/void states |
| **Payments** | Manual cash, bank transfer, simulated card/wallet with allocation engine |
| **Payment Attempts** | Simulated gateway integration with success/failure/pending states |
| **Notifications** | In-app notification system with read tracking |
| **Activity Logs** | Full audit trail of all entity changes |
| **Reports** | MRR calculation, collected revenue, at-risk analysis |
| **Settings** | Organization-level configuration (currency, grace period, prefixes, etc.) |
| **Maintenance** | Batch due-date processing for subscription renewals |

### Security & Compliance

- **JWT Authentication** with role-based scopes (`subscription:admin`, `subscription:billing`, `subscription:read`, etc.)
- **Idempotency Keys** for safe retry of payment and subscription operations
- **Versioned Commands** for subscription mutations (optimistic locking)
- **Request Correlation IDs** for end-to-end tracing
- **Multi-tenancy** — all data scoped by `organization_id`

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.115+ | Web framework |
| SQLAlchemy | 2.x | ORM |
| Pydantic | 2.x | Validation |
| Uvicorn | — | ASGI server |
| Pytest | — | Testing |
| SQLite | — | Dev database (PostgreSQL ready) |

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18.3+ | UI framework |
| TypeScript | 5.7+ | Type safety |
| Vite | 7.3+ | Build tool |
| React Router DOM | 6.30+ | Routing |
| Recharts | 3.0+ | Charts & dashboards |
| Axios | 1.7+ | HTTP client |
| Lucide React | 0.468+ | Icons |

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm (or pnpm)
- Git

### 1. Clone & Setup

```bash
git clone https://github.com/keikoocatalasan/sbms.git
cd sbms
```

### 2. Backend

```bash
# Create virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\pip.exe install -r backend\requirements.txt

# Copy environment (optional for SQLite dev)
copy backend\.env.example backend\.env

# Start server
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Open Application

- **Dashboard:** http://localhost:5173
- **API Docs:** http://127.0.0.1:8000/docs
- **Health Check:** http://127.0.0.1:8000/health

### Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Administrator | `admin@argo.demo` | `DemoPass123!` |
| Billing Specialist | `billing@argo.demo` | `DemoPass123!` |

---

## Backend Setup

### Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```env
DATABASE_URL=sqlite:///./subscription.db
JWT_SECRET=replace-me-before-deploying
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DEMO_MODE=true
```

For PostgreSQL production:

```env
DATABASE_URL=postgresql+psycopg2://user:pass@localhost/subscription
```

### Database

SQLite is used in development mode. The schema is auto-created on startup via SQLAlchemy `Base.metadata.create_all()`. The `DEMO_MODE=true` flag also seeds three starter plans and sample customers automatically.

### Running Tests

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

---

## Frontend Setup

```bash
cd frontend
npm install        # or pnpm install
npm run dev        # development server
npm run build      # production build
npm run lint       # ESLint
npm test           # Vitest
```

The Vite dev server runs on port 5173 by default. The backend CORS is pre-configured for this origin.

---

## Mock Data

The project includes **comprehensive mock data generators** for demonstration and load testing. These scripts produce realistic, unique records spanning a full year.

### Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `seed_full_year.py` | `backend/scripts/` | **Primary generator** — 2,600+ records (320 customers, 420 subscriptions, 751 invoices, 220 payments, etc.) spanning Sep 2025 – Aug 2026 |
| `generate_mock_data.py` | `backend/scripts/` | Original quick-seed generator (~350 records) |
| `add_missing_plans.py` | `backend/scripts/` | Adds additional plans if demo seed only created 3 |

### Running the Full-Year Dataset

```bash
cd backend
.\.venv\Scripts\python.exe scripts\seed_full_year.py
```

**What it generates:**
- 320 unique customers (individuals + businesses across 80 PH cities)
- 420 subscriptions with realistic lifecycle states
- 751 invoices with 999 line items
- 220 payments with 83 allocations
- 100 payment attempts (succeeded, failed, pending)
- 180 subscription events (audit trail)
- 120 in-app notifications
- 180 activity logs

**Total: ~2,640 records**

---

## API Reference

All endpoints are prefixed with `/api/v1/subscription/`.

### Authentication
```
POST /auth/login          → JWT token
```

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/dashboard/summary` | GET | Metrics, recent subscriptions & payments |
| `/customers` | GET/POST | List (paged) or create customer |
| `/customers/{id}` | GET/PATCH | Detail or update |
| `/customers/{id}/archive` | POST | Archive customer |
| `/plans` | GET/POST | List or create plan |
| `/plans/{id}/prices` | POST | Add price to plan |
| `/plans/{id}/status` | PATCH | Change plan status |
| `/subscriptions` | GET/POST | List or create subscription |
| `/subscriptions/{id}/schedule-cancellation` | POST | Cancel at period end |
| `/subscriptions/{id}/cancel-now` | POST | Immediate cancellation |
| `/subscriptions/{id}/schedule-plan-change` | POST | Upgrade/downgrade |
| `/invoices` | GET/POST | List or create invoice |
| `/invoices/{id}/finalize` | POST | Finalize draft invoice |
| `/invoices/{id}/void` | POST | Void invoice |
| `/payments` | GET/POST | List or record payment |
| `/payment-attempts` | GET/POST | List or create attempt |
| `/payment-attempts/{id}/simulate-success` | POST | Simulate gateway success |
| `/notifications` | GET/POST | In-app notifications |
| `/settings` | GET/PATCH | Organization settings |
| `/reports/mrr` | GET | Monthly recurring revenue |
| `/reports/collected-revenue` | GET | Total collected revenue |
| `/activity-logs` | GET | Full audit trail |
| `/maintenance/process-due` | POST | Batch renewals & overdue |

### Response Format

```json
{
  "data": { ... },
  "meta": { "page": 1, "page_size": 20, "total": 320 },
  "request_id": "uuid"
}
```

---

## Project Structure

```
sbms/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py           # Environment config
│   │   ├── db.py               # SQLAlchemy engine & session
│   │   ├── main.py             # FastAPI app & routers
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   ├── schemas.py          # Pydantic request/response schemas
│   │   ├── security.py         # JWT, Principal, scopes
│   │   ├── services.py         # Business logic & helpers
│   │   ├── seed.py             # Demo seed data
│   │   └── tests/              # Pytest suite
│   ├── scripts/
│   │   ├── seed_full_year.py   # Full-year mock data generator
│   │   ├── generate_mock_data.py
│   │   ├── add_missing_plans.py
│   │   └── README.md
│   ├── requirements.txt
│   ├── .env.example
│   └── subscription.db         # SQLite dev DB (gitignored)
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
├── docs/
├── .gitignore
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

---

## Testing

### Backend
```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

### Frontend
```bash
cd frontend
npm test       # Vitest
npm run lint   # ESLint
npm run build  # TypeScript + Vite build
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, pull requests, and development workflow.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

Built as a demonstration of production-grade subscription billing architecture using FastAPI and React. Payments are intentionally simulated in this local build — no real payment gateway or card data is processed.

---

<p align="center">
  <sub>Made with care by the Argo team.</sub>
</p>
