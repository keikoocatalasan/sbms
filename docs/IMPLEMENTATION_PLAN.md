# Build Plan and Delivered Baseline

## Delivery sequence

1. Establish a secure, organization-scoped foundation: FastAPI, SQLAlchemy, typed validation, request IDs, strict CORS, JWT demo adapter, and a database configuration that uses SQLite locally and PostgreSQL in deployment.
2. Model the complete subscription domain: customers and addresses; plans, prices, and features; subscriptions and events; invoices and immutable line items; payment attempts, payments, allocations; notifications, settings, idempotency keys, and activity logs.
3. Implement services before route handlers. Every lookup receives the authenticated organization ID; financial amounts are integer minor units; external tenant/user references are deliberately loose IDs; no card data is accepted or stored.
4. Implement lifecycle commands: customer archival; plan activation; price-version selection; trial and no-trial subscription creation; scheduled cancellation; immediate cancellation; cancellation revocation; scheduled plan changes; payment activation; and catch-up due processing.
5. Implement billing and collection rules: invoices derive totals from line items, allocation totals from completed payments, and a payment cannot over-allocate or cross customer/currency boundaries. Idempotency keys protect each duplicate-sensitive command.
6. Expose tenant-scoped REST resources, report aggregates, activity history, health/readiness, OpenAPI, and the demo-only login endpoint. Use structured errors and return a request ID on each response.
7. Build the responsive React shell from the supplied visual references: dark application navigation, dashboard metric cards, tables, reports, notifications, settings, and authenticated session flow. Keep financial calculations in the backend.
8. Validate the system with lifecycle/idempotency tests, unauthenticated-error tests, Python compilation, API startup/OpenAPI smoke checks, and a production Vite build.

## Delivered scope

The repository contains the implemented standalone demonstration baseline described above. It is ready for a PostgreSQL/Alembic migration hardening pass before a deployed Argo integration. The remaining integration gates are intentionally external to this local project: real Argo authentication middleware and organization table binding, a PostgreSQL 14 migration revision, approved production CORS origins/secrets, an actual payment gateway, deployment configuration, and legal/BIR invoice certification.

## Runbook

Backend:

```powershell
cd backend
<python> -m pip install -r requirements.txt
<python> -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
pnpm install
pnpm run dev
```

Use `admin@argo.demo` / `DemoPass123!`. The backend seeds non-production fake plans and customers only when an empty demo database is started.
