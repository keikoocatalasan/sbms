-- Additive migration for server-tracked login sessions.
BEGIN;
CREATE TABLE IF NOT EXISTS public.subscription_auth_sessions (
  id varchar(36) PRIMARY KEY,
  user_id varchar(36) NOT NULL,
  organization_id varchar(36) NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS subscription_auth_sessions_user_idx
  ON public.subscription_auth_sessions (user_id);
CREATE INDEX IF NOT EXISTS subscription_auth_sessions_org_idx
  ON public.subscription_auth_sessions (organization_id);
COMMIT;
