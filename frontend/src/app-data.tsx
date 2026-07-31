import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, apiMessage } from './api'
import type { AuthUser, Customer, DashboardSummary, Envelope, Invoice, MrrReport, Notification, Payment, Plan, Subscription, SystemSettings } from './types'

type AppDataValue = {
  user: AuthUser
  customers: Customer[]
  plans: Plan[]
  subscriptions: Subscription[]
  invoices: Invoice[]
  payments: Payment[]
  notifications: Notification[]
  settings: SystemSettings | null
  summary: DashboardSummary | null
  mrr: MrrReport | null
  loading: boolean
  error: string
  refresh: () => Promise<void>
  can: (scope: string) => boolean
}

const AppDataContext = createContext<AppDataValue | null>(null)

export function AppDataProvider({ user, children }: { user: AuthUser; children: React.ReactNode }) {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [plans, setPlans] = useState<Plan[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [payments, setPayments] = useState<Payment[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [settings, setSettings] = useState<SystemSettings | null>(null)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [mrr, setMrr] = useState<MrrReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const can = useCallback((scope: string) => user.scopes.includes(scope) || user.scopes.includes('subscription:admin'), [user.scopes])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const common = await Promise.all([
        api.get<Envelope<DashboardSummary>>('/dashboard/summary'),
        api.get<Envelope<Customer[]>>('/customers?page_size=100'),
        api.get<Envelope<Plan[]>>('/plans?page_size=100'),
        api.get<Envelope<Subscription[]>>('/subscriptions?page_size=100'),
        api.get<Envelope<Invoice[]>>('/invoices?page_size=100'),
        api.get<Envelope<Payment[]>>('/payments?page_size=100'),
        api.get<Envelope<Notification[]>>('/notifications?page_size=100'),
        api.get<Envelope<SystemSettings>>('/settings'),
      ])
      setSummary(common[0].data.data)
      setCustomers(common[1].data.data)
      setPlans(common[2].data.data)
      setSubscriptions(common[3].data.data)
      setInvoices(common[4].data.data)
      setPayments(common[5].data.data)
      setNotifications(common[6].data.data)
      setSettings(common[7].data.data)
      if (can('subscription:reports')) {
        const report = await api.get<Envelope<MrrReport>>('/reports/mrr')
        setMrr(report.data.data)
      } else {
        setMrr(null)
      }
    } catch (caught) {
      setError(apiMessage(caught, 'Unable to load subscription data.'))
    } finally {
      setLoading(false)
    }
  }, [can])

  useEffect(() => { void refresh() }, [refresh])

  const value = useMemo(() => ({ user, customers, plans, subscriptions, invoices, payments, notifications, settings, summary, mrr, loading, error, refresh, can }), [user, customers, plans, subscriptions, invoices, payments, notifications, settings, summary, mrr, loading, error, refresh, can])
  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>
}

export function useAppData() {
  const value = useContext(AppDataContext)
  if (!value) throw new Error('useAppData must be used inside AppDataProvider')
  return value
}
