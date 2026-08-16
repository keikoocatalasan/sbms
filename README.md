# Argo Subscription Management System

Argo is a subscription management application with a FastAPI backend, React/Vite frontend, SQLAlchemy persistence, JWT authentication, billing lifecycle operations, audit logs, and reporting.

## Architecture

- `backend/`: FastAPI API, SQLAlchemy models, business services, and tests.
- `frontend/`: React/Vite dashboard and authentication UI.
- PostgreSQL (Supabase in production) or SQLite for local development.

The frontend reads and writes data only through the API. The API reads and writes the configured SQL database. Startup does not seed sample customers, plans, subscriptions, invoices, payments, or notifications.

## Live account setup

Open the sign-up form and create an account. The first account in the configured organization receives administrator scopes. Later accounts receive read-only access until an administrator provisions additional scopes.

## Quick start

### Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://127.0.0.1:8000`; OpenAPI is at `/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The Vite app runs at `http://localhost:5173`. Set `VITE_API_URL` when the API is not on the local default.

## Environment

For local SQLite development:

```dotenv
DATABASE_URL=sqlite:///./subscription.db
ORGANIZATION_ID=00000000-0000-0000-0000-000000000001
ORGANIZATION_NAME=Argo Subscription Management
JWT_SECRET=replace-with-a-long-random-secret
FRONTEND_ORIGIN=http://localhost:5173
```

For production, use the Supabase transaction pooler URL in `DATABASE_URL` and the session pooler URL in `DIRECT_URL` for migrations/administration. Keep JWT secrets and database credentials in the hosting provider's secret environment variables; never commit them.

## API reference

All endpoints are prefixed with `/api/v1/subscription/`.

### Authentication

```text
POST /auth/signup         Create a live account and return a JWT
POST /auth/login          Authenticate a live account and return a JWT
```

### Core resources

| Endpoint | Methods | Purpose |
| --- | --- | --- |
| `/dashboard/summary` | GET | Dashboard metrics and recent activity |
| `/customers` | GET, POST | List or create customers |
| `/customers/{id}` | GET, PATCH | View or update a customer |
| `/plans` | GET, POST | List or create plans |
| `/plans/{id}/prices` | POST | Add a plan price |
| `/subscriptions` | GET, POST | List or create subscriptions |
| `/subscriptions/{id}/schedule-cancellation` | POST | Cancel at period end |
| `/subscriptions/{id}/cancel-now` | POST | Cancel immediately |
| `/subscriptions/{id}/schedule-plan-change` | POST | Schedule an upgrade/downgrade |
| `/invoices` | GET, POST | List or create invoices |
| `/payments` | GET, POST | List or record payments |
| `/payments/{id}/allocate` | POST | Apply an existing account credit to an invoice and synchronize its subscription |
| `/payments/{id}/void` | POST | Void a fully unallocated payment (administrator only) |
| `/notifications` | GET, POST | List or create notifications |
| `/settings` | GET, PATCH | Read or update organization settings |
| `/reports/mrr` | GET | Monthly recurring revenue |
| `/reports/collected-revenue` | GET | Collected revenue |
| `/activity-logs` | GET | Audit trail |
| `/maintenance/process-due` | POST | Process due renewals and overdue records |

## Testing

```powershell
\.venv\Scripts\python.exe -m pytest -q backend\tests
cd frontend
npm run lint
npm test -- --run
npm run build
```

Payment records are persisted in the database. A real payment gateway still needs to be connected before accepting real card payments.

## License

MIT
