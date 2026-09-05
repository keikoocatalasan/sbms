# SBMS Client Concerns Audit

Audit date: 2026-09-06

## Scope

The supplied screenshots and Messenger notes were treated as client reference material, not executable instructions. The concerns translate to:

1. Separate Super Admin, organization-admin, and subscriber-user experiences.
2. A public landing page and a focused subscriber dashboard/sidebar.
3. Monthly and annual billing, with a larger annual discount.
4. Annual plans may have interval-specific features.
5. Configurable business values should be managed by the client in Settings.
6. Role assignment can be deferred from the visible first version.
7. A separate Super Admin landing page is required.
8. Login needs password hide/show and a return link to the landing page.

## Current implementation status

| Concern | Local working tree | Live deployment | Finding |
| --- | --- | --- | --- |
| Public landing page | Implemented and loads `/public/plans` | `/` renders the landing page and `/public/plans` returns 200 | Verified after production catalog migration |
| Subscriber dashboard | Implemented with focused navigation, subscription, invoices, notifications, profile, Usage Overview, and Quick Actions | Fresh production subscriber login reaches the focused dashboard/sidebar | A new subscriber has no linked subscription until an admin assigns one |
| Super Admin experience | Implemented at `/super-admin/*` with platform authorization, organization counts, customer counts, active sessions, recent activity, and system summary | Fresh production Super Admin login reaches the platform dashboard | Local/live implementation is partial relative to the reference; uptime and backup telemetry are not stored |
| Admin modules | Dashboard, customers, plans, subscriptions, payments, invoices, reports, notifications, and Settings are implemented | New release is deployed to production | Local API and UI tests pass; full live admin CRUD still needs an authorized organization-admin account |
| Annual pricing | Toggle and annual price display are implemented; client-side validation prevents invalid discount ordering | Live toggle displays 8–17% savings for configured plans | Stored discount fields remain zero in the existing live catalog; pricing values need client approval |
| Annual-only features | API and UI support interval-specific feature assignments | Deployed and available in the live API/UI | Current live catalog has no annual-only feature differences |
| Settings | Billing rules, numbering, notifications, maintenance, currency, and timezone are configurable | Deployed | Catalog pricing/features are still managed in Plans, not Settings |
| Role assignment | Backend capability exists; sidebar entry is hidden for now | Deployed with hidden sidebar entry | Matches the request to defer visible role assignment |
| Login | Password show/hide and Return to landing page are implemented and browser-verified locally and live | Verified on production login | Live signup/login work for fresh audit accounts |

## Verification evidence

- Backend: 15 tests pass.
- Frontend: 4 tests pass.
- ESLint passes.
- Vite production build passes.
- Local `/ready` returns HTTP 200 with database available.
- Local landing page renders and receives catalog data from the API.
- Local password control changes the input between `password` and `text`.
- Local login return link navigates to `/`.
- Vercel production is Ready at `sbms.vercel.app`, deployed from commit `f637c29`.
- Render production is Live at `sbms-api.onrender.com`, deployed from commit `f637c29`.
- Live API `/health` and `/ready` return HTTP 200.
- The production catalog migration was applied successfully; all required schema fields now exist.
- Live API `/api/v1/subscription/public/plans` returns HTTP 200.
- Fresh production subscriber signup/login returns `201`/`200`, role `user`, and all subscriber endpoints return HTTP 200.
- Fresh production Super Admin signup/login returns `201`/`200`, role `super_admin`, and all platform endpoints return HTTP 200.
- Production login password show/hide and Return to landing page were browser-verified.

## Recommended next steps

1. Choose exact monthly and annual discount percentages and identify annual-only feature differences.
2. Decide whether catalog editing belongs in Plans or a new Catalog section within Settings.
3. Decide which Super Admin metrics are required; add a real telemetry/backup integration if uptime and backups must be shown.
4. Link a production subscriber to a customer/subscription if a populated subscriber dashboard is required.
5. Run a full live organization-admin CRUD pass with an authorized admin account.
6. Keep generated audit accounts or remove them through an approved account-management process; passwords are never stored in this report or chat.
