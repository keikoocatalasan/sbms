-- Remove only the deterministic showcase-12m-v1 dataset.
-- Run only after confirming the dataset marker and taking a backup.
BEGIN;
DO $$
DECLARE
    v_org text := '00000000-0000-0000-0000-000000000001';
    v_marker text := 'showcase-12m-v1';
BEGIN
    DELETE FROM subscription_payment_allocations a
    USING subscription_payments p
    WHERE a.payment_id = p.id AND p.organization_id = v_org AND p.notes LIKE '%' || v_marker || '%';
    DELETE FROM subscription_payments WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%';
    DELETE FROM subscription_payment_attempts WHERE organization_id = v_org AND idempotency_key LIKE v_marker || '%';
    DELETE FROM subscription_invoice_items i USING subscription_invoices inv WHERE i.invoice_id = inv.id AND inv.organization_id = v_org AND inv.notes LIKE '%' || v_marker || '%';
    DELETE FROM subscription_invoices WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%';
    DELETE FROM subscription_notifications WHERE organization_id = v_org AND body LIKE '%' || v_marker || '%';
    DELETE FROM subscription_activity_logs WHERE organization_id = v_org AND details_json ->> 'dataset' = v_marker;
    DELETE FROM subscription_subscription_events WHERE organization_id = v_org AND (reason LIKE '%' || v_marker || '%' OR metadata_json ->> 'dataset' = v_marker);
    DELETE FROM subscription_subscriptions WHERE organization_id = v_org AND subscription_number LIKE 'SC-SUB-%';
    DELETE FROM subscription_customer_addresses WHERE organization_id = v_org AND customer_id IN (SELECT id FROM subscription_customers WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%');
    DELETE FROM subscription_customers WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%';
    DELETE FROM subscription_plan_features WHERE organization_id = v_org AND plan_id IN (SELECT id FROM subscription_plans WHERE organization_id = v_org AND description LIKE '%' || v_marker || '%');
    DELETE FROM subscription_features WHERE organization_id = v_org AND description LIKE '%' || v_marker || '%';
    DELETE FROM subscription_plan_prices WHERE organization_id = v_org AND price_code LIKE 'SHOWCASE_%';
    DELETE FROM subscription_plans WHERE organization_id = v_org AND description LIKE '%' || v_marker || '%';
    DELETE FROM subscription_idempotency_keys WHERE organization_id = v_org AND operation = 'showcase.import' AND idempotency_key = v_marker;
END $$;
COMMIT;
