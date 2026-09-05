import os

os.environ["DATABASE_URL"] = "sqlite:///./test_subscription.db"

from fastapi.testclient import TestClient

from app.config import get_settings
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
    subscriptions = client.get("/api/v1/subscription/subscriptions", headers=headers).json()["data"]
    assert subscriptions[0]["status"] == "active"
    assert subscriptions[0]["next_billing_at"] == subscriptions[0]["current_period_end"]


def test_existing_payment_credit_can_be_allocated_once_and_sync_subscription() -> None:
    client, headers = client_and_token()
    customer = client.post("/api/v1/subscription/customers", headers=headers, json={"display_name": "Credit Customer"}).json()["data"]
    _, price_id = active_price(client, headers)
    created = client.post("/api/v1/subscription/subscriptions", headers={**headers, "Idempotency-Key": "credit-subscription"}, json={"customer_id": customer["id"], "plan_price_id": price_id, "starts_at": "2026-07-30T00:00:00Z", "use_trial": False}).json()["data"]
    invoice = created["invoice"]
    payment = client.post("/api/v1/subscription/payments", headers={**headers, "Idempotency-Key": "credit-payment"}, json={"customer_id": customer["id"], "payment_method": "manual_bank", "amount_minor": invoice["amounts"]["total_minor"], "currency": "PHP", "allocations": []}).json()["data"]
    assert payment["unallocated_minor"] == invoice["amounts"]["total_minor"]
    allocation_headers = {**headers, "Idempotency-Key": "credit-allocation"}
    allocated = client.post(f"/api/v1/subscription/payments/{payment['id']}/allocate", headers=allocation_headers, json={"allocations": [{"invoice_id": invoice["id"], "amount_minor": invoice["amounts"]["total_minor"]}]})
    assert allocated.status_code == 200
    assert allocated.json()["data"]["unallocated_minor"] == 0
    replay = client.post(f"/api/v1/subscription/payments/{payment['id']}/allocate", headers=allocation_headers, json={"allocations": [{"invoice_id": invoice["id"], "amount_minor": invoice["amounts"]["total_minor"]}]})
    assert replay.status_code == 200 and replay.json()["meta"]["idempotent_replay"] is True
    invoice_after = client.get(f"/api/v1/subscription/invoices/{invoice['id']}", headers=headers).json()["data"]
    subscription_after = client.get("/api/v1/subscription/subscriptions", headers=headers).json()["data"][0]
    assert invoice_after["status"] == "paid" and invoice_after["amounts"]["balance_minor"] == 0
    assert subscription_after["status"] == "active"


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
    assert signup.json()["data"]["user"]["role"] == "org_admin"
    login = client.post("/api/v1/subscription/auth/login", json={"email": "live@example.com", "password": "LivePass123!"})
    assert login.status_code == 200
    assert login.json()["data"]["user"]["email"] == "live@example.com"


def test_public_catalog_is_available_without_authentication() -> None:
    client, headers = client_and_token()
    active_price(client, headers)
    response = client.get("/api/v1/subscription/public/plans")
    assert response.status_code == 200
    assert response.json()["data"][0]["prices"][0]["list_amount_minor"] is not None


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


def test_plan_price_edit_and_safe_remove_rules() -> None:
    client, headers = client_and_token()
    plan_id, price_id = active_price(client, headers)

    edited_plan = client.patch(f"/api/v1/subscription/plans/{plan_id}", headers=headers, json={"display_order": 4})
    assert edited_plan.status_code == 200 and edited_plan.json()["data"]["display_order"] == 4
    edited_price = client.patch(f"/api/v1/subscription/plans/{plan_id}/prices/{price_id}", headers=headers, json={"list_amount_minor": 22500, "unit_amount_minor": 22500, "discount_bps": 0})
    assert edited_price.status_code == 200 and edited_price.json()["data"]["unit_amount_minor"] == 22500
    annual = client.post(f"/api/v1/subscription/plans/{plan_id}/prices", headers=headers, json={"price_code": "START-YEAR", "billing_interval": "year", "currency": "PHP", "list_amount_minor": 270000, "unit_amount_minor": 229500, "discount_bps": 1500, "is_default": True})
    assert annual.status_code == 201 and annual.json()["data"]["discount_bps"] == 1500
    invalid_discount = client.post(f"/api/v1/subscription/plans/{plan_id}/prices", headers=headers, json={"price_code": "START-YEAR-BAD", "billing_interval": "year", "currency": "PHP", "list_amount_minor": 270000, "unit_amount_minor": 250000, "discount_bps": 1500})
    assert invalid_discount.status_code == 422

    removed_unused_plan = client.post("/api/v1/subscription/plans", headers=headers, json={"plan_code": "DRAFT", "name": "Draft Plan"})
    assert removed_unused_plan.status_code == 201
    draft_id = removed_unused_plan.json()["data"]["id"]
    removed_draft = client.delete(f"/api/v1/subscription/plans/{draft_id}", headers=headers)
    assert removed_draft.status_code == 200 and removed_draft.json()["data"]["action"] == "deleted"

    customer = client.post("/api/v1/subscription/customers", headers=headers, json={"display_name": "Plan Owner"}).json()["data"]
    subscription = client.post(
        "/api/v1/subscription/subscriptions",
        headers={**headers, "Idempotency-Key": "plan-remove-subscription"},
        json={"customer_id": customer["id"], "plan_price_id": price_id, "starts_at": "2026-08-01T00:00:00Z", "use_trial": False},
    )
    assert subscription.status_code == 201
    immutable_price = client.patch(f"/api/v1/subscription/plans/{plan_id}/prices/{price_id}", headers=headers, json={"unit_amount_minor": 25000})
    assert immutable_price.status_code == 409
    removed_used_plan = client.delete(f"/api/v1/subscription/plans/{plan_id}", headers=headers)
    assert removed_used_plan.status_code == 200 and removed_used_plan.json()["data"]["action"] == "archived"


def test_read_only_user_is_scoped_to_matching_customer() -> None:
    client, admin_headers = client_and_token()
    own_customer = client.post("/api/v1/subscription/customers", headers=admin_headers, json={"display_name": "Portal User", "email": "viewer@example.com"}).json()["data"]
    other_customer = client.post("/api/v1/subscription/customers", headers=admin_headers, json={"display_name": "Private Customer", "email": "other@example.com"}).json()["data"]
    _, price_id = active_price(client, admin_headers)
    created = client.post(
        "/api/v1/subscription/subscriptions",
        headers={**admin_headers, "Idempotency-Key": "portal-user-subscription"},
        json={"customer_id": own_customer["id"], "plan_price_id": price_id, "starts_at": "2026-08-01T00:00:00Z", "use_trial": False},
    )
    assert created.status_code == 201
    signup = client.post("/api/v1/subscription/auth/signup", json={"name": "Portal User", "email": "viewer@example.com", "password": "LivePass123!"})
    assert signup.status_code == 201 and signup.json()["data"]["user"]["role"] == "user"
    user_headers = {"Authorization": f"Bearer {signup.json()['data']['access_token']}"}

    customers = client.get("/api/v1/subscription/customers?page_size=100", headers=user_headers)
    assert customers.status_code == 200 and [row["id"] for row in customers.json()["data"]] == [own_customer["id"]]
    assert client.get(f"/api/v1/subscription/customers/{other_customer['id']}", headers=user_headers).status_code == 404
    assert len(client.get("/api/v1/subscription/subscriptions", headers=user_headers).json()["data"]) == 1
    assert len(client.get("/api/v1/subscription/invoices", headers=user_headers).json()["data"]) == 1
    assert len(client.get("/api/v1/subscription/plans", headers=user_headers).json()["data"]) == 1
    subscription = client.get("/api/v1/subscription/subscriptions", headers=user_headers).json()["data"][0]
    auto_renew = client.patch(f"/api/v1/subscription/me/subscriptions/{subscription['id']}/auto-renew", headers=user_headers, json={"expected_version": subscription["version"], "auto_renew": False})
    assert auto_renew.status_code == 200 and auto_renew.json()["data"]["auto_renew"] is False
    scheduled = client.post(f"/api/v1/subscription/me/subscriptions/{subscription['id']}/schedule-cancellation", headers=user_headers, json={"expected_version": auto_renew.json()["data"]["version"], "reason": "Subscriber request"})
    assert scheduled.status_code == 200 and scheduled.json()["data"]["cancel_at_period_end"] is True
    revoked = client.post(f"/api/v1/subscription/me/subscriptions/{subscription['id']}/revoke-cancellation", headers=user_headers, json={"expected_version": scheduled.json()["data"]["version"], "reason": "Subscriber changed their mind"})
    assert revoked.status_code == 200 and revoked.json()["data"]["cancel_at_period_end"] is False
    assert client.post("/api/v1/subscription/auth/logout", headers=user_headers).status_code == 200
    assert client.get("/api/v1/subscription/dashboard/summary", headers=user_headers).status_code == 401


def test_feature_catalog_and_plan_feature_assignment() -> None:
    client, headers = client_and_token()
    active_price(client, headers)
    plan_id = client.get("/api/v1/subscription/plans", headers=headers).json()["data"][0]["id"]
    created = client.post("/api/v1/subscription/features", headers=headers, json={"feature_code": "PRIORITY_SUPPORT", "name": "Priority support", "value_type": "boolean"})
    assert created.status_code == 201
    feature = created.json()["data"]
    duplicate = client.post("/api/v1/subscription/features", headers=headers, json={"feature_code": "PRIORITY_SUPPORT", "name": "Duplicate", "value_type": "boolean"})
    assert duplicate.status_code == 409
    assigned = client.put(f"/api/v1/subscription/plans/{plan_id}/features", headers=headers, json={"feature_id": feature["id"], "is_included": True, "value_boolean": True})
    assert assigned.status_code == 200 and assigned.json()["data"][0]["feature"]["feature_code"] == "PRIORITY_SUPPORT"
    plan = client.get("/api/v1/subscription/plans", headers=headers).json()["data"][0]
    assert plan["features"][0]["feature"]["name"] == "Priority support"
    removed = client.delete(f"/api/v1/subscription/features/{feature['id']}", headers=headers)
    assert removed.status_code == 200 and removed.json()["data"]["action"] == "archived"


def test_configured_super_admin_can_read_platform_aggregates() -> None:
    previous = os.environ.get("SUPER_ADMIN_EMAILS")
    os.environ["SUPER_ADMIN_EMAILS"] = "platform@example.com"
    get_settings.cache_clear()
    try:
        client, _ = client_and_token()
        signup = client.post("/api/v1/subscription/auth/signup", json={"name": "Platform Owner", "email": "platform@example.com", "password": "LivePass123!"})
        assert signup.status_code == 201 and signup.json()["data"]["user"]["role"] == "super_admin"
        headers = {"Authorization": f"Bearer {signup.json()['data']['access_token']}"}
        summary = client.get("/api/v1/subscription/platform/summary", headers=headers)
        assert summary.status_code == 200 and {"total_customers", "active_sessions", "recent_activity"}.issubset(summary.json()["data"])
        assert client.get("/api/v1/subscription/platform/organizations", headers=headers).status_code == 200
        assert client.get("/api/v1/subscription/platform/reports", headers=headers).status_code == 200
    finally:
        if previous is None:
            os.environ.pop("SUPER_ADMIN_EMAILS", None)
        else:
            os.environ["SUPER_ADMIN_EMAILS"] = previous
        get_settings.cache_clear()


def test_organization_admin_can_assign_roles_without_removing_last_admin() -> None:
    client, admin_headers = client_and_token()
    signup = client.post("/api/v1/subscription/auth/signup", json={"name": "Managed User", "email": "managed@example.com", "password": "LivePass123!"})
    assert signup.status_code == 201
    user_id = signup.json()["data"]["user"]["id"]
    listed = client.get("/api/v1/subscription/users", headers=admin_headers)
    assert listed.status_code == 200 and any(item["id"] == user_id and item["role"] == "user" for item in listed.json()["data"])
    promoted = client.patch(f"/api/v1/subscription/users/{user_id}/role", headers=admin_headers, json={"role": "org_admin"})
    assert promoted.status_code == 200 and promoted.json()["data"]["role"] == "org_admin"
    demoted = client.patch(f"/api/v1/subscription/users/{user_id}/role", headers=admin_headers, json={"role": "user"})
    assert demoted.status_code == 200 and demoted.json()["data"]["role"] == "user"
    protected = client.patch(f"/api/v1/subscription/users/{user_id}/status", headers=admin_headers, json={"status": "suspended"})
    assert protected.status_code == 200 and protected.json()["data"]["status"] == "suspended"
    self_change = client.patch(f"/api/v1/subscription/users/{signup.json()['data']['user']['id']}/role", headers={"Authorization": f"Bearer {signup.json()['data']['access_token']}"}, json={"role": "org_admin"})
    assert self_change.status_code == 401
