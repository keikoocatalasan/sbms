import os

os.environ["DATABASE_URL"] = "sqlite:///./test_subscription.db"

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


def client_and_token() -> tuple[TestClient, dict[str, str]]:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client = TestClient(app)
    response = client.post("/api/v1/subscription/auth/signup", json={"name": "Test Administrator", "email": "admin@example.com", "password": "LivePass123!"})
    assert response.status_code == 201
    return client, {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def active_price(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    plan = client.post("/api/v1/subscription/plans", headers=headers, json={"plan_code": "START", "name": "Starter", "trial_days": 7}).json()["data"]
    price = client.post(f"/api/v1/subscription/plans/{plan['id']}/prices", headers=headers, json={"price_code": "START-MONTH", "billing_interval": "month", "unit_amount_minor": 19900}).json()["data"]
    assert client.patch(f"/api/v1/subscription/plans/{plan['id']}/status", headers=headers, json={"status": "active"}).status_code == 200
    return plan["id"], price["id"]


def test_subscription_to_payment_activation_and_idempotency() -> None:
    client, headers = client_and_token()
    customer = client.post("/api/v1/subscription/customers", headers=headers, json={"display_name": "Acme", "email": "a@acme.example"}).json()["data"]
    _, price_id = active_price(client, headers)
    payload = {"customer_id": customer["id"], "plan_price_id": price_id, "starts_at": "2026-07-26T00:00:00Z", "use_trial": False}
    response = client.post("/api/v1/subscription/subscriptions", headers={**headers, "Idempotency-Key": "subscription-1"}, json=payload)
    assert response.status_code == 201
    first = response.json()["data"]
    replay = client.post("/api/v1/subscription/subscriptions", headers={**headers, "Idempotency-Key": "subscription-1"}, json=payload)
    assert replay.status_code == 201 and replay.json()["meta"]["idempotent_replay"] is True
    invoice = first["invoice"]
    payment = client.post("/api/v1/subscription/payments", headers={**headers, "Idempotency-Key": "payment-1"}, json={"customer_id": customer["id"], "payment_method": "manual_bank", "amount_minor": invoice["amounts"]["total_minor"], "currency": "PHP", "allocations": [{"invoice_id": invoice["id"], "amount_minor": invoice["amounts"]["total_minor"]}]})
    assert payment.status_code == 201
    invoices = client.get("/api/v1/subscription/invoices", headers=headers).json()["data"]
    assert invoices[0]["status"] == "paid"


def test_missing_authentication_is_structured() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/subscription/customers")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_signup_and_live_login() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    client = TestClient(app)
    signup = client.post("/api/v1/subscription/auth/signup", json={"name": "Live User", "email": "live@example.com", "password": "LivePass123!"})
    assert signup.status_code == 201
    assert "subscription:admin" in signup.json()["data"]["user"]["scopes"]
    login = client.post("/api/v1/subscription/auth/login", json={"email": "live@example.com", "password": "LivePass123!"})
    assert login.status_code == 200
    assert login.json()["data"]["user"]["email"] == "live@example.com"


def test_plan_edit_invoice_detail_and_auto_renew() -> None:
    client, headers = client_and_token()
    customer = client.post("/api/v1/subscription/customers", headers=headers, json={"display_name": "Lifecycle Customer", "email": "lifecycle@example.com"}).json()["data"]
    plan_id, price_id = active_price(client, headers)
    edited = client.patch(f"/api/v1/subscription/plans/{plan_id}", headers=headers, json={"name": "Starter Plus", "trial_days": 14})
    assert edited.status_code == 200
    assert edited.json()["data"]["name"] == "Starter Plus"
    created = client.post("/api/v1/subscription/subscriptions", headers={**headers, "Idempotency-Key": "subscription-detail"}, json={"customer_id": customer["id"], "plan_price_id": price_id, "starts_at": "2026-07-30T00:00:00Z", "use_trial": False}).json()["data"]
    subscription = created["subscription"]
    renewal = client.patch(f"/api/v1/subscription/subscriptions/{subscription['id']}/auto-renew", headers=headers, json={"expected_version": subscription["version"], "auto_renew": False})
    assert renewal.status_code == 200
    assert renewal.json()["data"]["auto_renew"] is False
    detail = client.get(f"/api/v1/subscription/invoices/{created['invoice']['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["items"][0]["description"].startswith("Subscription renewal")


def test_scheduled_cancellation_can_be_revoked() -> None:
    client, headers = client_and_token()
    customer = client.post("/api/v1/subscription/customers", headers=headers, json={"display_name": "Cancel Customer"}).json()["data"]
    _, price_id = active_price(client, headers)
    subscription = client.post("/api/v1/subscription/subscriptions", headers={**headers, "Idempotency-Key": "subscription-cancel"}, json={"customer_id": customer["id"], "plan_price_id": price_id, "starts_at": "2026-07-30T00:00:00Z", "use_trial": True}).json()["data"]["subscription"]
    scheduled = client.post(f"/api/v1/subscription/subscriptions/{subscription['id']}/schedule-cancellation", headers=headers, json={"expected_version": subscription["version"], "reason": "Customer request"})
    assert scheduled.status_code == 200
    assert scheduled.json()["data"]["cancel_at_period_end"] is True
    revoked = client.post(f"/api/v1/subscription/subscriptions/{subscription['id']}/revoke-cancellation", headers=headers, json={"expected_version": scheduled.json()["data"]["version"], "reason": "Customer retained"})
    assert revoked.status_code == 200
    assert revoked.json()["data"]["cancel_at_period_end"] is False


def test_billing_role_is_limited_to_billing_workflows() -> None:
    client, _ = client_and_token()
    signup = client.post("/api/v1/subscription/auth/signup", json={"name": "Read Only", "email": "reader@example.com", "password": "LivePass123!"})
    billing_headers = {"Authorization": f"Bearer {signup.json()['data']['access_token']}"}
    assert client.get("/api/v1/subscription/settings", headers=billing_headers).status_code == 200
    assert client.post("/api/v1/subscription/customers", headers=billing_headers, json={"display_name": "Billing Managed"}).status_code == 403
    assert client.patch("/api/v1/subscription/settings", headers=billing_headers, json={"invoice_due_days": 10}).status_code == 403
    assert client.post("/api/v1/subscription/plans", headers=billing_headers, json={"plan_code": "DENIED", "name": "Denied"}).status_code == 403
    assert client.get("/api/v1/subscription/reports/mrr", headers=billing_headers).status_code == 403


def test_notification_create_and_mark_read() -> None:
    client, headers = client_and_token()
    created = client.post("/api/v1/subscription/notifications", headers=headers, json={"notification_type": "manual_notice", "title": "QA notice", "body": "Verify notification lifecycle"})
    assert created.status_code == 201
    notice = created.json()["data"]
    assert notice["read_at"] is None
    marked = client.post(f"/api/v1/subscription/notifications/{notice['id']}/mark-read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["data"]["read_at"] is not None


def test_void_invoice_has_no_collectible_balance() -> None:
    client, headers = client_and_token()
    customer = client.post("/api/v1/subscription/customers", headers=headers, json={"display_name": "Void Balance Test", "email": "void.balance@example.com"}).json()["data"]
    created = client.post("/api/v1/subscription/invoices", headers={**headers, "Idempotency-Key": "void-balance-invoice"}, json={"customer_id": customer["id"], "currency": "PHP", "due_date": "2027-01-01", "items": [{"description": "Voidable charge", "quantity": 1, "unit_amount_minor": 4200}]}).json()["data"]
    response = client.post(f"/api/v1/subscription/invoices/{created['id']}/void", headers=headers, json={"expected_version": 1, "reason": "Regression test"})
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "void"
    assert response.json()["data"]["amounts"] == {"total_minor": 4200, "paid_minor": 0, "balance_minor": 0}
