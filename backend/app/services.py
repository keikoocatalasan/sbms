import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .security import Principal

T = TypeVar("T", bound=models.TenantRecord)


def now() -> datetime:
    return datetime.now(timezone.utc)


def public(record: Any) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        result[column.name] = value
    return result


def one(session: Session, model: type[T], organization_id: str, record_id: str) -> T:
    record = session.scalar(select(model).where(model.id == record_id, model.organization_id == organization_id))
    if not record:
        raise HTTPException(404, "Resource not found")
    return record


BACKOFFICE_SCOPES = frozenset({"subscription:admin", "subscription:billing", "subscription:support", "subscription:reports", "subscription:system"})
NO_CUSTOMER_MATCH = "__no_customer_match__"


def is_restricted_principal(principal: Principal) -> bool:
    return not principal.scopes.intersection(BACKOFFICE_SCOPES)


def self_customer_id(session: Session, principal: Principal) -> str | None:
    """Return the sole customer visible to a subscriber user.

    The current schema predates an explicit user/customer link, so email is
    used as a compatibility bridge until the membership migration adds that
    relationship. A sentinel prevents an unlinked user from seeing everyone.
    """
    if not is_restricted_principal(principal):
        return None
    user = session.get(models.User, principal.user_id)
    if not user:
        return NO_CUSTOMER_MATCH
    customer_id = session.scalar(
        select(models.Customer.id).where(
            models.Customer.organization_id == principal.organization_id,
            func.lower(models.Customer.email) == user.email.lower(),
        )
    )
    return customer_id or NO_CUSTOMER_MATCH


def plan_feature_public(session: Session, plan_id: str, organization_id: str, active_only: bool = False, billing_interval: str | None = None) -> list[dict[str, Any]]:
    filters = [models.PlanFeature.plan_id == plan_id, models.PlanFeature.organization_id == organization_id]
    if billing_interval:
        filters.append((models.PlanFeature.billing_interval.is_(None)) | (models.PlanFeature.billing_interval == billing_interval))
    if active_only:
        filters.append(models.PlanFeature.is_included.is_(True))
    feature_rows = session.scalars(select(models.PlanFeature).where(*filters).order_by(models.PlanFeature.display_order, models.PlanFeature.created_at)).all()
    result = []
    for row in feature_rows:
        feature = session.scalar(select(models.Feature).where(models.Feature.id == row.feature_id, models.Feature.organization_id == organization_id))
        if not feature or (active_only and feature.status != "active"):
            continue
        payload = public(row)
        payload["feature"] = public(feature)
        result.append(payload)
    return result


def list_page(session: Session, model: type[T], organization_id: str, page: int, page_size: int, q: str | None = None, text_column: Any | None = None, customer_id: str | None = None) -> tuple[list[T], int]:
    filters = [model.organization_id == organization_id]
    if q and text_column is not None:
        filters.append(text_column.ilike(f"%{q.strip()}%"))
    if customer_id is not None:
        filters.append(getattr(model, "customer_id", model.id) == customer_id)
    total = session.scalar(select(func.count()).select_from(model).where(*filters)) or 0
    rows = session.scalars(select(model).where(*filters).order_by(model.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def reference(prefix: str, record_id: str) -> str:
    return f"{prefix}-{record_id.replace('-', '')[:10].upper()}"


def event(session: Session, principal: Principal, subscription: models.Subscription, event_type: str, previous: str | None, reason: str | None, request_id: str) -> None:
    session.add(models.SubscriptionEvent(organization_id=principal.organization_id, subscription_id=subscription.id, event_type=event_type, from_status=previous, to_status=subscription.status, effective_at=now(), actor_type="user", reason=reason, correlation_id=request_id, created_by=principal.user_id, updated_by=principal.user_id))
    activity(session, principal, "subscription", subscription.id, event_type, request_id, {"from_status": previous, "to_status": subscription.status})


def activity(session: Session, principal: Principal, entity_type: str, entity_id: str, action: str, request_id: str, details: dict[str, Any] | None = None) -> None:
    session.add(models.ActivityLog(organization_id=principal.organization_id, entity_type=entity_type, entity_id=entity_id, action=action, actor_user_id=principal.user_id, request_id=request_id, details_json=details, created_by=principal.user_id, updated_by=principal.user_id))


def notification(session: Session, principal: Principal, title: str, body: str, notification_type: str, request_id: str, customer_id: str | None = None, related_id: str | None = None) -> None:
    session.add(models.Notification(organization_id=principal.organization_id, customer_id=customer_id, recipient_user_id=principal.user_id, notification_type=notification_type, title=title, body=body, related_entity_id=related_id, related_entity_type=notification_type, created_by=principal.user_id, updated_by=principal.user_id))


def invoice_amounts(session: Session, invoice: models.Invoice) -> dict[str, int]:
    item_total = session.scalar(select(func.coalesce(func.sum(models.InvoiceItem.quantity * models.InvoiceItem.unit_amount_minor), 0)).where(models.InvoiceItem.invoice_id == invoice.id, models.InvoiceItem.organization_id == invoice.organization_id)) or 0
    paid = session.scalar(select(func.coalesce(func.sum(models.PaymentAllocation.amount_minor), 0)).join(models.Payment).where(models.PaymentAllocation.invoice_id == invoice.id, models.PaymentAllocation.organization_id == invoice.organization_id, models.Payment.status == "completed")) or 0
    balance = 0 if invoice.status == "void" else max(0, int(item_total - paid))
    return {"total_minor": int(item_total), "paid_minor": int(paid), "balance_minor": balance}


def invoice_public(session: Session, invoice: models.Invoice) -> dict[str, Any]:
    payload = public(invoice)
    amounts = invoice_amounts(session, invoice)
    payload["amounts"] = amounts
    # Expose the state implied by the ledger, even when an older import left
    # the stored status behind the payment allocations.
    if invoice.status not in {"draft", "void"}:
        payload["status"] = "paid" if amounts["balance_minor"] <= 0 else "overdue" if invoice.due_date < date.today() else "open"
    return payload


def payment_allocated_amount(session: Session, payment: models.Payment) -> int:
    return int(session.scalar(select(func.coalesce(func.sum(models.PaymentAllocation.amount_minor), 0)).where(models.PaymentAllocation.payment_id == payment.id, models.PaymentAllocation.organization_id == payment.organization_id)) or 0)


def payment_public(session: Session, payment: models.Payment) -> dict[str, Any]:
    payload = public(payment)
    payload["allocated_minor"] = payment_allocated_amount(session, payment)
    payload["unallocated_minor"] = max(0, payment.amount_minor - payload["allocated_minor"])
    return payload


def payment_public_many(session: Session, payments: list[models.Payment]) -> list[dict[str, Any]]:
    """Serialize a payment page with one allocation aggregate query.

    Payment pages are fetched in batches by the frontend. Calling
    ``payment_public`` for every row performs one allocation query per payment,
    which becomes a visible N+1 latency problem once the ledger contains a
    realistic history. Keep the single-payment helper for mutation responses,
    and use this batched path for collection endpoints.
    """
    if not payments:
        return []
    payment_ids = [payment.id for payment in payments]
    organization_id = payments[0].organization_id
    allocated_rows = session.execute(
        select(
            models.PaymentAllocation.payment_id,
            func.coalesce(func.sum(models.PaymentAllocation.amount_minor), 0),
        )
        .where(
            models.PaymentAllocation.payment_id.in_(payment_ids),
            models.PaymentAllocation.organization_id == organization_id,
        )
        .group_by(models.PaymentAllocation.payment_id)
    ).all()
    allocated_by_payment = {payment_id: int(amount or 0) for payment_id, amount in allocated_rows}
    result: list[dict[str, Any]] = []
    for payment in payments:
        payload = public(payment)
        allocated = allocated_by_payment.get(payment.id, 0)
        payload["allocated_minor"] = allocated
        payload["unallocated_minor"] = max(0, payment.amount_minor - allocated)
        result.append(payload)
    return result


def invoice_public_many(session: Session, invoices: list[models.Invoice]) -> list[dict[str, Any]]:
    """Serialize an invoice page with batched item and allocation totals."""
    if not invoices:
        return []
    invoice_ids = [invoice.id for invoice in invoices]
    organization_id = invoices[0].organization_id
    item_rows = session.execute(
        select(
            models.InvoiceItem.invoice_id,
            func.coalesce(func.sum(models.InvoiceItem.quantity * models.InvoiceItem.unit_amount_minor), 0),
        )
        .where(
            models.InvoiceItem.invoice_id.in_(invoice_ids),
            models.InvoiceItem.organization_id == organization_id,
        )
        .group_by(models.InvoiceItem.invoice_id)
    ).all()
    paid_rows = session.execute(
        select(
            models.PaymentAllocation.invoice_id,
            func.coalesce(func.sum(models.PaymentAllocation.amount_minor), 0),
        )
        .join(models.Payment, models.Payment.id == models.PaymentAllocation.payment_id)
        .where(
            models.PaymentAllocation.invoice_id.in_(invoice_ids),
            models.PaymentAllocation.organization_id == organization_id,
            models.Payment.organization_id == organization_id,
            models.Payment.status == "completed",
        )
        .group_by(models.PaymentAllocation.invoice_id)
    ).all()
    item_totals = {invoice_id: int(amount or 0) for invoice_id, amount in item_rows}
    paid_totals = {invoice_id: int(amount or 0) for invoice_id, amount in paid_rows}
    today = date.today()
    result: list[dict[str, Any]] = []
    for invoice in invoices:
        total = item_totals.get(invoice.id, 0)
        paid = paid_totals.get(invoice.id, 0)
        balance = 0 if invoice.status == "void" else max(0, total - paid)
        payload = public(invoice)
        payload["amounts"] = {"total_minor": total, "paid_minor": paid, "balance_minor": balance}
        if invoice.status not in {"draft", "void"}:
            payload["status"] = "paid" if balance <= 0 else "overdue" if invoice.due_date < today else "open"
        result.append(payload)
    return result


def sync_invoice(session: Session, invoice: models.Invoice) -> None:
    if invoice.status in {"draft", "void"}:
        return
    amounts = invoice_amounts(session, invoice)
    if amounts["balance_minor"] <= 0:
        invoice.status = "paid"
    elif invoice.due_date < date.today():
        invoice.status = "overdue"
    else:
        invoice.status = "open"


def activate_subscription_for_invoice(session: Session, principal: Principal, invoice: models.Invoice, request_id: str) -> None:
    if not invoice.subscription_id or invoice.status != "paid":
        return
    subscription = one(session, models.Subscription, principal.organization_id, invoice.subscription_id)
    if subscription.status in {"pending_payment", "past_due", "suspended"}:
        previous = subscription.status
        subscription.status = "active"
        subscription.updated_by = principal.user_id
        subscription.version += 1
        event(session, principal, subscription, "payment_activated", previous, "Payment settled", request_id)


def create_invoice_for_subscription(session: Session, principal: Principal, subscription: models.Subscription, issue_at: datetime, request_id: str) -> models.Invoice:
    price = one(session, models.PlanPrice, principal.organization_id, subscription.plan_price_id)
    settings = settings_for(session, principal)
    issue_date = issue_at.date()
    invoice = models.Invoice(organization_id=principal.organization_id, invoice_number=reference(settings.invoice_prefix, str(__import__('uuid').uuid4())), customer_id=subscription.customer_id, subscription_id=subscription.id, status="open", issue_date=issue_date, due_date=issue_date + timedelta(days=settings.invoice_due_days), service_period_start=subscription.current_period_start or issue_at, service_period_end=subscription.current_period_end, currency=price.currency, finalized_at=issue_at, created_by=principal.user_id, updated_by=principal.user_id)
    session.add(invoice)
    session.flush()
    session.add(models.InvoiceItem(organization_id=principal.organization_id, invoice_id=invoice.id, line_number=1, item_type="recurring", description=f"Subscription renewal ({price.billing_interval})", quantity=1, unit_amount_minor=price.unit_amount_minor + price.setup_fee_minor, tax_rate_bps=0, service_period_start=invoice.service_period_start, service_period_end=invoice.service_period_end, plan_id=subscription.plan_id, plan_price_id=price.id, created_by=principal.user_id, updated_by=principal.user_id))
    session.flush()
    activity(session, principal, "invoice", invoice.id, "created_from_subscription", request_id)
    apply_unallocated_credits(session, principal, subscription.customer_id, invoice.currency, request_id, invoice.id)
    return invoice


def settings_for(session: Session, principal: Principal) -> models.Settings:
    settings = session.scalar(select(models.Settings).where(models.Settings.organization_id == principal.organization_id))
    if settings:
        return settings
    settings = models.Settings(organization_id=principal.organization_id, created_by=principal.user_id, updated_by=principal.user_id)
    session.add(settings)
    session.flush()
    return settings


def claim_idempotency(session: Session, principal: Principal, operation: str, key: str | None, body: Any) -> dict[str, Any] | None:
    if not key:
        raise HTTPException(400, "Idempotency-Key header is required")
    request_hash = hashlib.sha256(json.dumps(body, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    existing = session.scalar(select(models.IdempotencyKey).where(models.IdempotencyKey.organization_id == principal.organization_id, models.IdempotencyKey.operation == operation, models.IdempotencyKey.idempotency_key == key))
    if not existing:
        session.add(models.IdempotencyKey(organization_id=principal.organization_id, operation=operation, idempotency_key=key, request_hash=request_hash, created_by=principal.user_id, updated_by=principal.user_id))
        session.flush()
        return None
    if existing.request_hash != request_hash:
        raise HTTPException(409, "Idempotency key was used with a different request")
    if existing.result_json is None:
        raise HTTPException(409, "Request with this idempotency key is still in progress")
    return existing.result_json


def complete_idempotency(session: Session, principal: Principal, operation: str, key: str, result: dict[str, Any], resource_type: str, resource_id: str, response_status: int = 201) -> None:
    record = session.scalar(select(models.IdempotencyKey).where(models.IdempotencyKey.organization_id == principal.organization_id, models.IdempotencyKey.operation == operation, models.IdempotencyKey.idempotency_key == key))
    if record:
        record.result_json, record.resource_type, record.resource_id, record.response_status = result, resource_type, resource_id, response_status


def apply_unallocated_credits(session: Session, principal: Principal, customer_id: str, currency: str, request_id: str, invoice_id: str | None = None) -> int:
    """Apply existing completed account credit to the oldest collectible invoices."""
    settings = settings_for(session, principal)
    invoice_filters = [
        models.Invoice.organization_id == principal.organization_id,
        models.Invoice.customer_id == customer_id,
        models.Invoice.currency == currency,
        # A legacy paid row can still carry a balance when the original
        # allocation was recorded out of order. Keep it collectible until
        # the balance is actually settled and sync_invoice can canonicalize it.
        models.Invoice.status.in_(["open", "overdue", "paid"]),
    ]
    if invoice_id:
        invoice_filters.append(models.Invoice.id == invoice_id)
    invoices = session.scalars(select(models.Invoice).where(*invoice_filters).order_by(models.Invoice.due_date, models.Invoice.created_at)).all()
    if not invoices:
        return 0
    payments = session.scalars(select(models.Payment).where(models.Payment.organization_id == principal.organization_id, models.Payment.customer_id == customer_id, models.Payment.currency == currency, models.Payment.status == "completed").order_by(models.Payment.received_at, models.Payment.created_at)).all()
    applied = 0
    for payment in payments:
        remaining = payment.amount_minor - payment_allocated_amount(session, payment)
        if remaining <= 0:
            continue
        for invoice in invoices:
            if remaining <= 0:
                break
            balance = invoice_amounts(session, invoice)["balance_minor"]
            if balance <= 0:
                continue
            if not settings.allow_partial_payments and remaining < balance:
                continue
            amount = min(remaining, balance)
            session.add(models.PaymentAllocation(organization_id=principal.organization_id, payment_id=payment.id, invoice_id=invoice.id, amount_minor=amount, created_by=principal.user_id, updated_by=principal.user_id))
            session.flush()
            sync_invoice(session, invoice)
            activate_subscription_for_invoice(session, principal, invoice, request_id)
            remaining -= amount
            applied += amount
    return applied


def allocate(session: Session, principal: Principal, payment: models.Payment, allocations: list[dict[str, Any]], request_id: str) -> None:
    if payment.status != "completed":
        raise HTTPException(409, "Only completed payments can be allocated")
    settings = settings_for(session, principal)
    allocated = payment_allocated_amount(session, payment)
    requested = sum(int(a["amount_minor"]) for a in allocations)
    if not requested:
        return
    if allocated + requested > payment.amount_minor:
        raise HTTPException(409, "Allocations exceed the payment amount")
    for input_item in allocations:
        invoice = one(session, models.Invoice, principal.organization_id, input_item["invoice_id"])
        if invoice.customer_id != payment.customer_id or invoice.currency != payment.currency:
            raise HTTPException(409, "Payment and invoice customer/currency must match")
        balance = invoice_amounts(session, invoice)["balance_minor"]
        if input_item["amount_minor"] > balance:
            raise HTTPException(409, "Allocation exceeds invoice balance")
        if not settings.allow_partial_payments and input_item["amount_minor"] != balance:
            raise HTTPException(409, "Partial payments are disabled; allocate the full invoice balance")
        session.add(models.PaymentAllocation(organization_id=principal.organization_id, payment_id=payment.id, invoice_id=invoice.id, amount_minor=input_item["amount_minor"], created_by=principal.user_id, updated_by=principal.user_id))
        session.flush()
        sync_invoice(session, invoice)
        activate_subscription_for_invoice(session, principal, invoice, request_id)


def subscription_period(starts_at: datetime, price: models.PlanPrice) -> tuple[datetime, datetime]:
    if price.billing_interval == "year":
        return starts_at, starts_at + timedelta(days=365 * price.interval_count)
    return starts_at, starts_at + timedelta(days=30 * price.interval_count)
