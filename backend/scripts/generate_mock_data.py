"""Generate realistic mock data for the Argo Subscription Management System.

Run from project root:
    .venv\Scripts\python.exe backend\generate_mock_data.py

Produces ~350+ records across all entities with realistic, varied data.
"""

import os
import sys
import uuid
import random
from datetime import date, datetime, timedelta, timezone

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, Base, engine
from app import models
from app.security import DEMO_ORGANIZATION_ID, Principal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ORG_ID = DEMO_ORGANIZATION_ID
ADMIN_USER_ID = "00000000-0000-0000-0000-000000000010"

random.seed(42)  # reproducible


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Data pools (realistic mock data)
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Juan", "Maria", "Pedro", "Ana", "Jose", "Carmen", "Luis", "Isabel", "Miguel", "Sofia",
    "Antonio", "Elena", "Francisco", "Lucia", "Carlos", "Martina", "Diego", "Valentina",
    "Gabriel", "Camila", "Andres", "Paula", "Rafael", "Diana", "Fernando", "Natalia",
    "Jorge", "Patricia", "Ricardo", "Daniela", "Alberto", "Monica", "Roberto", "Laura",
    "Hector", "Gabriela", "Sergio", "Alejandra", "Emilio", "Cristina", "Pablo", "Victoria",
    "Marcos", "Julia", "Raul", "Mariana", "Arturo", "Silvia", "Eduardo", "Renata",
]

LAST_NAMES = [
    "Dela Cruz", "Santos", "Reyes", "Garcia", "Mendoza", "Torres", "Ramos", "Flores",
    "Aquino", "Bautista", "Castro", "Delos Reyes", "Escobar", "Fernandez", "Gonzalez",
    "Hernandez", "Ignacio", "Jimenez", "Lopez", "Martin", "Navarro", "Ortega", "Perez",
    "Quisumbing", "Rodriguez", "Santiago", "Tan", "Uson", "Villanueva", "Yap",
    "Zamora", "Alvarez", "Bernardo", "Cruz", "Dizon", "Esteban", "Fajardo", "Guevara",
    "Herrera", "Ilagan", "Javier", "King", "Lim", "Magno", "Nieto", "Ocampo",
    "Padilla", "Quinto", "Rivera", "Sison",
]

COMPANIES = [
    ("Summit Digital Solutions", "corporation"),
    ("Pacific Cloud Services", "corporation"),
    ("Metro Data Partners", "partnership"),
    ("Bright Mind Academy", "corporation"),
    ("Apex Logistics Inc.", "corporation"),
    ("Horizon Tech Ventures", "partnership"),
    ("Stellar Software Labs", "corporation"),
    ("Crest Healthcare Systems", "corporation"),
    ("Vista Media Group", "partnership"),
    ("Unity Creatives Co.", "partnership"),
    ("North Star Analytics", "corporation"),
    ("EchoStream Networks", "corporation"),
    ("Prime Build Constructors", "corporation"),
    ("Greenleaf Consulting", "partnership"),
    ("Quantum Retail Solutions", "corporation"),
    ("BlueWave Maritime", "corporation"),
    ("Catalyst Education Inc.", "corporation"),
    ("Nova Financial Advisors", "partnership"),
    ("Phoenix Security Group", "corporation"),
    ("Zenith Design Studio", "partnership"),
    ("Pinnacle Energy Corp", "corporation"),
    ("Synergy Workforce Inc.", "corporation"),
    ("Atlas Shipping Lines", "corporation"),
    ("Dynasty Hospitality Group", "corporation"),
    ("Emerald AgriTech", "corporation"),
    ("Fusion Telecom Services", "corporation"),
    ("Meridian Real Estate", "partnership"),
    ("Titan Manufacturing Co.", "corporation"),
    ("Radiant Health Clinics", "partnership"),
    ("Stratos Aviation Ltd.", "corporation"),
    ("Beacon Publishing House", "corporation"),
    ("Cobalt IT Solutions", "partnership"),
    ("Aurora Events Management", "partnership"),
    ("Delta Freight Forwarders", "corporation"),
    ("Omicron Research Institute", "corporation"),
    ("Polaris Trading Company", "corporation"),
    ("Solstice Travel & Tours", "partnership"),
    ("Vertex Auto Services", "corporation"),
    ("Wavelength Audio Studios", "partnership"),
    ("Yonder Outdoor Gear", "corporation"),
]

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "company.ph", "corp.net", "business.io"]

CITIES = [
    ("Makati City", "Metro Manila", "1200"),
    ("Taguig City", "Metro Manila", "1630"),
    ("Quezon City", "Metro Manila", "1100"),
    ("Mandaluyong", "Metro Manila", "1550"),
    ("Pasig City", "Metro Manila", "1600"),
    ("San Juan", "Metro Manila", "1500"),
    ("Paranaque", "Metro Manila", "1700"),
    ("Muntinlupa City", "Metro Manila", "1780"),
    ("Caloocan City", "Metro Manila", "1400"),
    ("Manila", "Metro Manila", "1000"),
    ("Cebu City", "Cebu", "6000"),
    ("Mandaue City", "Cebu", "6014"),
    ("Lapu-Lapu City", "Cebu", "6015"),
    ("Davao City", "Davao del Sur", "8000"),
    ("Cagayan de Oro", "Misamis Oriental", "9000"),
    ("Iloilo City", "Iloilo", "5000"),
    ("Bacolod City", "Negros Occidental", "6100"),
    ("Baguio City", "Benguet", "2600"),
]

PLAN_DEFINITIONS = [
    ("STARTER", "Starter", "Essential tools for solo founders and small teams getting started.", 0, 1),
    ("GROWTH", "Growth", "Scaled features for growing businesses with moderate traffic.", 7, 2),
    ("PROFESSIONAL", "Professional", "Advanced capabilities for established teams and workflows.", 14, 3),
    ("ENTERPRISE", "Enterprise", "Full-featured platform with priority support and compliance.", 14, 4),
    ("ELITE", "Elite", "White-glove service with dedicated infrastructure and custom SLA.", 30, 5),
    ("BASIC_WEB", "Basic Web", "Lightweight web hosting and email for personal projects.", 0, 6),
    ("ECOMMERCE", "E-Commerce Pro", "Storefront, inventory, and payment processing for online sellers.", 14, 7),
    ("DEVELOPER", "Developer Hub", "API access, CI/CD credits, and staging environments for dev teams.", 7, 8),
]

FEATURE_DEFINITIONS = [
    ("users", "User Seats", "Number of team members allowed", "number", "seats"),
    ("storage", "Cloud Storage", "File and media storage quota", "number", "GB"),
    ("api_calls", "API Requests", "Monthly API call limit", "number", "calls"),
    ("support", "Support Level", "Customer support tier included", "text", None),
    ("analytics", "Analytics Dashboard", "Access to advanced analytics", "boolean", None),
    ("custom_domain", "Custom Domain", "Use your own branded domain", "boolean", None),
    ("sso", "SSO / SAML", "Single sign-on authentication", "boolean", None),
    ("dedicated_ip", "Dedicated IP", "Isolated IP address for your tenant", "boolean", None),
    ("sla", "Uptime SLA", "Guaranteed availability percentage", "text", None),
    ("webhooks", "Webhooks", "Real-time event notifications", "boolean", None),
]

NOTIFICATION_TYPES = [
    ("trial_ending", "Trial Ending Soon", "Your trial period ends in {days} days. Add a payment method to avoid interruption."),
    ("invoice_generated", "New Invoice Available", "Invoice {invoice_number} for {amount} has been generated and is due on {due_date}."),
    ("payment_received", "Payment Received", "We received your payment of {amount} for invoice {invoice_number}. Thank you!"),
    ("payment_failed", "Payment Failed", "We could not process your payment of {amount}. Please update your payment method."),
    ("subscription_activated", "Subscription Activated", "Your subscription {subscription_number} is now active."),
    ("plan_changed", "Plan Change Scheduled", "Your plan change to {plan_name} will take effect on {effective_date}."),
    ("subscription_cancelled", "Subscription Cancelled", "Your subscription {subscription_number} has been cancelled."),
    ("overdue_reminder", "Overdue Invoice Reminder", "Invoice {invoice_number} is now overdue. Please settle to avoid suspension."),
    ("welcome", "Welcome Aboard", "Welcome to Argo! Your account is set up and ready to go."),
    ("password_changed", "Security Alert", "Your account password was changed on {date}. If this wasn't you, contact support immediately."),
]

PAYMENT_METHODS = ["manual_cash", "manual_bank", "simulated_card", "simulated_wallet"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pick(lst):
    return random.choice(lst)


def rand_date(start: date, end: date) -> date:
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def rand_datetime(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = int(delta.total_seconds())
    return start + timedelta(seconds=random.randint(0, seconds))


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def generate_features(session: Session) -> list[models.Feature]:
    existing = session.scalars(select(models.Feature).where(models.Feature.organization_id == ORG_ID)).all()
    if existing:
        return existing
    records = []
    for code, name, desc, vtype, unit in FEATURE_DEFINITIONS:
        f = models.Feature(
            id=make_id(),
            organization_id=ORG_ID,
            feature_code=code,
            name=name,
            description=desc,
            value_type=vtype,
            unit_label=unit,
            status="active",
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(f)
        records.append(f)
    session.flush()
    return records


def generate_plans_and_prices(session: Session) -> tuple[list[models.Plan], list[models.PlanPrice]]:
    existing_plans = session.scalars(select(models.Plan).where(models.Plan.organization_id == ORG_ID)).all()
    if existing_plans:
        prices = session.scalars(select(models.PlanPrice).where(models.PlanPrice.organization_id == ORG_ID)).all()
        return existing_plans, prices

    plans: list[models.Plan] = []
    prices: list[models.PlanPrice] = []

    base_amounts = [9900, 29900, 59900, 129900, 249900, 4900, 79900, 39900]

    for idx, (code, name, desc, trial, order) in enumerate(PLAN_DEFINITIONS):
        plan = models.Plan(
            id=make_id(),
            organization_id=ORG_ID,
            plan_code=code,
            name=name,
            description=desc,
            status="active",
            trial_days=trial,
            is_featured=(name == "Growth" or name == "Professional"),
            display_order=order,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(plan)
        plans.append(plan)
        session.flush()

        # Monthly price
        monthly = models.PlanPrice(
            id=make_id(),
            organization_id=ORG_ID,
            plan_id=plan.id,
            price_code=f"{code}-MONTHLY",
            billing_interval="month",
            interval_count=1,
            currency="PHP",
            unit_amount_minor=base_amounts[idx],
            setup_fee_minor=random.choice([0, 0, 0, 5000, 10000]),
            status="active",
            effective_from=date(2024, 1, 1),
            is_default=True,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(monthly)
        prices.append(monthly)

        # Yearly price (15% discount roughly)
        yearly = models.PlanPrice(
            id=make_id(),
            organization_id=ORG_ID,
            plan_id=plan.id,
            price_code=f"{code}-YEARLY",
            billing_interval="year",
            interval_count=1,
            currency="PHP",
            unit_amount_minor=int(base_amounts[idx] * 10.2),
            setup_fee_minor=0,
            status="active",
            effective_from=date(2024, 1, 1),
            is_default=False,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(yearly)
        prices.append(yearly)

    session.flush()
    return plans, prices


def generate_plan_features(session: Session, plans: list[models.Plan], features: list[models.Feature]):
    existing = session.scalars(select(models.PlanFeature).where(models.PlanFeature.organization_id == ORG_ID)).all()
    if existing:
        return

    plan_feature_values = {
        "STARTER": {"users": 3, "storage": 10, "api_calls": 1000, "support": "email", "analytics": False, "custom_domain": False, "sso": False, "dedicated_ip": False, "sla": "99.0%", "webhooks": False},
        "GROWTH": {"users": 10, "storage": 50, "api_calls": 10000, "support": "email+chat", "analytics": True, "custom_domain": True, "sso": False, "dedicated_ip": False, "sla": "99.5%", "webhooks": True},
        "PROFESSIONAL": {"users": 25, "storage": 200, "api_calls": 50000, "support": "priority", "analytics": True, "custom_domain": True, "sso": True, "dedicated_ip": False, "sla": "99.9%", "webhooks": True},
        "ENTERPRISE": {"users": 100, "storage": 1000, "api_calls": 200000, "support": "dedicated", "analytics": True, "custom_domain": True, "sso": True, "dedicated_ip": True, "sla": "99.95%", "webhooks": True},
        "ELITE": {"users": 500, "storage": 5000, "api_calls": 1000000, "support": "white-glove", "analytics": True, "custom_domain": True, "sso": True, "dedicated_ip": True, "sla": "99.99%", "webhooks": True},
        "BASIC_WEB": {"users": 1, "storage": 5, "api_calls": 500, "support": "community", "analytics": False, "custom_domain": False, "sso": False, "dedicated_ip": False, "sla": "99.0%", "webhooks": False},
        "ECOMMERCE": {"users": 5, "storage": 100, "api_calls": 25000, "support": "email+chat", "analytics": True, "custom_domain": True, "sso": False, "dedicated_ip": False, "sla": "99.5%", "webhooks": True},
        "DEVELOPER": {"users": 15, "storage": 100, "api_calls": 100000, "support": "priority", "analytics": True, "custom_domain": True, "sso": True, "dedicated_ip": False, "sla": "99.9%", "webhooks": True},
    }

    for plan in plans:
        values = plan_feature_values.get(plan.plan_code, {})
        for feature in features:
            val = values.get(feature.feature_code)
            pf = models.PlanFeature(
                id=make_id(),
                organization_id=ORG_ID,
                plan_id=plan.id,
                feature_id=feature.id,
                is_included=bool(val) if isinstance(val, bool) else True,
                value_boolean=val if feature.value_type == "boolean" and isinstance(val, bool) else None,
                value_number=val if feature.value_type == "number" and isinstance(val, int) else None,
                value_text=str(val) if feature.value_type == "text" and val is not None else None,
                display_order=random.randint(0, 10),
                created_by=ADMIN_USER_ID,
                updated_by=ADMIN_USER_ID,
            )
            session.add(pf)
    session.flush()


def generate_customers_and_addresses(session: Session, count: int = 50) -> list[models.Customer]:
    existing = session.scalars(select(models.Customer).where(models.Customer.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    customers: list[models.Customer] = []
    used_emails: set[str] = set()

    for i in range(count - len(existing)):
        is_company = random.random() < 0.45
        if is_company:
            comp_name, ctype = pick(COMPANIES)
            display_name = comp_name
            company_name = comp_name
            email = f"billing.{display_name.lower().replace(' ', '-').replace('.', '').replace(',', '')}@{pick(EMAIL_DOMAINS)}"
        else:
            fname = pick(FIRST_NAMES)
            lname = pick(LAST_NAMES)
            display_name = f"{fname} {lname}"
            company_name = None
            email = f"{fname.lower()}.{lname.lower().replace(' ', '')}@{pick(EMAIL_DOMAINS)}"

        # ensure unique email
        while email in used_emails:
            email = email.replace("@", f"{random.randint(1,999)}@")
        used_emails.add(email)

        code = f"CUS-{random.randint(100000, 999999):06d}"
        customer = models.Customer(
            id=make_id(),
            organization_id=ORG_ID,
            customer_code=code,
            customer_type="organization" if is_company else "individual",
            display_name=display_name,
            company_name=company_name,
            email=email,
            phone=f"09{random.randint(10,99):02d}{random.randint(1000000,9999999):07d}",
            tax_identifier=f"TIN-{random.randint(100000000,999999999):09d}" if is_company else None,
            status=random.choices(["active", "active", "active", "archived"], weights=[70, 15, 10, 5])[0],
            notes=None,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(customer)
        customers.append(customer)
        session.flush()

        # Address
        city, province, postal = pick(CITIES)
        addr = models.Address(
            id=make_id(),
            organization_id=ORG_ID,
            customer_id=customer.id,
            address_type=random.choice(["billing", "shipping"]),
            line1=f"{random.randint(1, 999)} {pick(['Main', 'Commerce', 'Rizal', 'Mabini', 'Quezon', 'Bonifacio'])} St.",
            line2=f"Floor {random.randint(1, 20)}, Suite {random.randint(100, 999)}" if is_company else None,
            city_municipality=city,
            province=province,
            postal_code=postal,
            country_code="PH",
            is_primary=True,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(addr)

    session.flush()
    return customers


def generate_subscriptions(
    session: Session,
    customers: list[models.Customer],
    prices: list[models.PlanPrice],
    count: int = 60,
) -> list[models.Subscription]:
    existing = session.scalars(
        select(models.Subscription).where(models.Subscription.organization_id == ORG_ID)
    ).all()
    if len(existing) >= count:
        return existing

    statuses = ["active", "trialing", "pending_payment", "past_due", "suspended", "cancelled", "expired"]
    weights = [35, 10, 8, 7, 5, 10, 5]

    subscriptions: list[models.Subscription] = []
    now = utcnow()
    start_window = now - timedelta(days=180)

    for i in range(count - len(existing)):
        customer = pick(customers)
        if customer.status != "active":
            continue
        price = pick(prices)
        plan = session.get(models.Plan, price.plan_id)

        status = random.choices(statuses, weights=weights)[0]
        starts_at = rand_datetime(start_window, now - timedelta(days=1))

        trial = status == "trialing" and plan.trial_days > 0
        trial_start = starts_at if trial else None
        trial_end = starts_at + timedelta(days=plan.trial_days) if trial else None

        if status in ["active", "pending_payment", "past_due", "suspended"]:
            current_start = starts_at if not trial else trial_end
            current_end = current_start + timedelta(days=30) if price.billing_interval == "month" else current_start + timedelta(days=365)
            next_bill = current_end
        elif status == "cancelled":
            current_start = starts_at
            current_end = starts_at + timedelta(days=30)
            next_bill = None
        elif status == "expired":
            current_start = starts_at
            current_end = starts_at + timedelta(days=30)
            next_bill = None
        else:
            current_start = None
            current_end = None
            next_bill = None

        sub = models.Subscription(
            id=make_id(),
            organization_id=ORG_ID,
            subscription_number=f"SUB-{random.randint(100000, 999999):06d}",
            customer_id=customer.id,
            plan_id=plan.id,
            plan_price_id=price.id,
            status=status,
            starts_at=starts_at,
            trial_start_at=trial_start,
            trial_end_at=trial_end,
            current_period_start=current_start,
            current_period_end=current_end,
            next_billing_at=next_bill,
            auto_renew=status not in ["cancelled", "expired"] and random.random() < 0.85,
            cancel_at_period_end=status == "cancelled" and random.random() < 0.7,
            cancelled_at=current_end if status == "cancelled" else None,
            ended_at=current_end if status in ["cancelled", "expired"] else None,
            cancellation_reason=(
                pick([
                    "Customer requested cancellation",
                    "Switching to competitor",
                    "Business closure",
                    "Cost reduction",
                    "No longer needed",
                ]) if status == "cancelled" else None
            ),
            version=random.randint(1, 5),
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(sub)
        subscriptions.append(sub)

    session.flush()
    return subscriptions


def generate_invoices_and_items(
    session: Session,
    subscriptions: list[models.Subscription],
    prices: list[models.PlanPrice],
    count: int = 50,
) -> list[models.Invoice]:
    existing = session.scalars(select(models.Invoice).where(models.Invoice.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    invoices: list[models.Invoice] = []
    now = utcnow()

    # First generate subscription-linked invoices
    subs_for_invoicing = [s for s in subscriptions if s.status not in ["trialing", "expired"]]
    for sub in subs_for_invoicing[: min(len(subs_for_invoicing), count // 2)]:
        price = next((p for p in prices if p.id == sub.plan_price_id), None)
        if not price:
            continue
        issue = (sub.current_period_start or sub.starts_at).date() - timedelta(days=1)
        due = issue + timedelta(days=7)
        inv_status = random.choice(["draft", "open", "paid", "overdue", "void"])
        finalized = utcnow() if inv_status != "draft" else None
        voided = utcnow() if inv_status == "void" else None

        inv = models.Invoice(
            id=make_id(),
            organization_id=ORG_ID,
            invoice_number=f"INV-{random.randint(100000, 999999):06d}",
            customer_id=sub.customer_id,
            subscription_id=sub.id,
            status=inv_status,
            issue_date=issue,
            due_date=due,
            service_period_start=sub.current_period_start,
            service_period_end=sub.current_period_end,
            currency=price.currency,
            notes=pick(["Monthly renewal", "Quarterly service fee", "Annual subscription prorated", None, None]),
            finalized_at=finalized,
            voided_at=voided,
            void_reason=("Incorrect amount billed" if inv_status == "void" else None),
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(inv)
        invoices.append(inv)
        session.flush()

        # Line items
        amount = price.unit_amount_minor + price.setup_fee_minor
        item = models.InvoiceItem(
            id=make_id(),
            organization_id=ORG_ID,
            invoice_id=inv.id,
            line_number=1,
            item_type="recurring",
            description=f"Subscription renewal ({price.billing_interval})",
            quantity=1,
            unit_amount_minor=amount,
            tax_rate_bps=0,
            service_period_start=sub.current_period_start,
            service_period_end=sub.current_period_end,
            plan_id=sub.plan_id,
            plan_price_id=price.id,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(item)

    # Generate standalone invoices
    customers = session.scalars(select(models.Customer).where(models.Customer.organization_id == ORG_ID)).all()
    remaining = count - len(invoices) - len(existing)
    for i in range(max(0, remaining)):
        customer = pick(customers)
        issue = rand_date(date(2024, 6, 1), date.today())
        due = issue + timedelta(days=7)
        inv_status = random.choice(["draft", "open", "paid", "overdue", "void"])
        inv = models.Invoice(
            id=make_id(),
            organization_id=ORG_ID,
            invoice_number=f"INV-{random.randint(100000, 999999):06d}",
            customer_id=customer.id,
            subscription_id=None,
            status=inv_status,
            issue_date=issue,
            due_date=due,
            service_period_start=datetime.combine(issue, datetime.min.time(), tzinfo=timezone.utc),
            service_period_end=datetime.combine(due, datetime.min.time(), tzinfo=timezone.utc),
            currency="PHP",
            notes=pick(["One-time consulting fee", "Setup services", "Custom integration", None]),
            finalized_at=utcnow() if inv_status != "draft" else None,
            voided_at=utcnow() if inv_status == "void" else None,
            void_reason=("Client request" if inv_status == "void" else None),
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(inv)
        invoices.append(inv)
        session.flush()

        # 1-3 line items
        for line in range(1, random.randint(2, 4)):
            descs = [
                "Professional services",
                "Consulting hours",
                "Custom development",
                "Training session",
                "Support package",
                "Data migration",
                "API integration",
            ]
            item = models.InvoiceItem(
                id=make_id(),
                organization_id=ORG_ID,
                invoice_id=inv.id,
                line_number=line,
                item_type=random.choice(["recurring", "setup", "adjustment"]),
                description=pick(descs),
                quantity=random.randint(1, 5),
                unit_amount_minor=random.choice([5000, 10000, 15000, 25000, 50000]),
                tax_rate_bps=0,
                service_period_start=inv.service_period_start,
                service_period_end=inv.service_period_end,
                plan_id=None,
                plan_price_id=None,
                created_by=ADMIN_USER_ID,
                updated_by=ADMIN_USER_ID,
            )
            session.add(item)

    session.flush()
    return invoices


def generate_payments_and_allocations(
    session: Session,
    invoices: list[models.Invoice],
    count: int = 30,
) -> list[models.Payment]:
    existing = session.scalars(select(models.Payment).where(models.Payment.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    customers = session.scalars(select(models.Customer).where(models.Customer.organization_id == ORG_ID)).all()
    payments: list[models.Payment] = []

    for i in range(count - len(existing)):
        customer = pick(customers)
        method = pick(PAYMENT_METHODS)
        amount = random.choice([9900, 14900, 29900, 39900, 59900, 79900, 99900, 129900])
        status = random.choices(["completed", "completed", "completed", "voided"], weights=[80, 10, 5, 5])[0]
        received = rand_datetime(utcnow() - timedelta(days=60), utcnow())

        payment = models.Payment(
            id=make_id(),
            organization_id=ORG_ID,
            payment_reference=f"PAY-{random.randint(100000, 999999):06d}",
            customer_id=customer.id,
            payment_attempt_id=None,
            payment_method=method,
            status=status,
            amount_minor=amount,
            currency="PHP",
            received_at=received,
            external_reference=pick([f"REF-{random.randint(1000,9999)}", None, None]),
            notes=pick(["Cash payment at office", "Bank transfer - BPI", "GCash transfer", None]),
            voided_at=received if status == "voided" else None,
            void_reason=("Duplicate entry" if status == "voided" else None),
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(payment)
        payments.append(payment)
        session.flush()

        # Allocate to random open/paid invoices for this customer
        customer_invoices = [inv for inv in invoices if inv.customer_id == customer.id and inv.status in ["open", "paid", "overdue"]]
        if customer_invoices and status == "completed":
            target = pick(customer_invoices)
            alloc_amount = min(amount, random.randint(amount // 2, amount))
            alloc = models.PaymentAllocation(
                id=make_id(),
                organization_id=ORG_ID,
                payment_id=payment.id,
                invoice_id=target.id,
                amount_minor=alloc_amount,
                allocated_at=received,
                created_by=ADMIN_USER_ID,
                updated_by=ADMIN_USER_ID,
            )
            session.add(alloc)

    session.flush()
    return payments


def generate_payment_attempts(session: Session, invoices: list[models.Invoice], count: int = 15) -> list[models.PaymentAttempt]:
    existing = session.scalars(select(models.PaymentAttempt).where(models.PaymentAttempt.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    open_invoices = [inv for inv in invoices if inv.status == "open"]
    attempts: list[models.PaymentAttempt] = []

    for i in range(count - len(existing)):
        if not open_invoices:
            break
        invoice = pick(open_invoices)
        status = random.choices(["pending", "succeeded", "failed"], weights=[30, 40, 30])[0]
        amount = random.choice([9900, 29900, 59900, 79900])
        attempted = rand_datetime(utcnow() - timedelta(days=30), utcnow())

        attempt = models.PaymentAttempt(
            id=make_id(),
            organization_id=ORG_ID,
            attempt_reference=f"ATT-{random.randint(100000, 999999):06d}",
            invoice_id=invoice.id,
            provider="simulated",
            provider_attempt_id=f"sim_{make_id()[:8]}" if status != "pending" else None,
            idempotency_key=f"idem_{make_id()}",
            request_hash="mock-hash",
            status=status,
            amount_minor=amount,
            currency=invoice.currency,
            attempted_at=attempted,
            completed_at=attempted if status != "pending" else None,
            failure_message=(
                pick([
                    "Insufficient funds",
                    "Card declined by issuer",
                    "Expired card",
                    "Invalid CVV",
                ]) if status == "failed" else None
            ),
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(attempt)
        attempts.append(attempt)

    session.flush()
    return attempts


def generate_subscription_events(session: Session, subscriptions: list[models.Subscription], count: int = 30) -> list[models.SubscriptionEvent]:
    existing = session.scalars(select(models.SubscriptionEvent).where(models.SubscriptionEvent.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    events: list[models.SubscriptionEvent] = []
    event_types = [
        ("created", None),
        ("activated", None),
        ("payment_activated", None),
        ("plan_change_scheduled", None),
        ("auto_renew_updated", "Auto renewal toggled"),
        ("schedule_cancel", "Customer initiated cancellation"),
        ("cancel_now", "Immediate cancellation requested"),
        ("due_processed", None),
    ]

    for i in range(count - len(existing)):
        sub = pick(subscriptions)
        evt_type, reason_template = pick(event_types)
        from_status = sub.status
        to_status = sub.status

        if evt_type == "created":
            from_status = None
            to_status = "trialing" if sub.trial_start_at else "pending_payment"
        elif evt_type == "activated":
            from_status = "pending_payment"
            to_status = "active"
        elif evt_type == "payment_activated":
            from_status = pick(["pending_payment", "past_due", "suspended"])
            to_status = "active"
        elif evt_type == "schedule_cancel":
            from_status = sub.status
            to_status = sub.status

        effective = rand_datetime(sub.starts_at, utcnow())
        event = models.SubscriptionEvent(
            id=make_id(),
            organization_id=ORG_ID,
            subscription_id=sub.id,
            event_type=evt_type,
            from_status=from_status,
            to_status=to_status,
            effective_at=effective,
            actor_type="user",
            reason=reason_template or pick(["System processed", "User action", "Payment received", "Scheduled event"]),
            correlation_id=make_id(),
            metadata_json={"source": "mock_data"},
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(event)
        events.append(event)

    session.flush()
    return events


def generate_notifications(session: Session, customers: list[models.Customer], subscriptions: list[models.Subscription], invoices: list[models.Invoice], count: int = 20) -> list[models.Notification]:
    existing = session.scalars(select(models.Notification).where(models.Notification.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    notifications: list[models.Notification] = []

    for i in range(count - len(existing)):
        ntype, title_template, body_template = pick(NOTIFICATION_TYPES)
        customer = pick(customers) if random.random() < 0.7 else None
        sub = pick(subscriptions) if random.random() < 0.5 else None
        inv = pick(invoices) if random.random() < 0.5 else None

        title = title_template
        body = body_template.format(
            days=random.randint(1, 5),
            invoice_number=inv.invoice_number if inv else "INV-000000",
            amount=f"PHP {random.choice([99, 299, 599, 799]):,}.00",
            subscription_number=sub.subscription_number if sub else "SUB-000000",
            plan_name=pick(["Starter", "Growth", "Professional", "Enterprise"]),
            effective_date=(utcnow() + timedelta(days=7)).date().isoformat(),
            due_date=(utcnow() + timedelta(days=7)).date().isoformat(),
            date=utcnow().date().isoformat(),
        )

        notice = models.Notification(
            id=make_id(),
            organization_id=ORG_ID,
            customer_id=customer.id if customer else None,
            recipient_user_id=ADMIN_USER_ID,
            channel="in_app",
            notification_type=ntype,
            title=title,
            body=body,
            status=random.choice(["sent", "sent", "read"]),
            related_entity_type=pick(["subscription", "invoice", "payment", "customer"]),
            related_entity_id=(sub.id if sub else inv.id if inv else customer.id if customer else None),
            sent_at=rand_datetime(utcnow() - timedelta(days=30), utcnow()),
            read_at=utcnow() if random.random() < 0.3 else None,
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(notice)
        notifications.append(notice)

    session.flush()
    return notifications


def generate_activity_logs(session: Session, customers: list[models.Customer], plans: list[models.Plan], subscriptions: list[models.Subscription], invoices: list[models.Invoice], payments: list[models.Payment], count: int = 40) -> list[models.ActivityLog]:
    existing = session.scalars(select(models.ActivityLog).where(models.ActivityLog.organization_id == ORG_ID)).all()
    if len(existing) >= count:
        return existing

    logs: list[models.ActivityLog] = []
    actions = ["created", "updated", "viewed", "deleted", "finalized", "voided", "recorded", "status_changed"]
    entity_pools = [
        ("customer", customers),
        ("plan", plans),
        ("subscription", subscriptions),
        ("invoice", invoices),
        ("payment", payments),
    ]

    for i in range(count - len(existing)):
        entity_type, pool = pick(entity_pools)
        entity = pick(pool)
        action = pick(actions)

        log = models.ActivityLog(
            id=make_id(),
            organization_id=ORG_ID,
            entity_type=entity_type,
            entity_id=entity.id,
            action=action,
            actor_user_id=ADMIN_USER_ID,
            request_id=make_id(),
            details_json={"source": "mock_seed", "action": action},
            created_by=ADMIN_USER_ID,
            updated_by=ADMIN_USER_ID,
        )
        session.add(log)
        logs.append(log)

    session.flush()
    return logs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("Argo Subscription Management — Mock Data Generator")
    print("=" * 60)

    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        # Ensure settings row exists
        settings = session.scalar(select(models.Settings).where(models.Settings.organization_id == ORG_ID))
        if not settings:
            settings = models.Settings(
                id=make_id(),
                organization_id=ORG_ID,
                default_currency="PHP",
                timezone="Asia/Manila",
                invoice_due_days=7,
                grace_period_days=7,
                max_payment_retries=3,
                retry_interval_days=1,
                trial_reminder_days=3,
                invoice_due_reminder_days=3,
                auto_renew_default=True,
                allow_partial_payments=True,
                auto_generate_invoices=True,
                invoice_prefix="INV",
                payment_prefix="PAY",
                subscription_prefix="SUB",
                customer_prefix="CUS",
                enable_in_app_notifications=True,
                created_by=ADMIN_USER_ID,
                updated_by=ADMIN_USER_ID,
            )
            session.add(settings)
            session.flush()

        # 1. Features
        features = generate_features(session)
        print(f"  Features          : {len(features)}")

        # 2. Plans + Prices
        plans, prices = generate_plans_and_prices(session)
        print(f"  Plans             : {len(plans)}")
        print(f"  Plan Prices       : {len(prices)}")

        # 3. Plan Features
        generate_plan_features(session, plans, features)
        pf_count = session.scalar(select(func.count()).select_from(models.PlanFeature).where(models.PlanFeature.organization_id == ORG_ID)) or 0
        print(f"  Plan Features     : {pf_count}")

        # 4. Customers + Addresses
        customers = generate_customers_and_addresses(session, count=50)
        addr_count = session.scalar(select(func.count()).select_from(models.Address).where(models.Address.organization_id == ORG_ID)) or 0
        print(f"  Customers         : {len(customers)}")
        print(f"  Addresses         : {addr_count}")

        # 5. Subscriptions
        subscriptions = generate_subscriptions(session, customers, prices, count=60)
        print(f"  Subscriptions     : {len(subscriptions)}")

        # 6. Invoices + Items
        invoices = generate_invoices_and_items(session, subscriptions, prices, count=50)
        item_count = session.scalar(select(func.count()).select_from(models.InvoiceItem).where(models.InvoiceItem.organization_id == ORG_ID)) or 0
        print(f"  Invoices          : {len(invoices)}")
        print(f"  Invoice Items     : {item_count}")

        # 7. Payments + Allocations
        payments = generate_payments_and_allocations(session, invoices, count=30)
        alloc_count = session.scalar(select(func.count()).select_from(models.PaymentAllocation).where(models.PaymentAllocation.organization_id == ORG_ID)) or 0
        print(f"  Payments          : {len(payments)}")
        print(f"  Allocations       : {alloc_count}")

        # 8. Payment Attempts
        attempts = generate_payment_attempts(session, invoices, count=15)
        print(f"  Payment Attempts  : {len(attempts)}")

        # 9. Subscription Events
        events = generate_subscription_events(session, subscriptions, count=30)
        print(f"  Subscription Events: {len(events)}")

        # 10. Notifications
        notifications = generate_notifications(session, customers, subscriptions, invoices, count=20)
        print(f"  Notifications     : {len(notifications)}")

        # 11. Activity Logs
        logs = generate_activity_logs(session, customers, plans, subscriptions, invoices, payments, count=40)
        print(f"  Activity Logs     : {len(logs)}")

        session.commit()

    print("-" * 60)
    print("Mock data generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
