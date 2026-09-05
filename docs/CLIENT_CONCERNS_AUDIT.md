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
| Public landing page | Implemented and loads `/public/plans` | `/` redirects to `/login`; `/public/plans` returns 404 | Local changes are not deployed |
| Subscriber dashboard | Implemented with focused navigation, subscription, invoices, notifications, profile, Usage Overview, and Quick Actions | Not present in the deployed bundle | Local UI is ahead of production |
| Super Admin experience | Implemented at `/super-admin/*` with platform authorization, organization counts, customer counts, active sessions, recent activity, and system summary | Not present in the deployed bundle | Local implementation is partial relative to the reference; uptime and backup telemetry are not stored |
| Admin modules | Dashboard, customers, plans, subscriptions, payments, invoices, reports, notifications, and Settings are implemented | Production serves the older release | Local API and UI tests pass |
| Annual pricing | Toggle and annual price display are implemented; five local plans imply 15% annual savings | Not deployed | Three local plans have no annual price; stored discount fields are zero |
| Annual-only features | API and UI support interval-specific features | Not deployed | Current local catalog has no annual-only feature differences |
| Settings | Billing rules, numbering, notifications, maintenance, currency, and timezone are configurable | Not deployed | Catalog pricing/features are still managed in Plans, not Settings |
| Role assignment | Backend and protected UI capability exist; sidebar entry is hidden for now | Not deployed | Matches the request to defer visible role assignment |
| Login | Password show/hide and Return to landing page are implemented and browser-verified locally | Not deployed | Production still has the older login form |

## Verification evidence

- Backend: 15 tests pass.
- Frontend: 4 tests pass.
- ESLint passes.
- Vite production build passes.
- Local `/ready` returns HTTP 200 with database available.
- Local landing page renders and receives catalog data from the API.
- Local password control changes the input between `password` and `text`.
- Local login return link navigates to `/`.
- Vercel production is Ready at `sbms.vercel.app`, deployed from commit `4707d03`.
- Render production is Live at `sbms-api.onrender.com`, deployed from commit `4707d03`.
- Live API `/health` and `/ready` return HTTP 200.
- Live API `/api/v1/subscription/public/plans` returns HTTP 404.
- Production credentials were not entered or exposed, so live authentication remains unverified.

## Recommended next steps

1. Review and approve the current local working tree as the intended release source.
2. Choose exact monthly and annual discount percentages and identify annual-only feature differences.
3. Decide whether catalog editing belongs in Plans or a new Catalog section within Settings.
4. Decide which Super Admin metrics are required; add a real telemetry/backup integration if uptime and backups must be shown.
5. Configure the authorized production Super Admin email in Render.
6. Deploy the approved source to Render and Vercel.
7. Recheck API contract parity, public landing page, password controls, and each role's navigation.
8. For credential verification, have an authorized user enter production credentials directly in the live browser form; never place passwords in this report or chat.
