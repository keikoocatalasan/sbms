from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from . import models, schemas, services
from .config import get_settings
from .db import Base, engine, secure_postgres_tables
from .security import ADMIN_SCOPES, DBSession, MEMBER_SCOPES, Principal, current_principal, hash_password, issue_token, request_id, require_scope, verify_password


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    secure_postgres_tables()
    yield


app = FastAPI(title="Argo Subscription Management API", version="1.0.0", lifespan=lifespan, openapi_tags=[{"name": name} for name in ["Infrastructure", "Authentication", "Dashboard", "Customers", "Plans", "Subscriptions", "Invoices", "Payment Attempts", "Payments", "Notifications", "Reports", "Settings", "Activity", "Maintenance"]])
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"], expose_headers=["X-Request-ID"])


@app.middleware("http")
async def correlate(request: Request, call_next: Any) -> Any:
    request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "STATE_CONFLICT", 422: "VALIDATION_ERROR"}.get(exc.status_code, "REQUEST_ERROR")
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail), "details": [], "request_id": request_id(request)}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "The request contains invalid values.", "details": exc.errors(), "request_id": request_id(request)}})


def ok(data: Any, req: Request, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": data, "meta": meta or {}, "request_id": request_id(req)}


def paged(rows: list[Any], total: int, page: int, page_size: int, req: Request, transform: Any = services.public) -> dict[str, Any]:
    return ok([transform(row) for row in rows], req, {"page": page, "page_size": page_size, "total": total, "total_pages": (total + page_size - 1) // page_size})


ReadPrincipal = Annotated[Principal, Depends(require_scope("subscription:read", "subscription:admin", "subscription:billing", "subscription:support", "subscription:reports", "subscription:system"))]
BillingPrincipal = Annotated[Principal, Depends(require_scope("subscription:billing", "subscription:admin"))]
AdminPrincipal = Annotated[Principal, Depends(require_scope("subscription:admin"))]
ReportsPrincipal = Annotated[Principal, Depends(require_scope("subscription:reports", "subscription:admin"))]


@app.get("/health", tags=["Infrastructure"])
def health(request: Request) -> dict[str, Any]:
    return ok({"status": "ok"}, request)


@app.get("/ready", tags=["Infrastructure"])
def ready(request: Request, db: DBSession) -> dict[str, Any]:
    db.execute(select(1))
    return ok({"status": "ready", "database": "available"}, request)


def auth_payload(user: models.User) -> dict[str, Any]:
    return {"access_token": issue_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "scopes": user.scopes}}


@app.post("/api/v1/subscription/auth/signup", status_code=201, tags=["Authentication"])
def signup(payload: schemas.SignupRequest, request: Request, db: DBSession) -> dict[str, Any]:
    email = str(payload.email).lower()
    if db.scalar(select(models.User).where(func.lower(models.User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists")
    organization = db.get(models.Organization, settings.organization_id)
    if not organization:
        organization = models.Organization(id=settings.organization_id, name=settings.organization_name, slug="argo")
        db.add(organization)
        db.flush()
    member_count = db.scalar(select(func.count()).select_from(models.User).where(models.User.organization_id == organization.id)) or 0
    user = models.User(organization_id=organization.id, email=email, name=payload.name.strip(), password_hash=hash_password(payload.password), scopes=ADMIN_SCOPES if member_count == 0 else MEMBER_SCOPES)
    db.add(user)
    db.flush()
    principal = Principal(user_id=user.id, organization_id=user.organization_id, scopes=set(user.scopes), name=user.name)
    services.settings_for(db, principal)
    db.commit()
    return ok(auth_payload(user), request)


@app.post("/api/v1/subscription/auth/login", tags=["Authentication"])
def login(payload: schemas.LoginRequest, request: Request, db: DBSession) -> dict[str, Any]:
    email = str(payload.email).lower()
    user = db.scalar(select(models.User).where(func.lower(models.User.email) == email, models.User.status == "active"))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return ok(auth_payload(user), request)


@app.get("/api/v1/subscription/dashboard/summary", tags=["Dashboard"])
def dashboard(request: Request, db: DBSession, principal: ReadPrincipal) -> dict[str, Any]:
    org = principal.organization_id
    customers = db.scalar(select(func.count()).select_from(models.Customer).where(models.Customer.organization_id == org, models.Customer.status == "active")) or 0
    subscriptions = db.scalar(select(func.count()).select_from(models.Subscription).where(models.Subscription.organization_id == org, models.Subscription.status == "active")) or 0
    overdue = db.scalar(select(func.count()).select_from(models.Invoice).where(models.Invoice.organization_id == org, models.Invoice.status == "overdue")) or 0
    invoices = db.scalars(select(models.Invoice).where(models.Invoice.organization_id == org, models.Invoice.status != "void")).all()
    revenue = sum(services.invoice_amounts(db, invoice)["paid_minor"] for invoice in invoices)
    recent_subscriptions = db.scalars(select(models.Subscription).where(models.Subscription.organization_id == org).order_by(models.Subscription.created_at.desc()).limit(5)).all()
    recent_payments = db.scalars(select(models.Payment).where(models.Payment.organization_id == org).order_by(models.Payment.received_at.desc()).limit(5)).all()
    return ok({"metrics": {"active_customers": customers, "active_subscriptions": subscriptions, "collected_revenue_minor": revenue, "overdue_invoices": overdue}, "recent_subscriptions": [services.public(x) for x in recent_subscriptions], "recent_payments": [services.public(x) for x in recent_payments]}, request)


@app.get("/api/v1/subscription/customers", tags=["Customers"])
def customers(request: Request, db: DBSession, principal: ReadPrincipal, page: int = 1, page_size: int = 20, q: str | None = None) -> dict[str, Any]:
    rows, total = services.list_page(db, models.Customer, principal.organization_id, page, min(page_size, 100), q, models.Customer.display_name)
    return paged(rows, total, page, min(page_size, 100), request)


@app.post("/api/v1/subscription/customers", status_code=201, tags=["Customers"])
def create_customer(payload: schemas.CustomerCreate, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    settings_row = services.settings_for(db, principal)
    customer = models.Customer(organization_id=principal.organization_id, customer_code=services.reference(settings_row.customer_prefix, str(uuid.uuid4())), **payload.model_dump(), created_by=principal.user_id, updated_by=principal.user_id)
    db.add(customer)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "A customer with that email already exists") from exc
    services.activity(db, principal, "customer", customer.id, "created", request_id(request))
    db.commit()
    return ok(services.public(customer), request)


@app.get("/api/v1/subscription/customers/{customer_id}", tags=["Customers"])
def customer_detail(customer_id: str, request: Request, db: DBSession, principal: ReadPrincipal) -> dict[str, Any]:
    customer = services.one(db, models.Customer, principal.organization_id, customer_id)
    payload = services.public(customer)
    payload["subscriptions"] = [services.public(row) for row in db.scalars(select(models.Subscription).where(models.Subscription.customer_id == customer.id, models.Subscription.organization_id == principal.organization_id)).all()]
    return ok(payload, request)


@app.patch("/api/v1/subscription/customers/{customer_id}", tags=["Customers"])
def update_customer(customer_id: str, payload: schemas.CustomerUpdate, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    customer = services.one(db, models.Customer, principal.organization_id, customer_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, str(value).lower() if key == "email" and value else value)
    customer.updated_by = principal.user_id
    services.activity(db, principal, "customer", customer.id, "updated", request_id(request))
    db.commit()
    return ok(services.public(customer), request)


@app.post("/api/v1/subscription/customers/{customer_id}/archive", tags=["Customers"])
def archive_customer(customer_id: str, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    customer = services.one(db, models.Customer, principal.organization_id, customer_id)
    customer.status = "archived"
    customer.updated_by = principal.user_id
    services.activity(db, principal, "customer", customer.id, "archived", request_id(request))
    db.commit()
    return ok(services.public(customer), request)


@app.get("/api/v1/subscription/plans", tags=["Plans"])
def plans(request: Request, db: DBSession, principal: ReadPrincipal, page: int = 1, page_size: int = 50) -> dict[str, Any]:
    rows, total = services.list_page(db, models.Plan, principal.organization_id, page, min(page_size, 100))
    result = []
    for plan in rows:
        payload = services.public(plan)
        payload["prices"] = [services.public(price) for price in db.scalars(select(models.PlanPrice).where(models.PlanPrice.plan_id == plan.id, models.PlanPrice.organization_id == principal.organization_id)).all()]
        result.append(payload)
    return ok(result, request, {"page": page, "page_size": min(page_size, 100), "total": total})


@app.post("/api/v1/subscription/plans", status_code=201, tags=["Plans"])
def create_plan(payload: schemas.PlanCreate, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    plan = models.Plan(organization_id=principal.organization_id, **payload.model_dump(), created_by=principal.user_id, updated_by=principal.user_id)
    db.add(plan)
    try:
        db.flush()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, "A plan with that code already exists") from exc
    services.activity(db, principal, "plan", plan.id, "created", request_id(request))
    db.commit()
    return ok(services.public(plan), request)


@app.patch("/api/v1/subscription/plans/{plan_id}", tags=["Plans"])
def update_plan(plan_id: str, payload: schemas.PlanUpdate, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    plan = services.one(db, models.Plan, principal.organization_id, plan_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    plan.updated_by = principal.user_id
    services.activity(db, principal, "plan", plan.id, "updated", request_id(request))
    db.commit()
    return ok(services.public(plan), request)


@app.post("/api/v1/subscription/plans/{plan_id}/prices", status_code=201, tags=["Plans"])
def create_price(plan_id: str, payload: schemas.PriceCreate, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    plan = services.one(db, models.Plan, principal.organization_id, plan_id)
    if payload.is_default:
        for old in db.scalars(select(models.PlanPrice).where(models.PlanPrice.plan_id == plan.id, models.PlanPrice.organization_id == principal.organization_id, models.PlanPrice.billing_interval == payload.billing_interval, models.PlanPrice.currency == payload.currency)).all():
            old.is_default = False
    price = models.PlanPrice(organization_id=principal.organization_id, plan_id=plan.id, **payload.model_dump(), created_by=principal.user_id, updated_by=principal.user_id)
    db.add(price)
    db.flush()
    services.activity(db, principal, "plan_price", price.id, "created", request_id(request))
    db.commit()
    return ok(services.public(price), request)


@app.patch("/api/v1/subscription/plans/{plan_id}/status", tags=["Plans"])
def set_plan_status(plan_id: str, payload: schemas.PlanStatus, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    plan = services.one(db, models.Plan, principal.organization_id, plan_id)
    if payload.status == "active":
        usable = db.scalar(select(models.PlanPrice).where(models.PlanPrice.plan_id == plan.id, models.PlanPrice.organization_id == principal.organization_id, models.PlanPrice.status == "active"))
        if not usable:
            raise HTTPException(409, "An active plan requires an active price")
    plan.status = payload.status
    services.activity(db, principal, "plan", plan.id, f"status_{plan.status}", request_id(request))
    db.commit()
    return ok(services.public(plan), request)


@app.get("/api/v1/subscription/subscriptions", tags=["Subscriptions"])
def subscriptions(request: Request, db: DBSession, principal: ReadPrincipal, page: int = 1, page_size: int = 20, status_filter: str | None = None) -> dict[str, Any]:
    filters = [models.Subscription.organization_id == principal.organization_id]
    if status_filter:
        filters.append(models.Subscription.status == status_filter)
    total = db.scalar(select(func.count()).select_from(models.Subscription).where(*filters)) or 0
    rows = db.scalars(select(models.Subscription).where(*filters).order_by(models.Subscription.created_at.desc()).offset((page-1)*min(page_size,100)).limit(min(page_size,100))).all()
    return paged(list(rows), total, page, min(page_size, 100), request)


@app.post("/api/v1/subscription/subscriptions", status_code=201, tags=["Subscriptions"])
def create_subscription(payload: schemas.SubscriptionCreate, request: Request, db: DBSession, principal: BillingPrincipal, idempotency_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    replay = services.claim_idempotency(db, principal, "subscription.create", idempotency_key, payload.model_dump())
    if replay:
        return ok(replay, request, {"idempotent_replay": True})
    customer = services.one(db, models.Customer, principal.organization_id, payload.customer_id)
    if customer.status != "active":
        raise HTTPException(409, "Archived customers cannot receive a subscription")
    price = services.one(db, models.PlanPrice, principal.organization_id, payload.plan_price_id)
    plan = services.one(db, models.Plan, principal.organization_id, price.plan_id)
    if plan.status != "active" or price.status != "active":
        raise HTTPException(409, "Subscriptions require an active plan and price")
    existing = db.scalar(select(models.Subscription).where(models.Subscription.organization_id == principal.organization_id, models.Subscription.customer_id == customer.id, models.Subscription.plan_price_id == price.id, models.Subscription.status.in_(["trialing", "pending_payment", "active", "past_due", "suspended"])))
    if existing:
        raise HTTPException(409, "The customer already has an open subscription to this price")
    start, end = services.subscription_period(payload.starts_at, price)
    trial = payload.use_trial and plan.trial_days > 0
    subscription = models.Subscription(organization_id=principal.organization_id, subscription_number=services.reference(services.settings_for(db, principal).subscription_prefix, str(uuid.uuid4())), customer_id=customer.id, plan_id=plan.id, plan_price_id=price.id, status="trialing" if trial else "pending_payment", starts_at=payload.starts_at, trial_start_at=payload.starts_at if trial else None, trial_end_at=payload.starts_at + timedelta(days=plan.trial_days) if trial else None, current_period_start=None if trial else start, current_period_end=None if trial else end, next_billing_at=(payload.starts_at + timedelta(days=plan.trial_days)) if trial else start, auto_renew=payload.auto_renew, created_by=principal.user_id, updated_by=principal.user_id)
    db.add(subscription)
    db.flush()
    invoice = None
    if not trial:
        invoice = services.create_invoice_for_subscription(db, principal, subscription, payload.starts_at, request_id(request))
    services.event(db, principal, subscription, "created", None, "Subscription created", request_id(request))
    result = {"subscription": services.public(subscription), "invoice": services.invoice_public(db, invoice) if invoice else None}
    services.complete_idempotency(db, principal, "subscription.create", idempotency_key or "", result, "subscription", subscription.id)
    db.commit()
    return ok(result, request, {"idempotent_replay": False})


def versioned_subscription(subscription_id: str, payload: schemas.VersionedCommand, request: Request, db: DBSession, principal: BillingPrincipal, action: str) -> dict[str, Any]:
    subscription = services.one(db, models.Subscription, principal.organization_id, subscription_id)
    if subscription.version != payload.expected_version:
        raise HTTPException(409, f"Version conflict: expected {payload.expected_version}; current version is {subscription.version}")
    previous = subscription.status
    if action == "schedule_cancel":
        if previous not in {"trialing", "pending_payment", "active", "past_due"}:
            raise HTTPException(409, "This subscription cannot be scheduled for cancellation")
        subscription.cancel_at_period_end = True
    elif action == "cancel_now":
        if previous in {"cancelled", "expired"}:
            raise HTTPException(409, "This subscription has already ended")
        subscription.status, subscription.cancelled_at, subscription.ended_at, subscription.auto_renew = "cancelled", services.now(), services.now(), False
    elif action == "revoke_cancel":
        if not subscription.cancel_at_period_end:
            raise HTTPException(409, "No pending cancellation exists")
        subscription.cancel_at_period_end = False
    elif action == "resume":
        if previous != "suspended":
            raise HTTPException(409, "Only suspended subscriptions can be resumed")
        subscription.status = "active"
    subscription.cancellation_reason = payload.reason
    subscription.version += 1
    services.event(db, principal, subscription, action, previous, payload.reason, request_id(request))
    db.commit()
    return ok(services.public(subscription), request)


@app.post("/api/v1/subscription/subscriptions/{subscription_id}/schedule-cancellation", tags=["Subscriptions"])
def schedule_cancellation(subscription_id: str, payload: schemas.VersionedCommand, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    return versioned_subscription(subscription_id, payload, request, db, principal, "schedule_cancel")


@app.post("/api/v1/subscription/subscriptions/{subscription_id}/cancel-now", tags=["Subscriptions"])
def cancel_now(subscription_id: str, payload: schemas.VersionedCommand, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    return versioned_subscription(subscription_id, payload, request, db, principal, "cancel_now")


@app.post("/api/v1/subscription/subscriptions/{subscription_id}/revoke-cancellation", tags=["Subscriptions"])
def revoke_cancellation(subscription_id: str, payload: schemas.VersionedCommand, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    return versioned_subscription(subscription_id, payload, request, db, principal, "revoke_cancel")


@app.post("/api/v1/subscription/subscriptions/{subscription_id}/schedule-plan-change", tags=["Subscriptions"])
def schedule_plan_change(subscription_id: str, payload: schemas.PlanChangeCommand, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    subscription = services.one(db, models.Subscription, principal.organization_id, subscription_id)
    if subscription.version != payload.expected_version:
        raise HTTPException(409, "Subscription version conflict")
    target = services.one(db, models.PlanPrice, principal.organization_id, payload.target_plan_price_id)
    target_plan = services.one(db, models.Plan, principal.organization_id, target.plan_id)
    if target.status != "active" or target_plan.status != "active":
        raise HTTPException(409, "Target price must be active")
    subscription.pending_plan_id, subscription.pending_plan_price_id = target_plan.id, target.id
    subscription.plan_change_effective_at = subscription.current_period_end or subscription.trial_end_at
    subscription.version += 1
    services.event(db, principal, subscription, "plan_change_scheduled", subscription.status, payload.reason, request_id(request))
    db.commit()
    return ok(services.public(subscription), request)


@app.patch("/api/v1/subscription/subscriptions/{subscription_id}/auto-renew", tags=["Subscriptions"])
def update_auto_renew(subscription_id: str, payload: schemas.AutoRenewCommand, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    subscription = services.one(db, models.Subscription, principal.organization_id, subscription_id)
    if subscription.version != payload.expected_version:
        raise HTTPException(409, "Subscription version conflict")
    if subscription.status in {"cancelled", "expired"}:
        raise HTTPException(409, "Ended subscriptions cannot change auto renewal")
    subscription.auto_renew = payload.auto_renew
    subscription.version += 1
    subscription.updated_by = principal.user_id
    services.event(db, principal, subscription, "auto_renew_updated", subscription.status, f"Auto renewal set to {payload.auto_renew}", request_id(request))
    db.commit()
    return ok(services.public(subscription), request)


@app.get("/api/v1/subscription/invoices", tags=["Invoices"])
def invoices(request: Request, db: DBSession, principal: ReadPrincipal, page: int = 1, page_size: int = 20, status_filter: str | None = None) -> dict[str, Any]:
    filters = [models.Invoice.organization_id == principal.organization_id]
    if status_filter:
        filters.append(models.Invoice.status == status_filter)
    total = db.scalar(select(func.count()).select_from(models.Invoice).where(*filters)) or 0
    rows = db.scalars(select(models.Invoice).where(*filters).order_by(models.Invoice.created_at.desc()).offset((page-1)*min(page_size,100)).limit(min(page_size,100))).all()
    return paged(list(rows), total, page, min(page_size, 100), request, lambda x: services.invoice_public(db, x))


@app.get("/api/v1/subscription/invoices/{invoice_id}", tags=["Invoices"])
def invoice_detail(invoice_id: str, request: Request, db: DBSession, principal: ReadPrincipal) -> dict[str, Any]:
    invoice = services.one(db, models.Invoice, principal.organization_id, invoice_id)
    payload = services.invoice_public(db, invoice)
    payload["items"] = [services.public(item) for item in db.scalars(select(models.InvoiceItem).where(models.InvoiceItem.invoice_id == invoice.id, models.InvoiceItem.organization_id == principal.organization_id).order_by(models.InvoiceItem.line_number)).all()]
    return ok(payload, request)


@app.post("/api/v1/subscription/invoices", status_code=201, tags=["Invoices"])
def create_invoice(payload: schemas.InvoiceCreate, request: Request, db: DBSession, principal: BillingPrincipal, idempotency_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    replay = services.claim_idempotency(db, principal, "invoice.create", idempotency_key, payload.model_dump())
    if replay:
        return ok(replay, request, {"idempotent_replay": True})
    customer = services.one(db, models.Customer, principal.organization_id, payload.customer_id)
    if payload.subscription_id:
        subscription = services.one(db, models.Subscription, principal.organization_id, payload.subscription_id)
        if subscription.customer_id != customer.id:
            raise HTTPException(409, "Subscription does not belong to the customer")
    invoice = models.Invoice(organization_id=principal.organization_id, invoice_number=services.reference(services.settings_for(db, principal).invoice_prefix, str(uuid.uuid4())), customer_id=customer.id, subscription_id=payload.subscription_id, status="draft", issue_date=payload.issue_date, due_date=payload.due_date, service_period_start=payload.service_period_start, service_period_end=payload.service_period_end, currency=payload.currency, notes=payload.notes, created_by=principal.user_id, updated_by=principal.user_id)
    db.add(invoice); db.flush()
    for line, item in enumerate(payload.items, start=1):
        db.add(models.InvoiceItem(organization_id=principal.organization_id, invoice_id=invoice.id, line_number=line, **item.model_dump(), created_by=principal.user_id, updated_by=principal.user_id))
    db.flush()
    result = services.invoice_public(db, invoice)
    services.complete_idempotency(db, principal, "invoice.create", idempotency_key or "", result, "invoice", invoice.id)
    services.activity(db, principal, "invoice", invoice.id, "draft_created", request_id(request))
    db.commit()
    return ok(result, request)


@app.post("/api/v1/subscription/invoices/{invoice_id}/finalize", tags=["Invoices"])
def finalize_invoice(invoice_id: str, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    invoice = services.one(db, models.Invoice, principal.organization_id, invoice_id)
    if invoice.status != "draft":
        raise HTTPException(409, "Only draft invoices can be finalized")
    if services.invoice_amounts(db, invoice)["total_minor"] < 0:
        raise HTTPException(409, "An invoice total cannot be negative")
    invoice.finalized_at, invoice.status = services.now(), "open"
    services.sync_invoice(db, invoice)
    services.activity(db, principal, "invoice", invoice.id, "finalized", request_id(request))
    db.commit()
    return ok(services.invoice_public(db, invoice), request)


@app.post("/api/v1/subscription/invoices/{invoice_id}/void", tags=["Invoices"])
def void_invoice(invoice_id: str, payload: schemas.VersionedCommand, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    invoice = services.one(db, models.Invoice, principal.organization_id, invoice_id)
    if invoice.status not in {"draft", "open"} or services.invoice_amounts(db, invoice)["paid_minor"]:
        raise HTTPException(409, "Only unpaid draft or open invoices can be voided")
    invoice.status, invoice.voided_at, invoice.void_reason = "void", services.now(), payload.reason
    services.activity(db, principal, "invoice", invoice.id, "voided", request_id(request))
    db.commit()
    return ok(services.invoice_public(db, invoice), request)


@app.get("/api/v1/subscription/payments", tags=["Payments"])
def payments(request: Request, db: DBSession, principal: ReadPrincipal, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    rows, total = services.list_page(db, models.Payment, principal.organization_id, page, min(page_size, 100))
    def serializer(payment: models.Payment) -> dict[str, Any]:
        result = services.public(payment)
        allocated = db.scalar(select(func.coalesce(func.sum(models.PaymentAllocation.amount_minor), 0)).where(models.PaymentAllocation.payment_id == payment.id)) or 0
        result["unallocated_minor"] = payment.amount_minor - allocated
        return result
    return paged(rows, total, page, min(page_size, 100), request, serializer)


def make_payment(payload: schemas.PaymentCreate, request: Request, db: DBSession, principal: BillingPrincipal, attempt_id: str | None = None) -> models.Payment:
    customer = services.one(db, models.Customer, principal.organization_id, payload.customer_id)
    payment = models.Payment(organization_id=principal.organization_id, payment_reference=services.reference(services.settings_for(db, principal).payment_prefix, str(uuid.uuid4())), customer_id=customer.id, payment_attempt_id=attempt_id, payment_method=payload.payment_method, amount_minor=payload.amount_minor, currency=payload.currency, received_at=payload.received_at or services.now(), external_reference=payload.external_reference, notes=payload.notes, created_by=principal.user_id, updated_by=principal.user_id)
    db.add(payment); db.flush()
    services.allocate(db, principal, payment, [a.model_dump() for a in payload.allocations], request_id(request))
    services.activity(db, principal, "payment", payment.id, "recorded", request_id(request))
    return payment


@app.post("/api/v1/subscription/payments", status_code=201, tags=["Payments"])
def record_payment(payload: schemas.PaymentCreate, request: Request, db: DBSession, principal: BillingPrincipal, idempotency_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    replay = services.claim_idempotency(db, principal, "payment.create", idempotency_key, payload.model_dump())
    if replay:
        return ok(replay, request, {"idempotent_replay": True})
    payment = make_payment(payload, request, db, principal)
    result = services.public(payment)
    services.complete_idempotency(db, principal, "payment.create", idempotency_key or "", result, "payment", payment.id)
    db.commit()
    return ok(result, request)


@app.post("/api/v1/subscription/payment-attempts", status_code=201, tags=["Payment Attempts"])
def create_attempt(payload: schemas.PaymentAttemptCreate, request: Request, db: DBSession, principal: BillingPrincipal, idempotency_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    replay = services.claim_idempotency(db, principal, "payment_attempt.create", idempotency_key, payload.model_dump())
    if replay:
        return ok(replay, request, {"idempotent_replay": True})
    invoice = services.one(db, models.Invoice, principal.organization_id, payload.invoice_id)
    if invoice.currency != payload.currency or payload.amount_minor > services.invoice_amounts(db, invoice)["balance_minor"]:
        raise HTTPException(409, "Attempt must match the outstanding invoice balance and currency")
    attempt = models.PaymentAttempt(organization_id=principal.organization_id, attempt_reference=services.reference("ATT", str(uuid.uuid4())), invoice_id=invoice.id, provider=payload.provider, idempotency_key=idempotency_key or "", request_hash="request-hash", amount_minor=payload.amount_minor, currency=payload.currency, created_by=principal.user_id, updated_by=principal.user_id)
    db.add(attempt); db.flush()
    result = services.public(attempt)
    services.complete_idempotency(db, principal, "payment_attempt.create", idempotency_key or "", result, "payment_attempt", attempt.id)
    db.commit()
    return ok(result, request)


@app.post("/api/v1/subscription/payment-attempts/{attempt_id}/complete", tags=["Payment Attempts"])
def complete_payment_attempt(attempt_id: str, payload: schemas.CompletePaymentAttempt, request: Request, db: DBSession, principal: BillingPrincipal, idempotency_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    attempt = services.one(db, models.PaymentAttempt, principal.organization_id, attempt_id)
    if attempt.status != "pending":
        raise HTTPException(409, "Only pending attempts can be completed")
    invoice = services.one(db, models.Invoice, principal.organization_id, attempt.invoice_id)
    allocations = payload.allocations or [schemas.AllocationInput(invoice_id=invoice.id, amount_minor=attempt.amount_minor)]
    payment = make_payment(schemas.PaymentCreate(customer_id=invoice.customer_id, payment_method=payload.payment_method, amount_minor=attempt.amount_minor, currency=attempt.currency, received_at=payload.received_at, external_reference=payload.external_reference, allocations=allocations), request, db, principal, attempt.id)
    attempt.status, attempt.completed_at = "succeeded", services.now()
    db.commit()
    return ok({"attempt": services.public(attempt), "payment": services.public(payment)}, request)


@app.get("/api/v1/subscription/notifications", tags=["Notifications"])
def notifications(request: Request, db: DBSession, principal: ReadPrincipal, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    rows, total = services.list_page(db, models.Notification, principal.organization_id, page, min(page_size, 100))
    return paged(rows, total, page, min(page_size, 100), request)


@app.post("/api/v1/subscription/notifications", status_code=201, tags=["Notifications"])
def create_notification(payload: schemas.NotificationCreate, request: Request, db: DBSession, principal: BillingPrincipal) -> dict[str, Any]:
    values = payload.model_dump()
    values["recipient_user_id"] = payload.recipient_user_id or principal.user_id
    notice = models.Notification(organization_id=principal.organization_id, **values, channel="in_app", status="sent", created_by=principal.user_id, updated_by=principal.user_id)
    db.add(notice); db.commit()
    return ok(services.public(notice), request)


@app.post("/api/v1/subscription/notifications/{notification_id}/mark-read", tags=["Notifications"])
def mark_read(notification_id: str, request: Request, db: DBSession, principal: ReadPrincipal) -> dict[str, Any]:
    notice = services.one(db, models.Notification, principal.organization_id, notification_id)
    if notice.recipient_user_id not in {None, principal.user_id} and "subscription:admin" not in principal.scopes:
        raise HTTPException(403, "This notification belongs to another recipient")
    notice.status, notice.read_at = "read", services.now()
    db.commit()
    return ok(services.public(notice), request)


@app.get("/api/v1/subscription/settings", tags=["Settings"])
def get_settings(request: Request, db: DBSession, principal: ReadPrincipal) -> dict[str, Any]:
    return ok(services.public(services.settings_for(db, principal)), request)


@app.patch("/api/v1/subscription/settings", tags=["Settings"])
def update_settings(payload: schemas.SettingsUpdate, request: Request, db: DBSession, principal: AdminPrincipal) -> dict[str, Any]:
    settings_row = services.settings_for(db, principal)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings_row, key, value)
    settings_row.updated_by = principal.user_id
    services.activity(db, principal, "settings", settings_row.id, "updated", request_id(request))
    db.commit()
    return ok(services.public(settings_row), request)


@app.get("/api/v1/subscription/reports/mrr", tags=["Reports"])
def report_mrr(request: Request, db: DBSession, principal: ReportsPrincipal, currency: str = "PHP") -> dict[str, Any]:
    subscriptions = db.scalars(select(models.Subscription).where(models.Subscription.organization_id == principal.organization_id, models.Subscription.status.in_(["active", "trialing", "past_due", "suspended"]))).all()
    mrr = at_risk = 0
    for sub in subscriptions:
        price = services.one(db, models.PlanPrice, principal.organization_id, sub.plan_price_id)
        if price.currency != currency:
            continue
        value = price.unit_amount_minor // 12 if price.billing_interval == "year" else price.unit_amount_minor
        if sub.status in {"past_due", "suspended"}:
            at_risk += value
        else:
            mrr += value
    return ok({"as_of": datetime.now(timezone.utc).date().isoformat(), "currency": currency, "mrr_minor": mrr, "at_risk_mrr_minor": at_risk, "active_subscription_count": len(subscriptions), "calculation": "active monthly amount + annual amount / 12"}, request)


@app.get("/api/v1/subscription/reports/collected-revenue", tags=["Reports"])
def collected_revenue(request: Request, db: DBSession, principal: ReportsPrincipal, currency: str = "PHP") -> dict[str, Any]:
    total = db.scalar(select(func.coalesce(func.sum(models.PaymentAllocation.amount_minor), 0)).join(models.Payment).where(models.Payment.organization_id == principal.organization_id, models.Payment.status == "completed", models.Payment.currency == currency)) or 0
    return ok({"currency": currency, "total_minor": int(total)}, request)


@app.get("/api/v1/subscription/activity-logs", tags=["Activity"])
def activity_logs(request: Request, db: DBSession, principal: AdminPrincipal, page: int = 1, page_size: int = 50) -> dict[str, Any]:
    rows, total = services.list_page(db, models.ActivityLog, principal.organization_id, page, min(page_size, 100))
    return paged(rows, total, page, min(page_size, 100), request)


@app.post("/api/v1/subscription/maintenance/process-due", tags=["Maintenance"])
def process_due(payload: schemas.DueProcess, request: Request, db: DBSession, principal: Annotated[Principal, Depends(require_scope("subscription:admin", "subscription:system"))], idempotency_key: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    replay = services.claim_idempotency(db, principal, "maintenance.process_due", idempotency_key, payload.model_dump())
    if replay:
        return ok(replay, request, {"idempotent_replay": True})
    as_of = payload.as_of or services.now()
    result = {"processed": 0, "skipped": 0, "failed": 0, "created_invoices": 0, "marked_overdue": 0, "activated": 0, "suspended": 0, "cancelled": 0, "has_more": False}
    due = db.scalars(select(models.Subscription).where(models.Subscription.organization_id == principal.organization_id, models.Subscription.next_billing_at.is_not(None), models.Subscription.next_billing_at <= as_of, models.Subscription.status.in_(["trialing", "active", "pending_payment", "past_due", "suspended"])).order_by(models.Subscription.next_billing_at).limit(payload.batch_size + 1)).all()
    result["has_more"] = len(due) > payload.batch_size
    for subscription in due[:payload.batch_size]:
        result["processed"] += 1
        previous = subscription.status
        if subscription.status == "trialing":
            subscription.status = "pending_payment"
            price = services.one(db, models.PlanPrice, principal.organization_id, subscription.plan_price_id)
            start, end = services.subscription_period(subscription.trial_end_at or as_of, price)
            subscription.current_period_start, subscription.current_period_end, subscription.next_billing_at = start, end, start
            if not payload.dry_run:
                services.create_invoice_for_subscription(db, principal, subscription, as_of, request_id(request)); result["created_invoices"] += 1
        elif subscription.cancel_at_period_end:
            subscription.status, subscription.ended_at, subscription.auto_renew = "cancelled", as_of, False; result["cancelled"] += 1
        elif subscription.auto_renew:
            if subscription.pending_plan_price_id:
                subscription.plan_id, subscription.plan_price_id = subscription.pending_plan_id or subscription.plan_id, subscription.pending_plan_price_id
                subscription.pending_plan_id = subscription.pending_plan_price_id = None
            price = services.one(db, models.PlanPrice, principal.organization_id, subscription.plan_price_id)
            start, end = services.subscription_period(subscription.current_period_end or as_of, price)
            subscription.current_period_start, subscription.current_period_end, subscription.next_billing_at = start, end, end
            subscription.status = "pending_payment"
            if not payload.dry_run:
                services.create_invoice_for_subscription(db, principal, subscription, as_of, request_id(request)); result["created_invoices"] += 1
        subscription.version += 1
        if not payload.dry_run:
            services.event(db, principal, subscription, "due_processed", previous, None, request_id(request))
    for invoice in db.scalars(select(models.Invoice).where(models.Invoice.organization_id == principal.organization_id, models.Invoice.status == "open", models.Invoice.due_date < as_of.date())).all():
        if not payload.dry_run:
            invoice.status = "overdue"
        result["marked_overdue"] += 1
    if payload.dry_run:
        db.rollback()
    else:
        services.complete_idempotency(db, principal, "maintenance.process_due", idempotency_key or "", result, "maintenance_run", request_id(request), 200)
        db.commit()
    return ok(result, request, {"dry_run": payload.dry_run, "idempotent_replay": False})
