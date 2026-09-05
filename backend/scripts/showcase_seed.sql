-- Argo Subscription Management System: deterministic 12-month showcase data
--
-- This script is intentionally append-only. It preserves existing records,
-- refuses to run if the organization already has more than 50 customers, and
-- refuses to run twice for the same dataset marker. The whole DO block is one
-- transaction in PostgreSQL; any error rolls back every generated row.
--
-- Target: the configured Argo organization, 50 total customers, September
-- 2025 through August 17, 2026, PHP billing, and 10-row UI pagination.

DO $$
DECLARE
    v_org text := '00000000-0000-0000-0000-000000000001';
    v_marker text := 'showcase-12m-v1';
    v_as_of date := DATE '2026-08-17';
    v_target_customers integer := 50;
    v_actor text;
    v_existing_customers integer;
    v_existing_subscriptions integer;
    v_to_create integer;
    v_sub_index integer := 0;
    v_invoice_index integer := 0;
    v_customer record;
    v_plan record;
    v_feature record;
    v_status text;
    v_customer_id text;
    v_address_id text;
    v_sub_id text;
    v_event_id text;
    v_invoice_id text;
    v_item_id text;
    v_payment_id text;
    v_allocation_id text;
    v_attempt_id text;
    v_notification_id text;
    v_activity_id text;
    v_idempotency_id text;
    v_customer_code text;
    v_plan_id text;
    v_price_id text;
    v_pending_plan_id text;
    v_pending_price_id text;
    v_feature_id text;
    v_plan_code text;
    v_price_code text;
    v_unit integer;
    v_monthly integer;
    v_line integer;
    v_month_index integer;
    v_invoice_total integer;
    v_payment_amount integer;
    v_allocated_amount integer;
    v_issue_date date;
    v_due_date date;
    v_period_start timestamp with time zone;
    v_period_end timestamp with time zone;
    v_start_at timestamp with time zone;
    v_trial_end timestamp with time zone;
    v_end_at timestamp with time zone;
    v_limit_date date;
    v_created_at timestamp with time zone;
    v_attempt_status text;
    v_invoice_status text;
    v_should_pay boolean;
    v_partial boolean;
    v_draft boolean;
    v_void boolean;
    v_cancel_at_period_end boolean;
    v_auto_renew boolean;
    v_version integer;
    v_value_boolean boolean;
    v_value_number integer;
    v_value_text text;
    v_statuses text[] := ARRAY[
        'active','active','active','active','active','active','active','active','active','active','active',
        'active','active','active','active','active','active','active','active','active','active',
        'trialing',
        'pending_payment','pending_payment','pending_payment','pending_payment',
        'past_due','past_due','past_due','past_due','past_due',
        'suspended','suspended','suspended',
        'cancelled','cancelled','cancelled','cancelled',
        'expired','expired','expired'
    ];
    v_plan_basic text;
    v_plan_standard text;
    v_plan_premium text;
    v_plan_enterprise text;
    v_price_basic text;
    v_price_standard text;
    v_price_premium text;
    v_price_enterprise text;
    v_status_count integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM subscription_organizations WHERE id = v_org) THEN
        RAISE EXCEPTION 'Configured organization % does not exist', v_org;
    END IF;

    IF EXISTS (
        SELECT 1 FROM subscription_customers
        WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%'
    ) THEN
        RAISE EXCEPTION 'Dataset % already exists; refusing to duplicate it', v_marker;
    END IF;

    SELECT COUNT(*) INTO v_existing_customers
    FROM subscription_customers WHERE organization_id = v_org;
    IF v_existing_customers > v_target_customers THEN
        RAISE EXCEPTION 'Organization already has % customers; target is %', v_existing_customers, v_target_customers;
    END IF;

    SELECT id INTO v_actor
    FROM subscription_users
    WHERE organization_id = v_org AND status = 'active'
    ORDER BY created_at LIMIT 1;

    INSERT INTO subscription_settings (
        id, organization_id, default_currency, timezone, invoice_due_days,
        grace_period_days, max_payment_retries, retry_interval_days,
        trial_reminder_days, invoice_due_reminder_days, auto_renew_default,
        allow_partial_payments, auto_generate_invoices, invoice_prefix,
        payment_prefix, subscription_prefix, customer_prefix,
        enable_in_app_notifications, created_at, updated_at, created_by, updated_by
    )
    SELECT
        md5(v_marker || ':settings')::uuid::text, v_org, 'PHP', 'Asia/Manila', 7,
        7, 3, 1, 3, 3, true, true, true, 'INV', 'PAY', 'SUB', 'CUS', true,
        now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_settings WHERE organization_id = v_org);

    -- Reuse the four existing production plans when present; create only the
    -- missing catalog records. Annual prices are discounted to ten monthly
    -- periods so the dataset exercises both billing intervals.
    INSERT INTO subscription_plans (id, organization_id, plan_code, name, description, status, trial_days, is_featured, display_order, created_at, updated_at, created_by, updated_by)
    SELECT md5(v_marker || ':plan:BASIC')::uuid::text, v_org, 'BASIC', 'Basic', 'Core subscription plan', 'active', 14, false, 1, now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'BASIC');
    INSERT INTO subscription_plans (id, organization_id, plan_code, name, description, status, trial_days, is_featured, display_order, created_at, updated_at, created_by, updated_by)
    SELECT md5(v_marker || ':plan:STANDARD')::uuid::text, v_org, 'STANDARD', 'Standard', 'Growing teams subscription plan', 'active', 14, true, 2, now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'STANDARD');
    INSERT INTO subscription_plans (id, organization_id, plan_code, name, description, status, trial_days, is_featured, display_order, created_at, updated_at, created_by, updated_by)
    SELECT md5(v_marker || ':plan:PREMIUM')::uuid::text, v_org, 'PREMIUM', 'Premium', 'Advanced subscription plan', 'active', 30, false, 3, now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'PREMIUM');
    INSERT INTO subscription_plans (id, organization_id, plan_code, name, description, status, trial_days, is_featured, display_order, created_at, updated_at, created_by, updated_by)
    SELECT md5(v_marker || ':plan:ENTERPRISE')::uuid::text, v_org, 'ENTERPRISE', 'Enterprise', 'High-volume subscription plan', 'active', 30, false, 4, now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'ENTERPRISE');

    SELECT id INTO v_plan_basic FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'BASIC';
    SELECT id INTO v_plan_standard FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'STANDARD';
    SELECT id INTO v_plan_premium FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'PREMIUM';
    SELECT id INTO v_plan_enterprise FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'ENTERPRISE';

    INSERT INTO subscription_plans (id, organization_id, plan_code, name, description, status, trial_days, is_featured, display_order, created_at, updated_at, created_by, updated_by)
    SELECT md5(v_marker || ':plan:DRAFT')::uuid::text, v_org, 'SHOWCASE_DRAFT', 'Collaboration Plus (Draft)', v_marker || ' future plan for draft-state coverage', 'draft', 21, false, 20, now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'SHOWCASE_DRAFT');
    INSERT INTO subscription_plans (id, organization_id, plan_code, name, description, status, trial_days, is_featured, display_order, created_at, updated_at, created_by, updated_by)
    SELECT md5(v_marker || ':plan:LEGACY')::uuid::text, v_org, 'SHOWCASE_LEGACY', 'Legacy Archive', v_marker || ' archived plan for historical coverage', 'archived', 0, false, 21, now(), now(), v_actor, v_actor
    WHERE NOT EXISTS (SELECT 1 FROM subscription_plans WHERE organization_id = v_org AND plan_code = 'SHOWCASE_LEGACY');

    FOR v_plan IN SELECT id, plan_code FROM subscription_plans WHERE organization_id = v_org AND plan_code IN ('BASIC','STANDARD','PREMIUM','ENTERPRISE') LOOP
        SELECT unit_amount_minor INTO v_monthly
        FROM subscription_plan_prices
        WHERE organization_id = v_org AND plan_id = v_plan.id AND billing_interval = 'month' AND currency = 'PHP'
        ORDER BY is_default DESC, created_at LIMIT 1;
        IF v_monthly IS NULL THEN
            v_monthly := CASE v_plan.plan_code WHEN 'BASIC' THEN 55000 WHEN 'STANDARD' THEN 177500 WHEN 'PREMIUM' THEN 606500 WHEN 'ENTERPRISE' THEN 606500 ELSE 55000 END;
            INSERT INTO subscription_plan_prices (id, organization_id, plan_id, price_code, billing_interval, interval_count, currency, unit_amount_minor, setup_fee_minor, status, effective_from, is_default, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':price:' || v_plan.plan_code || ':month')::uuid::text, v_org, v_plan.id, v_plan.plan_code || '-MONTH', 'month', 1, 'PHP', v_monthly, 0, 'active', DATE '2025-09-01', true, now(), now(), v_actor, v_actor);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM subscription_plan_prices WHERE organization_id = v_org AND plan_id = v_plan.id AND billing_interval = 'year' AND currency = 'PHP') THEN
            INSERT INTO subscription_plan_prices (id, organization_id, plan_id, price_code, billing_interval, interval_count, currency, unit_amount_minor, setup_fee_minor, status, effective_from, is_default, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':price:' || v_plan.plan_code || ':year')::uuid::text, v_org, v_plan.id, v_plan.plan_code || '-YEAR', 'year', 1, 'PHP', v_monthly * 10, 0, 'active', DATE '2025-09-01', false, now(), now(), v_actor, v_actor);
        END IF;
    END LOOP;

    -- Feature catalog and plan-feature matrix.
    FOR v_feature IN
        SELECT * FROM (VALUES
            ('SEATS','Team seats','Licensed users on the account','number','seats'),
            ('STORAGE','Storage','Included file storage','number','GB'),
            ('PROJECTS','Projects','Maximum active projects','number','projects'),
            ('API_ACCESS','API access','Programmatic API access','boolean',NULL),
            ('CUSTOM_DOMAIN','Custom domain','Custom domain support','boolean',NULL),
            ('ANALYTICS','Analytics','Reporting depth','text',NULL),
            ('SUPPORT','Support','Support response tier','text',NULL),
            ('SLA','SLA','Service-level agreement','boolean',NULL),
            ('AUTOMATIONS','Automations','Automated workflows','number','workflows'),
            ('AUDIT_LOGS','Audit logs','Historical audit retention','text',NULL)
        ) AS f(code,name,description,value_type,unit_label)
    LOOP
        SELECT id INTO v_feature_id FROM subscription_features WHERE organization_id = v_org AND feature_code = v_feature.code ORDER BY created_at LIMIT 1;
        IF v_feature_id IS NULL THEN
            v_feature_id := md5(v_marker || ':feature:' || v_feature.code)::uuid::text;
            INSERT INTO subscription_features (id, organization_id, feature_code, name, description, value_type, unit_label, status, created_at, updated_at, created_by, updated_by)
            VALUES (v_feature_id, v_org, v_feature.code, v_feature.name, v_marker || ' - ' || v_feature.description, v_feature.value_type, v_feature.unit_label, 'active', now(), now(), v_actor, v_actor);
        END IF;
        FOR v_plan IN SELECT id, plan_code FROM subscription_plans WHERE organization_id = v_org AND plan_code IN ('BASIC','STANDARD','PREMIUM','ENTERPRISE') LOOP
            IF NOT EXISTS (SELECT 1 FROM subscription_plan_features WHERE organization_id = v_org AND plan_id = v_plan.id AND feature_id = v_feature_id) THEN
                v_value_boolean := NULL; v_value_number := NULL; v_value_text := NULL;
                IF v_feature.value_type = 'boolean' THEN
                    v_value_boolean := v_plan.plan_code IN ('STANDARD','PREMIUM','ENTERPRISE') OR v_feature.code = 'API_ACCESS' AND v_plan.plan_code = 'BASIC';
                ELSIF v_feature.value_type = 'number' THEN
                    v_value_number := CASE v_feature.code
                        WHEN 'SEATS' THEN CASE v_plan.plan_code WHEN 'BASIC' THEN 3 WHEN 'STANDARD' THEN 10 WHEN 'PREMIUM' THEN 30 ELSE 100 END
                        WHEN 'STORAGE' THEN CASE v_plan.plan_code WHEN 'BASIC' THEN 10 WHEN 'STANDARD' THEN 100 WHEN 'PREMIUM' THEN 500 ELSE 2000 END
                        WHEN 'PROJECTS' THEN CASE v_plan.plan_code WHEN 'BASIC' THEN 3 WHEN 'STANDARD' THEN 20 WHEN 'PREMIUM' THEN 100 ELSE 999 END
                        ELSE CASE v_plan.plan_code WHEN 'BASIC' THEN 5 WHEN 'STANDARD' THEN 25 WHEN 'PREMIUM' THEN 100 ELSE 500 END END;
                ELSE
                    v_value_text := CASE v_feature.code
                        WHEN 'ANALYTICS' THEN CASE v_plan.plan_code WHEN 'BASIC' THEN 'Standard' WHEN 'STANDARD' THEN 'Advanced' ELSE 'Advanced + exports' END
                        WHEN 'SUPPORT' THEN CASE v_plan.plan_code WHEN 'BASIC' THEN 'Email' WHEN 'STANDARD' THEN 'Priority' WHEN 'PREMIUM' THEN 'Dedicated' ELSE '24/7 concierge' END
                        ELSE CASE v_plan.plan_code WHEN 'BASIC' THEN '30 days' WHEN 'STANDARD' THEN '90 days' WHEN 'PREMIUM' THEN '1 year' ELSE '7 years' END END;
                END IF;
                INSERT INTO subscription_plan_features (id, organization_id, plan_id, feature_id, is_included, value_boolean, value_number, value_text, display_order, created_at, updated_at, created_by, updated_by)
                VALUES (md5(v_marker || ':plan-feature:' || v_plan.plan_code || ':' || v_feature.code)::uuid::text, v_org, v_plan.id, v_feature_id, true, v_value_boolean, v_value_number, v_value_text, 1, now(), now(), v_actor, v_actor);
            END IF;
        END LOOP;
    END LOOP;

    -- Add exactly the missing customers. All generated records carry the
    -- marker in notes so the cleanup script can identify them precisely.
    v_to_create := v_target_customers - v_existing_customers;
    FOR v_status_count IN 1..v_to_create LOOP
        v_customer_id := md5(v_marker || ':customer:' || v_status_count::text)::uuid::text;
        v_customer_code := 'SC-' || lpad(v_status_count::text, 4, '0');
        v_created_at := date_trunc('month', v_as_of::timestamp) - make_interval(months => (11 - ((v_status_count - 1) % 11))) + interval '1 day';
        IF v_status_count % 2 = 0 THEN
            INSERT INTO subscription_customers (id, organization_id, customer_code, customer_type, display_name, company_name, email, phone, tax_identifier, status, notes, created_at, updated_at, created_by, updated_by)
            VALUES (v_customer_id, v_org, v_customer_code, 'organization', (ARRAY['Harborline Systems','LumenWorks Studio','NorthStar Commerce','Pinecrest Health','Summit Learning Hub','CedarPoint Logistics','BrightPath Media','ApexCore Technologies','Riverstone Foods','Atlas Green Energy'])[((v_status_count / 2 - 1) % 10) + 1], (ARRAY['Harborline Systems','LumenWorks Studio','NorthStar Commerce','Pinecrest Health','Summit Learning Hub','CedarPoint Logistics','BrightPath Media','ApexCore Technologies','Riverstone Foods','Atlas Green Energy'])[((v_status_count / 2 - 1) % 10) + 1], 'showcase-' || lpad(v_status_count::text, 2, '0') || '@example.com', '+63 917 555 ' || lpad(v_status_count::text, 4, '0'), 'SC-TIN-' || lpad(v_status_count::text, 6, '0'), 'active', v_marker || ' generated organization', v_created_at, v_as_of::timestamp, v_actor, v_actor);
        ELSE
            INSERT INTO subscription_customers (id, organization_id, customer_code, customer_type, display_name, company_name, email, phone, tax_identifier, status, notes, created_at, updated_at, created_by, updated_by)
            VALUES (v_customer_id, v_org, v_customer_code, 'individual', (ARRAY['Ariana Villanueva','Bea Navarro','Carlos Mendoza','Diana Castillo','Elias Ramos','Faye Santos','Gabriel Flores','Hannah Lim','Ivan Mercado','Jessa Bautista'])[((v_status_count + 1) / 2 - 1) % 10 + 1], NULL, 'showcase-' || lpad(v_status_count::text, 2, '0') || '@example.com', '+63 917 555 ' || lpad(v_status_count::text, 4, '0'), 'SC-TIN-' || lpad(v_status_count::text, 6, '0'), 'active', v_marker || ' generated individual', v_created_at, v_as_of::timestamp, v_actor, v_actor);
        END IF;
        v_address_id := md5(v_marker || ':address:' || v_status_count::text || ':billing')::uuid::text;
        INSERT INTO subscription_customer_addresses (id, organization_id, customer_id, address_type, line1, line2, city_municipality, province, postal_code, country_code, is_primary, created_at, updated_at, created_by, updated_by)
        VALUES (v_address_id, v_org, v_customer_id, 'billing', (100 + v_status_count)::text || ' Argo Avenue', CASE WHEN v_status_count % 3 = 0 THEN 'Unit ' || v_status_count::text ELSE NULL END, (ARRAY['Makati','Quezon City','Cebu City','Davao City','Iloilo City'])[((v_status_count - 1) % 5) + 1], (ARRAY['Metro Manila','Cebu','Davao del Sur','Iloilo','Laguna'])[((v_status_count - 1) % 5) + 1], lpad((1000 + v_status_count)::text, 4, '0'), 'PH', true, v_created_at, v_as_of::timestamp, v_actor, v_actor);
        IF v_status_count % 2 = 0 THEN
            INSERT INTO subscription_customer_addresses (id, organization_id, customer_id, address_type, line1, line2, city_municipality, province, postal_code, country_code, is_primary, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':address:' || v_status_count::text || ':shipping')::uuid::text, v_org, v_customer_id, 'shipping', (100 + v_status_count)::text || ' Argo Avenue', 'Receiving dock', (ARRAY['Makati','Quezon City','Cebu City','Davao City','Iloilo City'])[((v_status_count - 1) % 5) + 1], (ARRAY['Metro Manila','Cebu','Davao del Sur','Iloilo','Laguna'])[((v_status_count - 1) % 5) + 1], lpad((1000 + v_status_count)::text, 4, '0'), 'PH', false, v_created_at, v_as_of::timestamp, v_actor, v_actor);
        END IF;
    END LOOP;

    -- Backfill a billing address for existing customers that do not have one;
    -- this does not alter existing addresses.
    FOR v_customer IN
        SELECT c.id, c.customer_code FROM subscription_customers c
        WHERE c.organization_id = v_org
          AND NOT EXISTS (SELECT 1 FROM subscription_customer_addresses a WHERE a.customer_id = c.id AND a.address_type = 'billing')
    LOOP
        INSERT INTO subscription_customer_addresses (id, organization_id, customer_id, address_type, line1, city_municipality, province, postal_code, country_code, is_primary, created_at, updated_at, created_by, updated_by)
        VALUES (md5(v_marker || ':existing-address:' || v_customer.id)::uuid::text, v_org, v_customer.id, 'billing', '1 Argo Avenue', 'Makati', 'Metro Manila', '1200', 'PH', true, v_as_of::timestamp, v_as_of::timestamp, v_actor, v_actor);
    END LOOP;

    -- Existing live records are left untouched. New subscriptions fill every
    -- remaining customer slot so the organization ends with 50 subscriptions.
    SELECT COUNT(*) INTO v_existing_subscriptions FROM subscription_subscriptions WHERE organization_id = v_org;
    v_to_create := v_target_customers - v_existing_subscriptions;
    IF v_to_create < 0 THEN
        RAISE EXCEPTION 'Organization already has % subscriptions; expected no more than %', v_existing_subscriptions, v_target_customers;
    END IF;
    IF v_to_create <> array_length(v_statuses, 1) THEN
        RAISE EXCEPTION 'Status blueprint has % rows but % subscriptions are needed', array_length(v_statuses, 1), v_to_create;
    END IF;

    FOR v_customer IN
        SELECT c.id, c.customer_code FROM subscription_customers c
        WHERE c.organization_id = v_org
          AND (c.notes LIKE '%' || v_marker || '%' OR NOT EXISTS (SELECT 1 FROM subscription_subscriptions s WHERE s.customer_id = c.id))
        ORDER BY c.created_at, c.id
        LIMIT v_to_create
    LOOP
        v_sub_index := v_sub_index + 1;
        v_status := v_statuses[v_sub_index];
        v_customer_id := v_customer.id;
        v_plan_id := CASE ((v_sub_index - 1) % 4) WHEN 0 THEN v_plan_basic WHEN 1 THEN v_plan_standard WHEN 2 THEN v_plan_premium ELSE v_plan_enterprise END;
        SELECT id, unit_amount_minor INTO v_price_id, v_unit
        FROM subscription_plan_prices
        WHERE organization_id = v_org AND plan_id = v_plan_id AND billing_interval = 'month' AND currency = 'PHP'
        ORDER BY is_default DESC, created_at LIMIT 1;
        IF v_price_id IS NULL THEN RAISE EXCEPTION 'Missing monthly price for plan %', v_plan_id; END IF;

        v_start_at := date_trunc('month', v_as_of::timestamp) - make_interval(months => ((v_sub_index - 1) % 11)) + interval '3 days';
        v_trial_end := NULL; v_period_start := date_trunc('month', v_start_at); v_period_end := v_period_start + interval '1 month'; v_end_at := NULL;
        v_auto_renew := v_status NOT IN ('cancelled','expired');
        v_cancel_at_period_end := false; v_pending_plan_id := NULL; v_pending_price_id := NULL; v_version := 1;
        IF v_status = 'trialing' THEN
            v_start_at := v_as_of::timestamp - make_interval(days => (v_sub_index % 5) + 1);
            v_trial_end := v_as_of::timestamp + interval '7 days';
            v_period_start := NULL; v_period_end := NULL;
        ELSIF v_status IN ('cancelled','expired') THEN
            v_end_at := v_as_of::timestamp - make_interval(days => (v_sub_index % 60) + 7);
            v_period_start := date_trunc('month', v_end_at);
            v_period_end := v_end_at;
            v_auto_renew := false;
        ELSIF v_status IN ('past_due','suspended') THEN
            v_period_start := date_trunc('month', v_as_of::timestamp) - interval '1 month';
            v_period_end := v_as_of::timestamp - interval '2 days';
        ELSIF v_status = 'pending_payment' THEN
            v_period_start := date_trunc('month', v_as_of::timestamp);
            v_period_end := v_as_of::timestamp + interval '14 days';
        ELSE
            v_period_start := date_trunc('month', v_as_of::timestamp);
            v_period_end := v_as_of::timestamp + interval '14 days';
        END IF;
        v_cancel_at_period_end := v_status IN ('active','trialing') AND v_sub_index % 13 = 0;
        IF v_status = 'active' AND v_sub_index % 11 = 0 THEN
            v_pending_plan_id := CASE ((v_sub_index) % 4) WHEN 0 THEN v_plan_basic WHEN 1 THEN v_plan_standard WHEN 2 THEN v_plan_premium ELSE v_plan_enterprise END;
            SELECT id INTO v_pending_price_id FROM subscription_plan_prices WHERE organization_id = v_org AND plan_id = v_pending_plan_id AND billing_interval = 'month' AND currency = 'PHP' ORDER BY is_default DESC LIMIT 1;
            v_version := v_version + 1;
        END IF;
        IF v_cancel_at_period_end THEN v_version := v_version + 1; END IF;
        v_sub_id := md5(v_marker || ':subscription:' || v_customer_id)::uuid::text;
        INSERT INTO subscription_subscriptions (id, organization_id, subscription_number, customer_id, plan_id, plan_price_id, pending_plan_id, pending_plan_price_id, status, starts_at, trial_start_at, trial_end_at, current_period_start, current_period_end, next_billing_at, plan_change_effective_at, auto_renew, cancel_at_period_end, cancelled_at, ended_at, cancellation_reason, version, created_at, updated_at, created_by, updated_by)
        VALUES (v_sub_id, v_org, 'SC-SUB-' || lpad(v_sub_index::text, 5, '0'), v_customer_id, v_plan_id, v_price_id, v_pending_plan_id, v_pending_price_id, v_status, v_start_at, CASE WHEN v_status = 'trialing' THEN v_start_at ELSE NULL END, v_trial_end, v_period_start, v_period_end, CASE WHEN v_status IN ('active','pending_payment','trialing') THEN v_period_end ELSE NULL END, CASE WHEN v_pending_price_id IS NOT NULL THEN v_period_end ELSE NULL END, v_auto_renew, v_cancel_at_period_end, CASE WHEN v_status = 'cancelled' THEN v_end_at ELSE NULL END, v_end_at, CASE WHEN v_status IN ('cancelled','expired') THEN 'showcase lifecycle scenario' ELSE NULL END, v_version, v_start_at - interval '1 day', v_as_of::timestamp, v_actor, v_actor);

        v_event_id := md5(v_marker || ':event:' || v_sub_id || ':created')::uuid::text;
        INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
        VALUES (v_event_id, v_org, v_sub_id, 'created', NULL, v_status, v_start_at, 'system', v_marker || ' subscription created', v_event_id, json_build_object('dataset',v_marker), v_start_at, v_start_at, v_actor, v_actor);
        IF v_status = 'trialing' THEN
            INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':event:' || v_sub_id || ':trial')::uuid::text, v_org, v_sub_id, 'trial_started', NULL, 'trialing', v_start_at, 'system', v_marker || ' trial', v_sub_id, json_build_object('dataset',v_marker), v_start_at, v_start_at, v_actor, v_actor);
        END IF;
        IF v_status IN ('past_due','suspended') THEN
            INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':event:' || v_sub_id || ':overdue')::uuid::text, v_org, v_sub_id, 'payment_overdue', 'active', v_status, v_as_of::timestamp - interval '10 days', 'system', v_marker || ' overdue scenario', v_sub_id, json_build_object('dataset',v_marker), v_as_of::timestamp - interval '10 days', v_as_of::timestamp - interval '10 days', v_actor, v_actor);
        END IF;
        IF v_status = 'cancelled' THEN
            INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':event:' || v_sub_id || ':cancelled')::uuid::text, v_org, v_sub_id, 'cancelled', 'active', 'cancelled', v_end_at, 'system', v_marker || ' cancellation scenario', v_sub_id, json_build_object('dataset',v_marker), v_end_at, v_end_at, v_actor, v_actor);
        END IF;
        IF v_status = 'expired' THEN
            INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':event:' || v_sub_id || ':expired')::uuid::text, v_org, v_sub_id, 'expired', 'active', 'expired', v_end_at, 'system', v_marker || ' non-renewal scenario', v_sub_id, json_build_object('dataset',v_marker), v_end_at, v_end_at, v_actor, v_actor);
        END IF;
        IF v_cancel_at_period_end THEN
            INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':event:' || v_sub_id || ':schedule-cancel')::uuid::text, v_org, v_sub_id, 'cancellation_scheduled', v_status, v_status, v_as_of::timestamp - interval '2 days', 'system', v_marker || ' scheduled cancellation', v_sub_id, json_build_object('dataset',v_marker), v_as_of::timestamp - interval '2 days', v_as_of::timestamp - interval '2 days', v_actor, v_actor);
        END IF;
        IF v_pending_price_id IS NOT NULL THEN
            INSERT INTO subscription_subscription_events (id, organization_id, subscription_id, event_type, from_status, to_status, effective_at, actor_type, reason, correlation_id, metadata_json, created_at, updated_at, created_by, updated_by)
            VALUES (md5(v_marker || ':event:' || v_sub_id || ':plan-change')::uuid::text, v_org, v_sub_id, 'plan_change_scheduled', v_status, v_status, v_as_of::timestamp - interval '1 day', 'system', v_marker || ' plan change', v_sub_id, json_build_object('dataset',v_marker,'pending_plan_price_id',v_pending_price_id), v_as_of::timestamp - interval '1 day', v_as_of::timestamp - interval '1 day', v_actor, v_actor);
        END IF;

        -- Monthly invoices create the 12-month ledger. Trial subscriptions
        -- intentionally have no invoice until the trial ends.
        IF v_status <> 'trialing' THEN
            v_limit_date := CASE WHEN v_status IN ('cancelled','expired') THEN v_end_at::date ELSE v_as_of END;
            v_issue_date := date_trunc('month', v_start_at)::date;
            v_month_index := 0;
            WHILE v_issue_date <= v_limit_date AND v_month_index < 12 LOOP
                v_invoice_index := v_invoice_index + 1;
                v_due_date := v_issue_date + 7;
                v_invoice_id := md5(v_marker || ':invoice:' || v_sub_id || ':' || v_month_index::text)::uuid::text;
                v_invoice_total := v_unit;
                v_draft := v_month_index = 0 AND v_sub_index % 19 = 0;
                v_void := v_month_index = 1 AND v_sub_index % 23 = 0;
                INSERT INTO subscription_invoices (id, organization_id, invoice_number, customer_id, subscription_id, status, issue_date, due_date, service_period_start, service_period_end, currency, notes, finalized_at, voided_at, void_reason, created_at, updated_at, created_by, updated_by)
                VALUES (v_invoice_id, v_org, 'SC-INV-' || substr(md5(v_invoice_id),1,10), v_customer_id, v_sub_id, CASE WHEN v_draft THEN 'draft' WHEN v_void THEN 'void' ELSE 'open' END, v_issue_date, v_due_date, v_issue_date::timestamp, (v_issue_date + 30)::timestamp, 'PHP', v_marker || ' monthly ledger', CASE WHEN NOT v_draft THEN v_issue_date::timestamp ELSE NULL END, CASE WHEN v_void THEN v_issue_date::timestamp ELSE NULL END, CASE WHEN v_void THEN v_marker || ' void scenario' ELSE NULL END, v_issue_date::timestamp, v_as_of::timestamp, v_actor, v_actor);
                v_line := 1;
                INSERT INTO subscription_invoice_items (id, organization_id, invoice_id, line_number, item_type, description, quantity, unit_amount_minor, tax_rate_bps, service_period_start, service_period_end, plan_id, plan_price_id, created_at, updated_at, created_by, updated_by)
                VALUES (md5(v_marker || ':item:' || v_invoice_id || ':recurring')::uuid::text, v_org, v_invoice_id, v_line, 'recurring', 'Subscription recurring charge', 1, v_unit, CASE WHEN v_sub_index % 3 = 0 THEN 1200 ELSE 0 END, v_issue_date::timestamp, (v_issue_date + 30)::timestamp, v_plan_id, v_price_id, v_issue_date::timestamp, v_as_of::timestamp, v_actor, v_actor);
                IF v_month_index = 0 AND v_sub_index % 3 = 0 THEN
                    v_line := v_line + 1; v_invoice_total := v_invoice_total + 5000;
                    INSERT INTO subscription_invoice_items (id, organization_id, invoice_id, line_number, item_type, description, quantity, unit_amount_minor, tax_rate_bps, service_period_start, service_period_end, plan_id, plan_price_id, created_at, updated_at, created_by, updated_by)
                    VALUES (md5(v_marker || ':item:' || v_invoice_id || ':setup')::uuid::text, v_org, v_invoice_id, v_line, 'setup', 'One-time setup fee', 1, 5000, 0, v_issue_date::timestamp, (v_issue_date + 30)::timestamp, v_plan_id, v_price_id, v_issue_date::timestamp, v_as_of::timestamp, v_actor, v_actor);
                END IF;
                IF (v_sub_index + v_month_index) % 4 = 0 THEN
                    v_line := v_line + 1; v_invoice_total := v_invoice_total - (v_unit / 10);
                    INSERT INTO subscription_invoice_items (id, organization_id, invoice_id, line_number, item_type, description, quantity, unit_amount_minor, tax_rate_bps, service_period_start, service_period_end, plan_id, plan_price_id, created_at, updated_at, created_by, updated_by)
                    VALUES (md5(v_marker || ':item:' || v_invoice_id || ':discount')::uuid::text, v_org, v_invoice_id, v_line, 'discount', 'Showcase loyalty discount', 1, -(v_unit / 10), 0, v_issue_date::timestamp, (v_issue_date + 30)::timestamp, v_plan_id, v_price_id, v_issue_date::timestamp, v_as_of::timestamp, v_actor, v_actor);
                END IF;
                v_should_pay := false;
                IF v_status IN ('active','cancelled','expired') THEN v_should_pay := true;
                ELSIF v_status = 'pending_payment' AND v_issue_date < date_trunc('month', v_as_of::timestamp)::date THEN v_should_pay := true;
                ELSIF v_status IN ('past_due','suspended') AND v_issue_date < (date_trunc('month', v_as_of::timestamp)::date - 30) THEN v_should_pay := true;
                END IF;
                v_partial := v_should_pay AND (v_sub_index + v_month_index) % 17 = 0;
                v_attempt_id := NULL;
                IF v_invoice_index <= 60 AND NOT v_draft AND NOT v_void THEN
                    v_attempt_id := md5(v_marker || ':attempt:' || v_invoice_id)::uuid::text;
                    IF v_should_pay AND v_invoice_index <= 48 THEN v_attempt_status := 'succeeded';
                    ELSIF v_invoice_index <= 56 THEN v_attempt_status := 'failed';
                    ELSE v_attempt_status := 'pending'; END IF;
                    INSERT INTO subscription_payment_attempts (id, organization_id, attempt_reference, invoice_id, provider, provider_attempt_id, idempotency_key, request_hash, status, amount_minor, currency, attempted_at, completed_at, failure_message, created_at, updated_at, created_by, updated_by)
                    VALUES (v_attempt_id, v_org, 'SC-ATT-' || substr(md5(v_attempt_id),1,10), v_invoice_id, 'manual', v_marker || ':provider:' || substr(md5(v_attempt_id),1,12), v_marker || ':attempt:' || v_invoice_index::text, md5(v_marker || ':attempt-hash:' || v_invoice_id), v_attempt_status, v_invoice_total, 'PHP', v_issue_date::timestamp + interval '3 days', CASE WHEN v_attempt_status = 'succeeded' THEN v_issue_date::timestamp + interval '4 days' ELSE NULL END, CASE WHEN v_attempt_status = 'failed' THEN 'Showcase declined payment' ELSE NULL END, v_issue_date::timestamp, v_as_of::timestamp, v_actor, v_actor);
                END IF;
                IF v_should_pay AND NOT v_draft AND NOT v_void THEN
                    v_payment_amount := CASE WHEN v_partial THEN greatest(1, v_invoice_total / 2) ELSE v_invoice_total END;
                    v_payment_id := md5(v_marker || ':payment:' || v_invoice_id)::uuid::text;
                    INSERT INTO subscription_payments (id, organization_id, payment_reference, customer_id, payment_attempt_id, payment_method, status, amount_minor, currency, received_at, external_reference, notes, created_at, updated_at, created_by, updated_by)
                    VALUES (v_payment_id, v_org, 'SC-PAY-' || substr(md5(v_payment_id),1,10), v_customer_id, CASE WHEN v_attempt_status = 'succeeded' THEN v_attempt_id ELSE NULL END, CASE WHEN (v_sub_index + v_month_index) % 3 = 0 THEN 'manual_cash' ELSE 'manual_bank' END, 'completed', v_payment_amount, 'PHP', v_issue_date::timestamp + interval '5 days', v_marker || ':external:' || substr(md5(v_payment_id),1,12), v_marker || ' historical payment', v_issue_date::timestamp + interval '5 days', v_as_of::timestamp, v_actor, v_actor);
                    v_allocation_id := md5(v_marker || ':allocation:' || v_payment_id)::uuid::text;
                    INSERT INTO subscription_payment_allocations (id, organization_id, payment_id, invoice_id, amount_minor, allocated_at, created_at, updated_at, created_by, updated_by)
                    VALUES (v_allocation_id, v_org, v_payment_id, v_invoice_id, v_payment_amount, v_issue_date::timestamp + interval '5 days', v_issue_date::timestamp + interval '5 days', v_as_of::timestamp, v_actor, v_actor);
                    v_invoice_status := CASE WHEN v_payment_amount >= v_invoice_total THEN 'paid' WHEN v_due_date < v_as_of THEN 'overdue' ELSE 'open' END;
                    UPDATE subscription_invoices SET status = v_invoice_status WHERE id = v_invoice_id;
                ELSE
                    v_invoice_status := CASE WHEN v_draft THEN 'draft' WHEN v_void THEN 'void' WHEN v_due_date < v_as_of THEN 'overdue' ELSE 'open' END;
                    UPDATE subscription_invoices SET status = v_invoice_status WHERE id = v_invoice_id;
                END IF;
                v_month_index := v_month_index + 1;
                v_issue_date := (date_trunc('month', v_start_at)::date + make_interval(months => v_month_index))::date;
            END LOOP;
        END IF;

        -- Two notifications per generated subscription exercise unread and
        -- read states without creating a mailbox-sized dataset.
        v_notification_id := md5(v_marker || ':notification:' || v_sub_id || ':invoice')::uuid::text;
        INSERT INTO subscription_notifications (id, organization_id, customer_id, recipient_user_id, channel, notification_type, title, body, status, related_entity_type, related_entity_id, sent_at, read_at, created_at, updated_at, created_by, updated_by)
        VALUES (v_notification_id, v_org, v_customer_id, v_actor, 'in_app', 'invoice_issued', 'Invoice activity', v_marker || ' invoice activity for subscription ' || v_sub_id, CASE WHEN v_sub_index % 4 = 0 THEN 'sent' ELSE 'read' END, 'subscription', v_sub_id, v_as_of::timestamp - interval '1 day', CASE WHEN v_sub_index % 4 = 0 THEN NULL ELSE v_as_of::timestamp END, v_as_of::timestamp - interval '1 day', v_as_of::timestamp, v_actor, v_actor);
        v_notification_id := md5(v_marker || ':notification:' || v_sub_id || ':lifecycle')::uuid::text;
        INSERT INTO subscription_notifications (id, organization_id, customer_id, recipient_user_id, channel, notification_type, title, body, status, related_entity_type, related_entity_id, sent_at, read_at, created_at, updated_at, created_by, updated_by)
        VALUES (v_notification_id, v_org, v_customer_id, v_actor, 'in_app', CASE WHEN v_status = 'trialing' THEN 'trial_ending' WHEN v_status IN ('past_due','suspended') THEN 'payment_failed' ELSE 'renewal' END, 'Subscription lifecycle update', v_marker || ' lifecycle scenario: ' || v_status, CASE WHEN v_sub_index % 5 = 0 THEN 'sent' ELSE 'read' END, 'subscription', v_sub_id, v_as_of::timestamp - interval '2 days', CASE WHEN v_sub_index % 5 = 0 THEN NULL ELSE v_as_of::timestamp END, v_as_of::timestamp - interval '2 days', v_as_of::timestamp, v_actor, v_actor);

        v_activity_id := md5(v_marker || ':activity:subscription:' || v_sub_id)::uuid::text;
        INSERT INTO subscription_activity_logs (id, organization_id, entity_type, entity_id, action, actor_user_id, request_id, details_json, created_at, updated_at, created_by, updated_by)
        VALUES (v_activity_id, v_org, 'subscription', v_sub_id, 'showcase_imported', v_actor, v_activity_id, json_build_object('dataset',v_marker,'status',v_status), v_as_of::timestamp, v_as_of::timestamp, v_actor, v_actor);
    END LOOP;

    IF v_sub_index <> v_to_create THEN
        RAISE EXCEPTION 'Expected % generated subscriptions but inserted %', v_to_create, v_sub_index;
    END IF;

    -- Ten account-credit payments remain intentionally unallocated so the
    -- payment allocation workflow has realistic open credits to exercise.
    FOR v_status_count IN 1..10 LOOP
        SELECT id INTO v_customer_id FROM subscription_customers WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%' ORDER BY customer_code OFFSET (v_status_count - 1) LIMIT 1;
        v_payment_id := md5(v_marker || ':credit:' || v_status_count::text)::uuid::text;
        INSERT INTO subscription_payments (id, organization_id, payment_reference, customer_id, payment_method, status, amount_minor, currency, received_at, external_reference, notes, created_at, updated_at, created_by, updated_by)
        VALUES (v_payment_id, v_org, 'SC-CREDIT-' || lpad(v_status_count::text, 3, '0'), v_customer_id, CASE WHEN v_status_count % 2 = 0 THEN 'manual_bank' ELSE 'manual_cash' END, 'completed', 25000 + v_status_count * 1000, 'PHP', v_as_of::timestamp - make_interval(days => v_status_count), v_marker || ':credit:' || v_status_count::text, v_marker || ' unallocated account credit', v_as_of::timestamp - make_interval(days => v_status_count), v_as_of::timestamp, v_actor, v_actor);
    END LOOP;

    -- Bridge the first calendar bucket so the reports contain all twelve
    -- requested month labels (September 2025 through August 2026).
    IF NOT EXISTS (
        SELECT 1 FROM subscription_invoices
        WHERE organization_id = v_org AND notes = v_marker || ' September bridge'
    ) THEN
        SELECT id INTO v_customer_id
        FROM subscription_customers
        WHERE organization_id = v_org AND notes LIKE '%' || v_marker || '%'
        ORDER BY customer_code LIMIT 1;
        v_invoice_id := md5(v_marker || ':september-bridge:invoice')::uuid::text;
        v_payment_id := md5(v_marker || ':september-bridge:payment')::uuid::text;
        INSERT INTO subscription_invoices (id, organization_id, invoice_number, customer_id, subscription_id, status, issue_date, due_date, service_period_start, service_period_end, currency, notes, finalized_at, created_at, updated_at, created_by, updated_by)
        VALUES (v_invoice_id, v_org, 'SC-INV-SEP25', v_customer_id, NULL, 'paid', DATE '2025-09-01', DATE '2025-09-08', TIMESTAMP WITH TIME ZONE '2025-09-01 00:00:00+08', TIMESTAMP WITH TIME ZONE '2025-09-30 23:59:59+08', 'PHP', v_marker || ' September bridge', TIMESTAMP WITH TIME ZONE '2025-09-01 00:00:00+08', TIMESTAMP WITH TIME ZONE '2025-09-01 00:00:00+08', v_as_of::timestamp, v_actor, v_actor);
        INSERT INTO subscription_invoice_items (id, organization_id, invoice_id, line_number, item_type, description, quantity, unit_amount_minor, tax_rate_bps, service_period_start, service_period_end, created_at, updated_at, created_by, updated_by)
        VALUES (md5(v_marker || ':september-bridge:item')::uuid::text, v_org, v_invoice_id, 1, 'adjustment', 'Historical onboarding adjustment', 1, 55000, 0, TIMESTAMP WITH TIME ZONE '2025-09-01 00:00:00+08', TIMESTAMP WITH TIME ZONE '2025-09-30 23:59:59+08', TIMESTAMP WITH TIME ZONE '2025-09-01 00:00:00+08', v_as_of::timestamp, v_actor, v_actor);
        INSERT INTO subscription_payments (id, organization_id, payment_reference, customer_id, payment_method, status, amount_minor, currency, received_at, external_reference, notes, created_at, updated_at, created_by, updated_by)
        VALUES (v_payment_id, v_org, 'SC-PAY-SEP25', v_customer_id, 'manual_bank', 'completed', 55000, 'PHP', TIMESTAMP WITH TIME ZONE '2025-09-06 12:00:00+08', v_marker || ':september-bridge', v_marker || ' September bridge payment', TIMESTAMP WITH TIME ZONE '2025-09-06 12:00:00+08', v_as_of::timestamp, v_actor, v_actor);
        INSERT INTO subscription_payment_allocations (id, organization_id, payment_id, invoice_id, amount_minor, allocated_at, created_at, updated_at, created_by, updated_by)
        VALUES (md5(v_marker || ':september-bridge:allocation')::uuid::text, v_org, v_payment_id, v_invoice_id, 55000, TIMESTAMP WITH TIME ZONE '2025-09-06 12:00:00+08', TIMESTAMP WITH TIME ZONE '2025-09-06 12:00:00+08', v_as_of::timestamp, v_actor, v_actor);
    END IF;

    v_idempotency_id := md5(v_marker || ':idempotency')::uuid::text;
    INSERT INTO subscription_idempotency_keys (id, organization_id, operation, idempotency_key, request_hash, status, resource_type, resource_id, response_status, result_json, created_at, updated_at, created_by, updated_by)
    VALUES (v_idempotency_id, v_org, 'showcase.import', v_marker, md5(v_marker), 'completed', 'showcase_dataset', v_idempotency_id, 201, json_build_object('dataset',v_marker,'customers_added',v_to_create,'subscriptions_added',v_sub_index), v_as_of::timestamp, v_as_of::timestamp, v_actor, v_actor);

    RAISE NOTICE 'Imported %: % customers added, % subscriptions added, invoices/payment rows generated transactionally', v_marker, v_to_create, v_sub_index;
END $$;
