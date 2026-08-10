from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SignupRequest(APIModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class CustomerCreate(APIModel):
    display_name: str = Field(min_length=1, max_length=160)
    customer_type: Literal["individual", "organization"] = "individual"
    company_name: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    tax_identifier: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).lower() if value else None


class CustomerUpdate(APIModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    company_name: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)


class PlanCreate(APIModel):
    plan_code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    trial_days: int = Field(default=0, ge=0, le=365)
    is_featured: bool = False
    display_order: int = Field(default=0, ge=0)


class PlanUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    trial_days: int | None = Field(default=None, ge=0, le=365)
    is_featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0)


class PriceCreate(APIModel):
    price_code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    billing_interval: Literal["month", "year"]
    interval_count: int = Field(default=1, ge=1, le=12)
    currency: str = Field(default="PHP", pattern=r"^[A-Z]{3}$")
    unit_amount_minor: int = Field(ge=0)
    setup_fee_minor: int = Field(default=0, ge=0)
    effective_from: date = Field(default_factory=date.today)
    is_default: bool = True


class PlanStatus(APIModel):
    status: Literal["draft", "active", "inactive", "archived"]


class SubscriptionCreate(APIModel):
    customer_id: str
    plan_price_id: str
    starts_at: datetime
    auto_renew: bool = True
    use_trial: bool = True


class VersionedCommand(APIModel):
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)


class PlanChangeCommand(VersionedCommand):
    target_plan_price_id: str


class AutoRenewCommand(APIModel):
    expected_version: int = Field(ge=1)
    auto_renew: bool


class InvoiceItemInput(APIModel):
    item_type: Literal["recurring", "setup", "adjustment", "discount"] = "recurring"
    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1, le=100000)
    unit_amount_minor: int
    tax_rate_bps: int = Field(default=0, ge=0, le=10000)
    service_period_start: datetime | None = None
    service_period_end: datetime | None = None


class InvoiceCreate(APIModel):
    customer_id: str
    subscription_id: str | None = None
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    currency: str = Field(default="PHP", pattern=r"^[A-Z]{3}$")
    service_period_start: datetime | None = None
    service_period_end: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    items: list[InvoiceItemInput] = Field(min_length=1)


class AllocationInput(APIModel):
    invoice_id: str
    amount_minor: int = Field(gt=0)


class PaymentCreate(APIModel):
    customer_id: str
    payment_method: Literal["manual_cash", "manual_bank"]
    amount_minor: int = Field(gt=0)
    currency: str = Field(default="PHP", pattern=r"^[A-Z]{3}$")
    received_at: datetime | None = None
    external_reference: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=2000)
    allocations: list[AllocationInput] = Field(default_factory=list)


class PaymentAttemptCreate(APIModel):
    invoice_id: str
    provider: Literal["manual"] = "manual"
    amount_minor: int = Field(gt=0)
    currency: str = Field(default="PHP", pattern=r"^[A-Z]{3}$")


class CompletePaymentAttempt(APIModel):
    payment_method: Literal["manual_cash", "manual_bank"] = "manual_bank"
    external_reference: str | None = Field(default=None, max_length=128)
    received_at: datetime | None = None
    allocations: list[AllocationInput] = Field(default_factory=list)


class NotificationCreate(APIModel):
    customer_id: str | None = None
    recipient_user_id: str | None = None
    notification_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)
    related_entity_type: str | None = Field(default=None, max_length=40)
    related_entity_id: str | None = None


class SettingsUpdate(APIModel):
    default_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timezone: str | None = Field(default=None, max_length=64)
    invoice_due_days: int | None = Field(default=None, ge=0, le=365)
    grace_period_days: int | None = Field(default=None, ge=0, le=365)
    allow_partial_payments: bool | None = None
    auto_renew_default: bool | None = None
    auto_generate_invoices: bool | None = None
    invoice_prefix: str | None = Field(default=None, pattern=r"^[A-Z]{2,8}$")
    payment_prefix: str | None = Field(default=None, pattern=r"^[A-Z]{2,8}$")
    subscription_prefix: str | None = Field(default=None, pattern=r"^[A-Z]{2,8}$")
    customer_prefix: str | None = Field(default=None, pattern=r"^[A-Z]{2,8}$")


class DueProcess(APIModel):
    as_of: datetime | None = None
    batch_size: int = Field(default=50, ge=1, le=200)
    dry_run: bool = False


class Envelope(BaseModel):
    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)
    request_id: str
