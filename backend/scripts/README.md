# Mock Data Scripts

This directory contains standalone Python scripts for generating realistic demonstration data for the Argo Subscription Management System.

## Scripts

### `seed_full_year.py`

**Primary generator.** Produces 2,600+ unique records spanning **September 2025 – August 2026**.

**Usage:**
```bash
cd backend
.\.venv\Scripts\python.exe scripts\seed_full_year.py
```

**What it generates:**

| Entity | Count | Notes |
|--------|-------|-------|
| Customers | 320 | Unique names, emails, phones, companies, addresses across 80 PH cities |
| Addresses | 320 | Billing/shipping with realistic streets & postal codes |
| Subscriptions | 420 | Full lifecycle: trial → active → renewals → upgrades → cancellations |
| Invoices | 751 | 1–4 per subscription + standalone, all statuses |
| Invoice Items | 999 | Recurring, setup, adjustment, discount lines |
| Payments | 220 | Cash, bank, card, wallet with allocations |
| Payment Allocations | 83 | Linked to open/paid invoices |
| Payment Attempts | 100 | Pending, succeeded, failed with realistic error messages |
| Subscription Events | 180 | Full audit trail (created, activated, cancelled, etc.) |
| Notifications | 120 | In-app alerts across the year |
| Activity Logs | 180 | Admin actions on all entities |
| **Total** | **~2,640** | |

**Behavior:**
- Clears all existing mock data first (keeps plans, prices, features, settings)
- Uses `bulk_save_objects()` for fast insertion (~5–10 seconds)
- Deterministic random seed (`20250801`) for reproducibility

---

### `generate_mock_data.py`

Quick-seed generator producing ~350 records. Useful for rapid prototyping or small demos.

**Usage:**
```bash
cd backend
.\.venv\Scripts\python.exe scripts\generate_mock_data.py
```

---

### `add_missing_plans.py`

Adds the 5 additional plans (Elite, Basic Web, E-Commerce Pro, Developer, Starter) if the demo seed only created the initial 3 plans (Basic, Standard, Premium).

**Usage:**
```bash
cd backend
.\.venv\Scripts\python.exe scripts\add_missing_plans.py
```

---

## Data Uniqueness Guarantees

All scripts enforce:
- **Unique customer codes** (`CUS-{random}`) via set deduplication
- **Unique emails** via domain + numeric suffix fallback
- **Unique phones** (09XXXXXXXXX format)
- **Unique subscription numbers** (`SUB-{random}`)
- **Unique invoice numbers** (`INV-{random}`)
- **Unique payment references** (`PAY-{random}`)

Name pools:
- **150+ first names** × **100+ last names** = 15,000+ unique individual name combinations
- **300+ company names** from realistic Philippine businesses
- **80 cities/provinces** with proper postal codes

---

## Re-running

Scripts are idempotent within their own scope. `seed_full_year.py` will **clear existing customer, subscription, invoice, payment, and log data** before inserting, but preserves plans and pricing. This allows clean re-runs without re-creating the catalog.
