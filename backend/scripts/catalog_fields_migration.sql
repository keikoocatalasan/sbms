-- Additive catalog migration for list prices and discounts.
-- Run once against PostgreSQL before deploying code that uses these fields.
BEGIN;
ALTER TABLE public.subscription_plan_prices
  ADD COLUMN IF NOT EXISTS list_amount_minor integer,
  ADD COLUMN IF NOT EXISTS discount_bps integer NOT NULL DEFAULT 0;
ALTER TABLE public.subscription_plan_features
  ADD COLUMN IF NOT EXISTS billing_interval varchar(10);
CREATE UNIQUE INDEX IF NOT EXISTS subscription_features_org_code_uq
  ON public.subscription_features (organization_id, feature_code);
CREATE UNIQUE INDEX IF NOT EXISTS subscription_plan_features_scope_uq
  ON public.subscription_plan_features (organization_id, plan_id, feature_id, COALESCE(billing_interval, '__all__'));
UPDATE public.subscription_plan_prices
SET list_amount_minor = unit_amount_minor
WHERE list_amount_minor IS NULL;
COMMIT;
