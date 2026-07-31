"""Add the remaining 5 plans that weren't created because seed_demo already had 3."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from sqlalchemy import select
from app.db import SessionLocal
from app import models
from app.security import DEMO_ORGANIZATION_ID

ORG_ID = DEMO_ORGANIZATION_ID
ADMIN_USER_ID = "00000000-0000-0000-0000-000000000010"

def make_id():
    import uuid
    return str(uuid.uuid4())

PLAN_DEFINITIONS = [
    ("ELITE", "Elite", "White-glove service with dedicated infrastructure and custom SLA.", 30, 5),
    ("BASIC_WEB", "Basic Web", "Lightweight web hosting and email for personal projects.", 0, 6),
    ("ECOMMERCE", "E-Commerce Pro", "Storefront, inventory, and payment processing for online sellers.", 14, 7),
    ("DEVELOPER", "Developer Hub", "API access, CI/CD credits, and staging environments for dev teams.", 7, 8),
    ("STARTER", "Starter", "Essential tools for solo founders and small teams getting started.", 0, 1),
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

plan_feature_values = {
    "STARTER": {"users": 3, "storage": 10, "api_calls": 1000, "support": "email", "analytics": False, "custom_domain": False, "sso": False, "dedicated_ip": False, "sla": "99.0%", "webhooks": False},
    "ELITE": {"users": 500, "storage": 5000, "api_calls": 1000000, "support": "white-glove", "analytics": True, "custom_domain": True, "sso": True, "dedicated_ip": True, "sla": "99.99%", "webhooks": True},
    "BASIC_WEB": {"users": 1, "storage": 5, "api_calls": 500, "support": "community", "analytics": False, "custom_domain": False, "sso": False, "dedicated_ip": False, "sla": "99.0%", "webhooks": False},
    "ECOMMERCE": {"users": 5, "storage": 100, "api_calls": 25000, "support": "email+chat", "analytics": True, "custom_domain": True, "sso": False, "dedicated_ip": False, "sla": "99.5%", "webhooks": True},
    "DEVELOPER": {"users": 15, "storage": 100, "api_calls": 100000, "support": "priority", "analytics": True, "custom_domain": True, "sso": True, "dedicated_ip": False, "sla": "99.9%", "webhooks": True},
}

base_amounts = {"STARTER": 9900, "ELITE": 249900, "BASIC_WEB": 4900, "ECOMMERCE": 79900, "DEVELOPER": 39900}

with SessionLocal() as session:
    # Ensure all features exist
    features = {}
    for code, name, desc, vtype, unit in FEATURE_DEFINITIONS:
        f = session.scalar(select(models.Feature).where(models.Feature.organization_id == ORG_ID, models.Feature.feature_code == code))
        if not f:
            f = models.Feature(
                id=make_id(), organization_id=ORG_ID, feature_code=code, name=name,
                description=desc, value_type=vtype, unit_label=unit, status="active",
                created_by=ADMIN_USER_ID, updated_by=ADMIN_USER_ID,
            )
            session.add(f)
            session.flush()
        features[code] = f

    added_plans = 0
    added_prices = 0

    for code, name, desc, trial, order in PLAN_DEFINITIONS:
        existing = session.scalar(select(models.Plan).where(models.Plan.organization_id == ORG_ID, models.Plan.plan_code == code))
        if existing:
            print(f"  Plan {code} already exists, skipping")
            continue

        plan = models.Plan(
            id=make_id(), organization_id=ORG_ID, plan_code=code, name=name,
            description=desc, status="active", trial_days=trial,
            is_featured=(name in ["Growth", "Professional"]),
            display_order=order, created_by=ADMIN_USER_ID, updated_by=ADMIN_USER_ID,
        )
        session.add(plan)
        session.flush()
        added_plans += 1

        base = base_amounts[code]
        # Monthly
        monthly = models.PlanPrice(
            id=make_id(), organization_id=ORG_ID, plan_id=plan.id,
            price_code=f"{code}-MONTHLY", billing_interval="month", interval_count=1,
            currency="PHP", unit_amount_minor=base, setup_fee_minor=0,
            status="active", is_default=True,
            created_by=ADMIN_USER_ID, updated_by=ADMIN_USER_ID,
        )
        session.add(monthly)
        session.flush()
        added_prices += 1

        # Yearly
        yearly = models.PlanPrice(
            id=make_id(), organization_id=ORG_ID, plan_id=plan.id,
            price_code=f"{code}-YEARLY", billing_interval="year", interval_count=1,
            currency="PHP", unit_amount_minor=int(base * 10.2), setup_fee_minor=0,
            status="active", is_default=False,
            created_by=ADMIN_USER_ID, updated_by=ADMIN_USER_ID,
        )
        session.add(yearly)
        session.flush()
        added_prices += 1

        # Plan features
        values = plan_feature_values[code]
        for feat_code, feat in features.items():
            val = values.get(feat_code)
            pf = models.PlanFeature(
                id=make_id(), organization_id=ORG_ID, plan_id=plan.id, feature_id=feat.id,
                is_included=bool(val) if isinstance(val, bool) else True,
                value_boolean=val if feat.value_type == "boolean" and isinstance(val, bool) else None,
                value_number=val if feat.value_type == "number" and isinstance(val, int) else None,
                value_text=str(val) if feat.value_type == "text" and val is not None else None,
                display_order=0, created_by=ADMIN_USER_ID, updated_by=ADMIN_USER_ID,
            )
            session.add(pf)

    session.commit()
    print(f"Added {added_plans} plans and {added_prices} prices.")
