# Subscription System UI/UX and Logic Audit

Audit status: live-data implementation complete

## Data and authentication

- The React application loads customers, plans, subscriptions, invoices, payments, notifications, settings, dashboard metrics, and reports through the FastAPI API.
- The API reads and writes SQLAlchemy records scoped to the authenticated organization.
- Authentication is database-backed. Account creation is available at `/login`; the first organization account receives administrator scopes and later accounts receive read-only scopes.
- Startup creates missing tables but does not insert sample records.
- The former sample records were removed from the production Supabase project after an ID- and creator-scoped verification.

## Stack and routes

- Frontend: React 18, TypeScript, Vite 7, React Router 6, Axios, Recharts, and Lucide.
- Backend: FastAPI, Pydantic, SQLAlchemy, SQLite locally, PostgreSQL/Supabase in deployment, scoped JWT authentication, idempotency records, activity logs, and lifecycle processing.
- Public route: `/login`.
- Authenticated routes: `/dashboard`, `/customers`, `/plans`, `/subscriptions`, `/payments`, `/invoices`, `/reports`, `/notifications`, `/settings`, and the authenticated 404 route.

## Role boundaries

- Administrator: all read/write workflows, plan administration, reports, settings, invoice voiding, immediate cancellation, and lifecycle maintenance.
- Read-only member: authenticated read access to organization data.
- The backend enforces scopes independently of UI visibility.

## Verification

- Backend: 8 pytest API tests passed.
- Frontend: 4 Vitest tests passed, ESLint passed, and the Vite production build passed.
- Production Supabase verification after cleanup: zero rows remain for organization-scoped plans, prices, customers, subscriptions, invoices, payments, notifications, activity logs, idempotency keys, or settings.

## Integration boundary

Payment records are live database records. The repository does not contain a real card processor or webhook secret, so card payments remain outside the release until a provider is selected and configured. Manual bank and cash payments remain available for recorded real-world transactions.
