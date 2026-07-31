# Subscription System UI/UX and Logic Audit

Audit date: 2026-07-30  
Project: Argo Subscription Management System  
Local UI: `http://127.0.0.1:5173`  
Local API: `http://127.0.0.1:8000`

## Scope and assumptions

- The repository did not contain filled-in task metadata, so the stack and startup procedure were detected from the source and package files.
- The supplied PDF/design package was treated as the visual reference. The existing dark navigation shell, page hierarchy, colors, cards, tables, charts, forms, and responsive behavior were retained and completed rather than replaced with an unrelated design.
- The application is a local demonstration using simulated/manual payments. No external payment processor credentials were present.
- No feature was declared out of scope. Changes were kept inside this repository and no commit was created.
- Browser verification used the real rendered application and API. Test records created during the audit were removed by resetting and reseeding the local demo database before handoff.

## Architecture and route inventory

### Stack

- Frontend: React 18, TypeScript, Vite 7, React Router 6, Axios, Recharts, Lucide icons.
- Frontend state: authenticated session plus a centralized `AppDataProvider` that fetches customers, plans, subscriptions, invoices, payments, notifications, settings, dashboard metrics, and admin MRR data.
- Backend: FastAPI, Pydantic, SQLAlchemy, SQLite in local development, JWT-style demo bearer tokens, scoped dependencies, idempotency records, activity logs, and lifecycle processing.
- Tests: Pytest/TestClient for API behavior; Vitest, jsdom, and Testing Library for reusable UI behavior.

### Routes

| Route | Access | Purpose |
|---|---|---|
| `/login` | Public | Demo authentication and validation |
| `/dashboard` | Admin, billing | Live operational summary |
| `/customers` | Admin, billing | Customer search, filters, profiles, create/edit/archive |
| `/plans` | Admin, billing read-only | Plan comparison and plan administration |
| `/subscriptions` | Admin, billing | Trial, renewal, plan-change, and cancellation workflows |
| `/payments` | Admin, billing | Payment recording, invoice allocation, and CSV export |
| `/invoices` | Admin, billing | Draft, finalize, view/download, and admin void workflows |
| `/reports` | Admin only | Revenue, MRR, plan, and customer reporting |
| `/notifications` | Admin, billing | Targeted/account notices, preview, and read state |
| `/settings` | Admin only | Persisted billing, numbering, and lifecycle settings |
| `*` | Authenticated users | Explicit 404 page with a return-to-dashboard link |

### Roles and permissions

- Administrator: all read/write workflows, plan administration, reports, settings, invoice voiding, immediate cancellation, and lifecycle maintenance.
- Billing specialist: customers, subscriptions, payments, invoices, and notifications; can read plans but cannot create/edit/archive them; cannot navigate to or directly open reports/settings.
- Guest: login only. Protected routes redirect to login.
- The backend also enforces scopes, so hiding a control is not the only permission boundary.

Demo accounts:

- `admin@argo.demo` / `DemoPass123!`
- `billing@argo.demo` / `DemoPass123!`

## Initial interactive-element inventory

The status in this section records the first browser pass before repair. “Failed” includes controls that appeared to work visually but did not update real backend-driven state.

### Login

| Element | Expected | Initial result |
|---|---|---|
| Email/password fields | Accept credentials with browser validation | Passed |
| Sign in | Show errors for invalid credentials and enter the app for valid credentials | Failed initially: valid sign-in had previously produced “Unable to sign in”; later role/session state was incomplete |
| Demo-account help | Identify available roles | Failed: only the administrator path was documented clearly |

### Global shell

| Element | Expected | Initial result |
|---|---|---|
| Brand/logo | Return to dashboard | Failed: not a link |
| Sidebar route links | Open the correct page and show active state | Passed for navigation, failed for role visibility |
| Sidebar collapse button | Collapse and expand with accessible state | Partially passed: desktop-only behavior and weak accessible naming |
| Mobile menu/backdrop | Open/close navigation without layout overflow | Failed/incomplete |
| Header notification bell | Open notifications and show unread count | Failed: decorative/non-clickable |
| Profile menu/sign out | Open/close and end the session | Failed/incomplete profile menu; sign out worked |
| Icon buttons | Have hover/focus behavior and accessible names | Failed on several table/card actions |

### Dashboard

| Element | Expected | Initial result |
|---|---|---|
| Metric cards | Reflect API data | Failed: static sample values |
| Revenue-period select | Change the chart range | Failed: label changed without real data behavior |
| Revenue/status charts | Reflect payments/subscriptions | Failed: hardcoded series |
| Recent-table “View all” links | Navigate to full lists | Failed/inert in the report/dashboard implementation |
| New subscription | Open a working dynamic form | Partially passed; resulting list remained static |

### Customers

| Element | Expected | Initial result |
|---|---|---|
| Search | Filter matching customer data | Passed against sample rows |
| Status filter | Filter status | Passed |
| Plan filter | Filter plan independently | Failed: “All Plans” opened/changed the status filter |
| Pagination | Change the visible data page | Failed: caption changed but the first row stayed the same |
| Row selection/profile | Update the side summary; open detail only on command | Failed during repair retest: row selection also opened the full modal |
| Add customer | Validate, save through API, and update table | Failed: generic validation message and table did not update |
| Edit/archive action menu | Perform named customer actions | Failed/missing |
| Modal X, Cancel, backdrop, Escape | Dismiss consistently | Failed: Escape left the modal open |

### Subscription plans

| Element | Expected | Initial result |
|---|---|---|
| Plan cards/table | Show live price, trial, status, features, subscribers | Failed: static data |
| Add plan | Create a real plan and first active price | Failed: API record did not appear |
| Edit icon | Edit the selected plan | Failed: opened the create dialog |
| Archive/activate icon | Change availability with confirmation | Failed: opened the create dialog |
| Search/status pagination | Operate on displayed plan data | Failed/static |

### Subscriptions

| Element | Expected | Initial result |
|---|---|---|
| Search/status/plan filters and pagination | Combine against live subscriptions | Failed/static |
| New trial | Start trial and display countdown immediately | Failed: backend changed, table did not |
| New non-trial subscription | Create an invoice and show pending payment | Failed: table did not update |
| Details | Show lifecycle dates and scheduled state | Missing |
| Change plan | Schedule a period-end plan change | Missing |
| Auto renewal | Persist and display on/off state | Missing |
| Cancel at period end/revoke | Preserve access and allow reversal | Missing |
| Cancel immediately | End access with confirmation | Missing |

### Payments

| Element | Expected | Initial result |
|---|---|---|
| Metrics/chart/table | Reflect recorded and allocated payments | Failed/static |
| Add payment | Select customer, allocate an invoice, and save | Critical failure: UI always sent `allocations: []` |
| Pending-subscription activation | Fully paid invoice activates immediately | Failed because payment became unallocated credit |
| Search/status pagination | Operate on live payment data | Failed/static |
| CSV export | Download the current payment dataset | Missing/inert |

### Invoices

| Element | Expected | Initial result |
|---|---|---|
| Metrics/table/filter/pagination | Reflect live invoice states and balances | Failed/static/incomplete |
| Generate draft | Create an itemized draft | Missing/incomplete |
| Finalize | Make a draft collectible | Missing |
| View/download | Load item detail and export it | Missing |
| Void | Preserve history but remove collectible balance | Missing; a later live regression exposed a non-zero void balance |

### Reports

| Element | Expected | Initial result |
|---|---|---|
| Period select | Change live series | Failed: text-only/static |
| Revenue/MRR/status/plan/customer panels | Derive from backend records | Failed: hardcoded |
| View-all links | Navigate to source datasets | Failed/inert |
| Export report | Download current values | Missing/inert |

### Notifications

| Element | Expected | Initial result |
|---|---|---|
| Table/filter/pagination | Show real notifications and status | Failed/static |
| New notification | Target all users or a real customer | Failed: customer select only contained “All users” |
| Row preview | Show complete dynamic message | Missing |
| Mark as read | Persist read state and update bell count | Missing |

### Settings

| Element | Expected | Initial result |
|---|---|---|
| Section navigation | Move to the requested settings group | Failed: toast-only/fake behavior |
| Currency/timezone/billing/numbering inputs | Load and persist backend settings | Failed: hardcoded and reset after reload |
| Save | Persist for authorized admin | Failed for billing with a backend 403 and no useful role-aware UI |
| Toggles | Persist and affect lifecycle defaults | Failed: visual-only state |
| Lifecycle preview/process | Confirm and call the lifecycle engine | Missing |

## Bugs and gaps fixed

| Location | Problem/root cause | Fix |
|---|---|---|
| Frontend data layer | Pages imported static sample arrays instead of querying the API | Added a typed API/session layer and centralized live-data provider with loading, error, retry, and refresh behavior |
| Login/session | Authentication failure handling and user role state were incomplete | Added real login response handling, stored user/scopes, loading/disabled state, useful API errors, and role-aware routing |
| Navigation/RBAC | Billing users could see admin routes and controls | Added role-filtered navigation, protected route redirects, UI gates, and retained backend scope enforcement |
| Tables | Pagination only changed text; plan/status controls were crossed | Rebuilt reusable table filtering and real row slicing; added combined search/status/plan filtering and reset/clamp logic |
| Modals | Escape and backdrop dismissal were inconsistent | Added a reusable accessible modal with focus, X, Cancel, backdrop, and Escape dismissal |
| Customer selection | Table row click reused full-profile modal state | Split side-panel selection from explicit full-profile state |
| Customers | Create/edit/archive did not refresh live data | Wired each action to API endpoints and centralized refresh/toast/error handling |
| Plans | Edit/archive buttons opened the create dialog | Added distinct edit/status handlers, metadata PATCH endpoint, and activate/archive confirmations |
| Plans | Created plans did not appear | Removed static list and refreshed live plan/price data after mutation |
| Subscriptions | No lifecycle controls in UI | Added details, trial countdown, auto-renew endpoint/control, scheduled plan change, cancellation scheduling/revocation, and immediate cancellation |
| Payments | Every payment was sent without invoice allocations | Added customer-specific open-invoice selection, balance autofill, explicit allocation payloads, and immediate state refresh |
| Payment activation | Fully paid non-trial subscriptions remained pending | Correct allocation now pays the invoice; backend activation is reflected immediately after refresh |
| Invoices | No usable draft/finalize/detail/download/void workflow | Added all workflows and an invoice-detail API returning item lines |
| Void invoices | Historical total was incorrectly presented as collectible balance | `invoice_amounts` now returns zero balance for `void` status while retaining total/paid history; regression test added |
| Reports | Hardcoded charts/panels and inert actions | Derived revenue, status, plan MRR, and customer totals from live records; added range control and CSV export |
| Notifications | Recipient list returned early before customer data loaded | Centralized parallel data loading; added populated recipient select, live preview, read state, and unread header count |
| Settings | Fake sections/toggles and non-persistent save | Replaced with backend-backed admin settings, section scrolling, validation, lifecycle preview/process confirmations |
| Seed behavior | Seed exited when any plan existed, leaving partial demo databases broken | Made demo seeding additive/idempotent by stable codes and relationships |
| Test isolation | API tests deleted/used the development database | Tests now set a dedicated `test_subscription.db` before importing the app |
| Mobile customers | Intrinsic table width forced page-level horizontal overflow | Added zero-min-width grid/card containment and kept horizontal scrolling inside the table card |
| Accessibility | Unnamed icon controls, decorative bell/logo, weak dialog semantics | Added accessible names, button/link semantics, dialog labels, keyboard dismissal, and visible hover/focus-capable controls |
| Tooling | Frontend `test` and `lint` scripts referenced missing tools | Added Vitest/Testing Library/jsdom and ESLint configuration; aligned Vite React plugin peer versions |
| Backend lifecycle startup | Deprecated FastAPI startup event | Migrated initialization/seeding to an application lifespan context |

## Subscription business-logic results

The following were performed through the browser against the running API unless explicitly identified as an automated API test:

- Plan comparison: live cards showed correct active price, interval, trial days, active subscriber count, featured state, and archive state.
- Trial: a 5-day trial was created and immediately displayed as `trialing` with “5 days left.”
- Non-trial checkout: a Basic subscription was created as `pending payment` with a ₱99.00 open invoice.
- Payment validation/allocation: selecting that invoice autofilled ₱99.00; the recorded payment showed ₱99.00 allocated and ₱0.00 unallocated.
- Activation: the associated subscription changed from `pending payment` to `active` immediately in the UI.
- Plan change: a period-end change from Browser QA Plus to Basic was scheduled and displayed in subscription detail.
- Auto renewal: changed from On to Off and persisted after refresh.
- Cancellation: period-end cancellation was scheduled, visibly labeled, revoked, then an isolated QA trial was canceled immediately with confirmation.
- Invoice lifecycle: a ₱42.00 draft was created, finalized to open, loaded with its item detail, exercised through CSV download, then voided; the final collectible balance was ₱0.00.
- Notifications: a customer-specific payment reminder was created, previewed, marked read, and the unread bell count updated from 1 to 0.
- Lifecycle maintenance: admin dry-run preview completed with a structured processed/skipped/failed result and no data mutation.
- RBAC: billing login omitted Reports/Settings and all plan-admin controls; direct `/reports` and `/settings` navigation redirected to Dashboard.
- Idempotency and structured unauthenticated errors were verified by backend automated tests.

## Responsive and state regression

- Desktop: 1379×958 final screenshot and all-route sweep; no page overflow or browser console errors.
- Tablet: 768×1024; two-column plan cards, mobile navigation trigger, no page overflow.
- Mobile: 390×844; single-column cards/charts, full-height slide-out navigation and close backdrop, responsive form modal, customer side panel hidden, and table scrolling contained inside the card.
- Empty states: verified on zero notifications/payments and filtered no-results cases.
- Validation: verified native required-field blocking and backend error presentation.
- Loading/error handling: every data route has a shared loading panel and retryable API error panel; final route sweep completed with neither stuck loading nor error panels.
- Rapid/repeated writes: saving controls disable while busy; backend idempotency coverage verifies duplicate subscription/payment keys do not duplicate records.
- The local demo database was reset after testing and contains only the three seeded demo customers/plans/subscriptions.

## Final regression matrix

| Area | Final result |
|---|---|
| Login, invalid credentials, admin login, billing login, sign out | Pass |
| Brand, sidebar, active links, desktop collapse, mobile open/close, bell, profile menu | Pass |
| Dashboard metrics, charts, range, recent links, new subscription | Pass |
| Customer search, combined filters, selection, profile, create, edit, archive, pagination behavior | Pass |
| Plan search/filter, create, edit, archive, activate, role gating | Pass |
| Trial/non-trial create, details, change plan, auto-renew, cancel/revoke/cancel-now | Pass |
| Payment creation, invoice allocation, metrics, table, filters, export | Pass |
| Invoice create, finalize, detail, CSV, void, zero collectible void balance | Pass |
| Report range, live metrics/charts/panels, export | Pass |
| Notification create, dynamic recipient, row preview, mark read, bell count | Pass |
| Settings load/save/reload, section navigation, toggles/inputs, lifecycle preview | Pass |
| Admin/billing route and action permissions | Pass |
| Authenticated 404 | Pass |
| Desktop/tablet/mobile overflow and responsive navigation | Pass |

All listed application pages and repaired interactive workflows were re-opened in the live browser after the fixes. The final nine-route sweep reported the correct heading, no stuck loader, no error panel, no open dialog, and no horizontal page overflow on every route. The browser console error log was empty.

## Automated verification

- Backend: `7 passed`; one third-party Starlette TestClient deprecation warning remains.
- Frontend unit/component tests: `4 passed` (combined filtering, real pagination, modal Escape/backdrop, CSV creation/click).
- Frontend lint: passed.
- Frontend production build: passed; Vite reports only the bundle-size advisory for the 668.19 kB main chunk.
- Package peer-dependency check: passed with no issues.

## Unresolved or intentionally unsupported capabilities

These were not silently simulated as production features:

- Real card/wallet checkout, gateway SDK, webhook signature verification, and asynchronous gateway status updates: no provider or credentials exist. The UI labels simulated/manual payment methods clearly.
- Coupons/promo codes: no coupon domain model, rules, or approved design exists.
- Usage/quota enforcement: no metered feature/seat/storage model exists in the supplied backend.
- Real email/SMS/push delivery: notifications are persisted in-app only.
- True proration/refunds/credit notes: plan changes are intentionally scheduled for the period end; no proration engine exists.
- Automated time travel for renewal/trial expiration in the browser: lifecycle behavior is exposed through preview/process and API tests, but the local UI has no clock-control test harness.

Implementing any of these would require a product/payment-provider decision and, for gateway work, sandbox credentials and webhook infrastructure.

## Further polish recommendations

- Split route bundles with dynamic imports to remove Vite’s >500 kB main-chunk advisory.
- Add Playwright/Cypress CI coverage for the browser journeys documented here.
- Replace Starlette’s deprecated TestClient/httpx integration when the dependency stack provides a stable migration path.
- Add a product-approved coupon/proration model before exposing related controls.
- Add automated accessibility tooling (axe) and screen-reader acceptance checks in CI.
