import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "subscription_organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class User(Base):
    __tablename__ = "subscription_users"
    __table_args__ = (UniqueConstraint("email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AuthSession(Base):
    __tablename__ = "subscription_auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TenantRecord:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36))
    updated_by: Mapped[str | None] = mapped_column(String(36))


class Customer(TenantRecord, Base):
    __tablename__ = "subscription_customers"
    __table_args__ = (UniqueConstraint("organization_id", "customer_code"), UniqueConstraint("organization_id", "email"))
    customer_code: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_type: Mapped[str] = mapped_column(String(20), default="individual")
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(160))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(32))
    tax_identifier: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Address(TenantRecord, Base):
    __tablename__ = "subscription_customer_addresses"
    customer_id: Mapped[str] = mapped_column(ForeignKey("subscription_customers.id"), nullable=False, index=True)
    address_type: Mapped[str] = mapped_column(String(20), default="billing")
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(255))
    city_municipality: Mapped[str] = mapped_column(String(120), nullable=False)
    province: Mapped[str | None] = mapped_column(String(120))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country_code: Mapped[str] = mapped_column(String(2), default="PH")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class Plan(TenantRecord, Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (UniqueConstraint("organization_id", "plan_code"),)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    trial_days: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class PlanPrice(TenantRecord, Base):
    __tablename__ = "subscription_plan_prices"
    __table_args__ = (UniqueConstraint("organization_id", "price_code"),)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False, index=True)
    price_code: Mapped[str] = mapped_column(String(50), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(10), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, default=1)
    currency: Mapped[str] = mapped_column(String(3), default="PHP")
    list_amount_minor: Mapped[int | None] = mapped_column(Integer)
    unit_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    setup_fee_minor: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    effective_from: Mapped[date] = mapped_column(Date, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)


class Feature(TenantRecord, Base):
    __tablename__ = "subscription_features"
    __table_args__ = (UniqueConstraint("organization_id", "feature_code"),)
    feature_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(20), default="boolean")
    unit_label: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="active")


class PlanFeature(TenantRecord, Base):
    __tablename__ = "subscription_plan_features"
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    feature_id: Mapped[str] = mapped_column(ForeignKey("subscription_features.id"), nullable=False)
    billing_interval: Mapped[str | None] = mapped_column(String(10))
    is_included: Mapped[bool] = mapped_column(Boolean, default=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean)
    value_number: Mapped[int | None] = mapped_column(Integer)
    value_text: Mapped[str | None] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(TenantRecord, Base):
    __tablename__ = "subscription_subscriptions"
    __table_args__ = (UniqueConstraint("organization_id", "subscription_number"),)
    subscription_number: Mapped[str] = mapped_column(String(48), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("subscription_customers.id"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("subscription_plans.id"), nullable=False)
    plan_price_id: Mapped[str] = mapped_column(ForeignKey("subscription_plan_prices.id"), nullable=False)
    pending_plan_id: Mapped[str | None] = mapped_column(String(36))
    pending_plan_price_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_billing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    plan_change_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SubscriptionEvent(TenantRecord, Base):
    __tablename__ = "subscription_subscription_events"
    subscription_id: Mapped[str] = mapped_column(ForeignKey("subscription_subscriptions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str | None] = mapped_column(String(24))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor_type: Mapped[str] = mapped_column(String(20), default="user")
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(36))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Invoice(TenantRecord, Base):
    __tablename__ = "subscription_invoices"
    __table_args__ = (UniqueConstraint("organization_id", "invoice_number"),)
    invoice_number: Mapped[str] = mapped_column(String(48), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("subscription_customers.id"), nullable=False, index=True)
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey("subscription_subscriptions.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    service_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)


class InvoiceItem(TenantRecord, Base):
    __tablename__ = "subscription_invoice_items"
    __table_args__ = (UniqueConstraint("organization_id", "invoice_id", "line_number"),)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("subscription_invoices.id"), nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), default="recurring")
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_rate_bps: Mapped[int] = mapped_column(Integer, default=0)
    service_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    service_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_id: Mapped[str | None] = mapped_column(String(36))
    plan_price_id: Mapped[str | None] = mapped_column(String(36))


class PaymentAttempt(TenantRecord, Base):
    __tablename__ = "subscription_payment_attempts"
    attempt_reference: Mapped[str] = mapped_column(String(48), nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("subscription_invoices.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), default="manual")
    provider_attempt_id: Mapped[str | None] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_message: Mapped[str | None] = mapped_column(String(255))


class Payment(TenantRecord, Base):
    __tablename__ = "subscription_payments"
    __table_args__ = (UniqueConstraint("organization_id", "payment_reference"),)
    payment_reference: Mapped[str] = mapped_column(String(48), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("subscription_customers.id"), nullable=False, index=True)
    payment_attempt_id: Mapped[str | None] = mapped_column(ForeignKey("subscription_payment_attempts.id"))
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    external_reference: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(Text)


class PaymentAllocation(TenantRecord, Base):
    __tablename__ = "subscription_payment_allocations"
    payment_id: Mapped[str] = mapped_column(ForeignKey("subscription_payments.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("subscription_invoices.id"), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(TenantRecord, Base):
    __tablename__ = "subscription_notifications"
    customer_id: Mapped[str | None] = mapped_column(String(36), index=True)
    recipient_user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="sent")
    related_entity_type: Mapped[str | None] = mapped_column(String(40))
    related_entity_id: Mapped[str | None] = mapped_column(String(36))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Settings(TenantRecord, Base):
    __tablename__ = "subscription_settings"
    __table_args__ = (UniqueConstraint("organization_id"),)
    default_currency: Mapped[str] = mapped_column(String(3), default="PHP")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Manila")
    invoice_due_days: Mapped[int] = mapped_column(Integer, default=7)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7)
    max_payment_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_interval_days: Mapped[int] = mapped_column(Integer, default=1)
    trial_reminder_days: Mapped[int] = mapped_column(Integer, default=3)
    invoice_due_reminder_days: Mapped[int] = mapped_column(Integer, default=3)
    auto_renew_default: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_partial_payments: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_generate_invoices: Mapped[bool] = mapped_column(Boolean, default=True)
    invoice_prefix: Mapped[str] = mapped_column(String(8), default="INV")
    payment_prefix: Mapped[str] = mapped_column(String(8), default="PAY")
    subscription_prefix: Mapped[str] = mapped_column(String(8), default="SUB")
    customer_prefix: Mapped[str] = mapped_column(String(8), default="CUS")
    enable_in_app_notifications: Mapped[bool] = mapped_column(Boolean, default=True)


class IdempotencyKey(TenantRecord, Base):
    __tablename__ = "subscription_idempotency_keys"
    __table_args__ = (UniqueConstraint("organization_id", "operation", "idempotency_key"),)
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(36))
    response_status: Mapped[int] = mapped_column(Integer, default=201)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ActivityLog(TenantRecord, Base):
    __tablename__ = "subscription_activity_logs"
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    request_id: Mapped[str | None] = mapped_column(String(36), index=True)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
