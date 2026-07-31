export type Envelope<T> = { data: T; meta: Record<string, number>; request_id: string }

export type AuthUser = {
  id: string
  name: string
  email: string
  scopes: string[]
}

export type BaseRecord = {
  id: string
  created_at: string
  updated_at: string
}

export type Customer = BaseRecord & {
  customer_code: string
  customer_type: 'individual' | 'organization'
  display_name: string
  company_name: string | null
  email: string | null
  phone: string | null
  status: string
  notes: string | null
}

export type PlanPrice = BaseRecord & {
  plan_id: string
  price_code: string
  billing_interval: 'month' | 'year'
  interval_count: number
  currency: string
  unit_amount_minor: number
  setup_fee_minor: number
  status: string
  is_default: boolean
}

export type Plan = BaseRecord & {
  plan_code: string
  name: string
  description: string | null
  status: string
  trial_days: number
  is_featured: boolean
  display_order: number
  prices: PlanPrice[]
}

export type Subscription = BaseRecord & {
  subscription_number: string
  customer_id: string
  plan_id: string
  plan_price_id: string
  pending_plan_id: string | null
  pending_plan_price_id: string | null
  status: string
  starts_at: string
  trial_start_at: string | null
  trial_end_at: string | null
  current_period_end: string | null
  next_billing_at: string | null
  plan_change_effective_at: string | null
  auto_renew: boolean
  cancel_at_period_end: boolean
  cancellation_reason: string | null
  version: number
}

export type Invoice = BaseRecord & {
  invoice_number: string
  customer_id: string
  subscription_id: string | null
  status: string
  issue_date: string
  due_date: string
  currency: string
  notes: string | null
  amounts: { total_minor: number; paid_minor: number; balance_minor: number }
}

export type Payment = BaseRecord & {
  payment_reference: string
  customer_id: string
  payment_method: string
  status: string
  amount_minor: number
  currency: string
  received_at: string
  external_reference: string | null
  unallocated_minor: number
}

export type Notification = BaseRecord & {
  customer_id: string | null
  notification_type: string
  title: string
  body: string
  status: string
  sent_at: string
  read_at: string | null
}

export type SystemSettings = BaseRecord & {
  default_currency: string
  timezone: string
  invoice_due_days: number
  grace_period_days: number
  max_payment_retries: number
  retry_interval_days: number
  trial_reminder_days: number
  invoice_due_reminder_days: number
  auto_renew_default: boolean
  allow_partial_payments: boolean
  auto_generate_invoices: boolean
  invoice_prefix: string
  payment_prefix: string
  subscription_prefix: string
  customer_prefix: string
  enable_in_app_notifications: boolean
}

export type DashboardSummary = {
  metrics: {
    active_customers: number
    active_subscriptions: number
    collected_revenue_minor: number
    overdue_invoices: number
  }
  recent_subscriptions: Subscription[]
  recent_payments: Payment[]
}

export type MrrReport = {
  as_of: string
  currency: string
  mrr_minor: number
  at_risk_mrr_minor: number
  active_subscription_count: number
  calculation: string
}

