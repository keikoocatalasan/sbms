"""Safe, idempotent fake data for the standalone demonstration only."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, services
from .security import DEMO_ORGANIZATION_ID, Principal


def seed_demo(session: Session) -> None:
    admin = Principal(user_id="00000000-0000-0000-0000-000000000010", organization_id=DEMO_ORGANIZATION_ID, scopes={"subscription:admin"}, name="Demo Administrator")
    settings = services.settings_for(session, admin)
    catalog = [("BASIC", "Basic", 9900, 7), ("STANDARD", "Standard", 29900, 14), ("PREMIUM", "Premium", 59900, 14)]
    prices: list[models.PlanPrice] = []
    for order, (code, name, amount, trial_days) in enumerate(catalog):
        plan = session.scalar(select(models.Plan).where(models.Plan.organization_id == admin.organization_id, models.Plan.plan_code == code))
        if not plan:
            plan = models.Plan(organization_id=admin.organization_id, plan_code=code, name=name, description=f"{name} demonstration subscription plan", status="active", trial_days=trial_days, is_featured=name == "Standard", display_order=order, created_by=admin.user_id, updated_by=admin.user_id)
            session.add(plan); session.flush()
        price = session.scalar(select(models.PlanPrice).where(models.PlanPrice.organization_id == admin.organization_id, models.PlanPrice.price_code == f"{code}-MONTHLY"))
        if not price:
            price = models.PlanPrice(organization_id=admin.organization_id, plan_id=plan.id, price_code=f"{code}-MONTHLY", billing_interval="month", currency="PHP", unit_amount_minor=amount, status="active", is_default=True, created_by=admin.user_id, updated_by=admin.user_id)
            session.add(price)
        prices.append(price)
    session.flush()
    customers = []
    for index, name in enumerate(["Juan Dela Cruz", "Maria Santos", "Tech Solutions Inc."]):
        code = f"{settings.customer_prefix}-DEMO-{index+1:03d}"
        customer = session.scalar(select(models.Customer).where(models.Customer.organization_id == admin.organization_id, models.Customer.customer_code == code))
        if not customer:
            customer = models.Customer(organization_id=admin.organization_id, customer_code=code, customer_type="organization" if "Inc" in name else "individual", display_name=name, company_name=name if "Inc" in name else None, email=f"demo{index+1}@example.com", phone="09171234567", status="active", created_by=admin.user_id, updated_by=admin.user_id)
            session.add(customer)
        customers.append(customer)
    session.flush()
    started = datetime.now(timezone.utc) - timedelta(days=10)
    for index, customer in enumerate(customers):
        price = prices[index]
        existing = session.scalar(select(models.Subscription.id).where(models.Subscription.organization_id == admin.organization_id, models.Subscription.customer_id == customer.id, models.Subscription.plan_price_id == price.id))
        if not existing:
            session.add(models.Subscription(organization_id=admin.organization_id, subscription_number=f"{settings.subscription_prefix}-DEMO-{index+1:03d}", customer_id=customer.id, plan_id=price.plan_id, plan_price_id=price.id, status="active", starts_at=started, current_period_start=started, current_period_end=started + timedelta(days=30), next_billing_at=started + timedelta(days=30), auto_renew=True, created_by=admin.user_id, updated_by=admin.user_id))
    session.commit()
