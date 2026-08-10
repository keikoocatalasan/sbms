import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Archive, Bell, CalendarDays, CheckCircle2, CircleDollarSign, CreditCard, FileText, LayoutDashboard, LineChart, Menu, Package, Plus, ReceiptText, RefreshCw, Settings, ShieldCheck, Users, WalletCards } from 'lucide-react'
import './styles.css'
import { api, apiMessage, clearSession, readUser, requestKey, saveSession, tokenKey } from './api'
import { AppDataProvider, useAppData } from './app-data'
import { ConfirmDialog, DataTable, downloadCsv, EmptyState, ErrorState, ExportButton, LoadingState, Metric, Modal, money, shortDate, Status, Toast } from './components'
import { CustomerDialog, CustomerProfileDialog, InvoiceDetailDialog, InvoiceDialog, NotificationDialog, PaymentDialog, PlanDialog, SubscriptionCommandDialog, SubscriptionDialog } from './dialogs'
import type { AuthUser, Customer, Envelope, Invoice, Notification, Payment, Plan, Subscription, SystemSettings } from './types'

type IconType = typeof LayoutDashboard
type ToastState = { message: string; error?: boolean } | null

const navItems: Array<{ path: string; label: string; icon: IconType; scope?: string }> = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/customers', label: 'Customers', icon: Users },
  { path: '/plans', label: 'Subscription Plans', icon: Package },
  { path: '/subscriptions', label: 'Subscriptions', icon: ReceiptText },
  { path: '/payments', label: 'Payments', icon: CreditCard },
  { path: '/invoices', label: 'Invoices', icon: FileText },
  { path: '/reports', label: 'Reports', icon: LineChart, scope: 'subscription:reports' },
  { path: '/notifications', label: 'Notifications', icon: Bell },
  { path: '/settings', label: 'Settings', icon: Settings, scope: 'subscription:admin' },
]

const pageCopy: Record<string, string> = {
  '/dashboard': 'Live overview of customers, billing, and subscription health',
  '/customers': 'Manage customer records and their billing relationships',
  '/plans': 'Create and manage the plans available for subscription',
  '/subscriptions': 'Manage trials, renewals, plan changes, and cancellations',
  '/payments': 'Record payments and allocate them to open invoices',
  '/invoices': 'Review, finalize, download, and void invoices',
  '/reports': 'Analyze revenue and recurring subscription performance',
  '/notifications': 'Send and review in-app account notifications',
  '/settings': 'Configure billing rules, numbering, and notifications',
}

function useFeedback() {
  const { refresh } = useAppData()
  const [toast, setToast] = useState<ToastState>(null)
  const done = async (message: string) => { await refresh(); setToast({ message }) }
  const fail = (error: unknown, fallback: string) => setToast({ message: apiMessage(error, fallback), error: true })
  const toastNode = toast && <Toast message={toast.message} error={toast.error} onClose={() => setToast(null)}/>
  return { done, fail, toastNode, setToast }
}

function Page({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  const location = useLocation()
  return <section className="content"><div className="page-head"><div><h1>{title}</h1><p>{pageCopy[location.pathname]}</p></div>{action && <div className="page-actions">{action}</div>}</div>{children}</section>
}

function Shell({ children }: { children: React.ReactNode }) {
  const { user, notifications, can } = useAppData()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const unread = notifications.filter(item => !item.read_at).length
  const allowedNav = navItems.filter(item => !item.scope || can(item.scope))
  const signOut = () => { clearSession(); navigate('/login', { replace: true }) }
  useEffect(() => setCollapsed(false), [location.pathname])
  return <div className={`shell ${collapsed ? 'collapsed' : ''}`}>
    <aside aria-label="Primary navigation">
      <Link className="brand" to="/dashboard" aria-label="Argo dashboard"><span className="brand-logo"><LayoutDashboard size={22}/></span><b>Subscription<br/>Management System</b></Link>
      <button type="button" className="hamburger" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed} onClick={() => setCollapsed(value => !value)}><Menu/></button>
      <nav>{allowedNav.map(({ path, label, icon: Icon }) => <Link key={path} to={path} className={path === location.pathname ? 'selected' : ''}><Icon size={20}/><span>{label}</span></Link>)}</nav>
      <div className="side-footer">© {new Date().getFullYear()} Argo Subscription System</div>
      <button type="button" className="logout" onClick={signOut}>Sign out</button>
    </aside>
    {collapsed && <button type="button" className="mobile-overlay" aria-label="Close navigation" onClick={() => setCollapsed(false)}/>} 
    <main><header><button type="button" className="mobile-menu" aria-label="Open navigation" onClick={() => setCollapsed(true)}><Menu/></button><div className="header-spacer"/><span className="date">{shortDate(new Date().toISOString())}</span><button type="button" className="notification-bell icon-button" aria-label={`${unread} unread notifications`} onClick={() => navigate('/notifications')}><Bell size={21}/>{unread > 0 && <b>{unread}</b>}</button><div className="profile-wrap"><button type="button" className="profile-button" aria-label="Open profile menu" aria-expanded={profileOpen} onClick={() => setProfileOpen(value => !value)}><span className="profile-photo">{user.name[0]}</span><span><b>{user.name}</b><small>{can('subscription:admin') ? 'Administrator' : 'Billing specialist'}</small></span></button>{profileOpen && <div className="profile-menu"><p>{user.email}</p><button type="button" onClick={() => { setProfileOpen(false); signOut() }}>Sign out</button></div>}</div></header>{children}</main>
  </div>
}

function DataBoundary({ children }: { children: React.ReactNode }) {
  const { loading, error, refresh } = useAppData()
  if (loading) return <LoadingState/>
  if (error) return <ErrorState message={error} onRetry={() => void refresh()}/>
  return <>{children}</>
}

function monthSeries(payments: Payment[], count = 6) {
  const now = new Date()
  const months = Array.from({ length: count }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - (count - index - 1), 1)
    return { key: `${date.getFullYear()}-${date.getMonth()}`, label: date.toLocaleString('en-PH', { month: 'short' }), revenue: 0 }
  })
  for (const payment of payments) {
    const date = new Date(payment.received_at)
    const target = months.find(item => item.key === `${date.getFullYear()}-${date.getMonth()}`)
    if (target && payment.status === 'completed') target.revenue += payment.amount_minor - payment.unallocated_minor
  }
  return months
}

function RevenueChart({ payments, months = 6 }: { payments: Payment[]; months?: number }) {
  const data = useMemo(() => monthSeries(payments, months), [payments, months])
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ left: 5, right: 8, top: 5, bottom: 0 }}><defs><linearGradient id="revenueFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#2563eb" stopOpacity=".22"/><stop offset="100%" stopColor="#2563eb" stopOpacity="0"/></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf1f7"/><XAxis dataKey="label" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false} tickFormatter={value => `₱${Math.round(value / 100000)}K`}/><Tooltip formatter={value => money(Number(value ?? 0))}/><Area type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2.5} fill="url(#revenueFill)"/></AreaChart></ResponsiveContainer>
}

function StatusChart({ subscriptions }: { subscriptions: Subscription[] }) {
  const colors: Record<string, string> = { active: '#2563eb', trialing: '#18b979', pending_payment: '#f5a31a', past_due: '#ef4444', cancelled: '#94a3b8', expired: '#64748b' }
  const data = Object.entries(subscriptions.reduce<Record<string, number>>((result, item) => ({ ...result, [item.status]: (result[item.status] ?? 0) + 1 }), {})).map(([name, value]) => ({ name, value, color: colors[name] ?? '#7c3aed' }))
  if (!data.length) return <EmptyState title="No subscriptions yet" copy="Create a subscription to populate this chart."/>
  return <div className="status-body"><div className="donut"><ResponsiveContainer width={205} height={205}><PieChart><Pie data={data} dataKey="value" nameKey="name" innerRadius={59} outerRadius={90} paddingAngle={1}>{data.map(item => <Cell key={item.name} fill={item.color}/>)}</Pie></PieChart></ResponsiveContainer><div className="donut-total"><strong>{subscriptions.length}</strong><span>Total</span></div></div><div className="legend">{data.map(item => <div key={item.name}><span><i style={{ background: item.color }}/>{item.name.replaceAll('_', ' ')}</span><b>{item.value} ({((item.value / subscriptions.length) * 100).toFixed(0)}%)</b></div>)}</div></div>
}

function DashboardPage() {
  const { customers, subscriptions, invoices, payments, plans, summary, can } = useAppData()
  const { done, toastNode } = useFeedback()
  const [newSubscription, setNewSubscription] = useState(false)
  const [months, setMonths] = useState(6)
  const customerById = Object.fromEntries(customers.map(item => [item.id, item]))
  const planById = Object.fromEntries(plans.map(item => [item.id, item]))
  const outstanding = invoices.reduce((sum, item) => sum + item.amounts.balance_minor, 0)
  return <Page title="Dashboard" action={can('subscription:billing') && <button className="button primary" onClick={() => setNewSubscription(true)}><Plus size={18}/>New subscription</button>}><DataBoundary>
    <div className="metric-grid"><Metric icon={<Users/>} label="Active customers" value={String(summary?.metrics.active_customers ?? customers.filter(item => item.status === 'active').length)} note={`${customers.length} total`} tone="green"/><Metric icon={<WalletCards/>} label="Active subscriptions" value={String(summary?.metrics.active_subscriptions ?? subscriptions.filter(item => item.status === 'active').length)} note={`${subscriptions.filter(item => item.status === 'trialing').length} trialing`}/><Metric icon={<CircleDollarSign/>} label="Collected revenue" value={money(summary?.metrics.collected_revenue_minor ?? 0)} note="Allocated payments" tone="orange"/><Metric icon={<CalendarDays/>} label="Outstanding balance" value={money(outstanding)} note={`${invoices.filter(item => item.amounts.balance_minor > 0).length} open invoices`} tone="red"/></div>
    <div className="dashboard-charts"><section className="card chart-card"><div className="card-head"><h2>Revenue overview</h2><select aria-label="Revenue period" value={months} onChange={event => setMonths(Number(event.target.value))}><option value={6}>Last 6 months</option><option value={12}>Last 12 months</option></select></div><RevenueChart payments={payments} months={months}/></section><section className="card status-card"><h2>Subscription status</h2><StatusChart subscriptions={subscriptions}/></section></div>
    <div className="dashboard-tables"><section className="card compact-table"><div className="card-head"><h2>Recent subscriptions</h2><Link to="/subscriptions">View all</Link></div><table><thead><tr><th>Customer</th><th>Plan</th><th>Status</th></tr></thead><tbody>{subscriptions.slice(0, 5).map(item => <tr key={item.id}><td>{customerById[item.customer_id]?.display_name ?? 'Unknown'}</td><td>{planById[item.plan_id]?.name ?? 'Unknown'}</td><td><Status>{item.status}</Status></td></tr>)}{!subscriptions.length && <tr><td colSpan={3}>No subscriptions yet.</td></tr>}</tbody></table></section><section className="card compact-table"><div className="card-head"><h2>Recent payments</h2><Link to="/payments">View all</Link></div><table><thead><tr><th>Customer</th><th>Amount</th><th>Status</th></tr></thead><tbody>{payments.slice(0, 5).map(item => <tr key={item.id}><td>{customerById[item.customer_id]?.display_name ?? 'Unknown'}</td><td>{money(item.amount_minor, item.currency)}</td><td><Status>{item.status}</Status></td></tr>)}{!payments.length && <tr><td colSpan={3}>No payments yet.</td></tr>}</tbody></table></section></div>
  </DataBoundary>{newSubscription && <SubscriptionDialog onClose={() => setNewSubscription(false)} onDone={done}/>} {toastNode}</Page>
}

function CustomersPage() {
  const { customers, subscriptions, plans, payments, invoices, can, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [dialog, setDialog] = useState<'new' | Customer | null>(null)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [profile, setProfile] = useState<Customer | null>(null)
  const [archive, setArchive] = useState<Customer | null>(null)
  const [busy, setBusy] = useState(false)
  const activeSubscription = (customer: Customer) => subscriptions.find(item => item.customer_id === customer.id && ['active', 'trialing', 'pending_payment', 'past_due'].includes(item.status))
  const planName = (customer: Customer) => plans.find(plan => plan.id === activeSubscription(customer)?.plan_id)?.name ?? 'No plan'
  async function archiveCustomer() { if (!archive) return; setBusy(true); try { await api.post(`/customers/${archive.id}/archive`); await refresh(); setArchive(null); done('Customer archived.'); } catch (caught) { fail(caught, 'Unable to archive customer.') } finally { setBusy(false) } }
  const selected = selectedCustomer ?? customers[0] ?? null
  return <Page title="Customers" action={can('subscription:billing') && <button className="button primary" onClick={() => setDialog('new')}><Plus size={18}/>Add customer</button>}><DataBoundary><div className="customer-layout"><section className="card table-card"><DataTable rows={customers} rowKey={row => row.id} searchPlaceholder="Search customers" searchText={row => `${row.customer_code} ${row.display_name} ${row.email ?? ''} ${row.phone ?? ''}`} statusOf={row => row.status} statuses={['active', 'archived']} planOf={planName} planOptions={plans.map(plan => plan.name)} onRowClick={setSelectedCustomer} columns={[{ key: 'customer', label: 'Customer', render: row => <span className="person"><i className="avatar-square">{row.display_name.slice(0, 2).toUpperCase()}</i><span>{row.display_name}<small>{row.customer_code}</small></span></span> }, { key: 'email', label: 'Email', render: row => row.email ?? '—' }, { key: 'phone', label: 'Phone', render: row => row.phone ?? '—' }, { key: 'plan', label: 'Plan', render: planName }, { key: 'joined', label: 'Joined', render: row => shortDate(row.created_at) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }]} actions={row => [{ label: 'View profile', onClick: () => setProfile(row) }, ...(can('subscription:billing') ? [{ label: 'Edit customer', onClick: () => setDialog(row) }] : []), ...(can('subscription:admin') && row.status === 'active' ? [{ label: 'Archive customer', danger: true, onClick: () => setArchive(row) }] : [])]}/></section>{selected && <aside className="customer-profile card"><div className="profile-summary"><span className="big-avatar">{selected.display_name.slice(0, 2).toUpperCase()}</span><div><h2>{selected.display_name}</h2><p>{selected.email ?? 'No email'}</p><Status>{selected.status}</Status></div></div><hr/><h3>Subscription summary</h3><div className="summary-box"><div><span>Current plan</span><b>{planName(selected)}</b></div><div><span>Status</span><b>{activeSubscription(selected)?.status.replaceAll('_', ' ') ?? 'None'}</b></div><div><span>Next billing</span><b>{shortDate(activeSubscription(selected)?.next_billing_at)}</b></div><hr/><div><span>Payments</span><b>{payments.filter(item => item.customer_id === selected.id).length}</b></div><div><span>Total paid</span><b>{money(payments.filter(item => item.customer_id === selected.id).reduce((sum, item) => sum + item.amount_minor - item.unallocated_minor, 0))}</b></div><div><span>Outstanding</span><b>{money(invoices.filter(item => item.customer_id === selected.id).reduce((sum, item) => sum + item.amounts.balance_minor, 0))}</b></div></div><button className="outline" onClick={() => setProfile(selected)}>View full profile</button></aside>}</div></DataBoundary>
    {dialog && <CustomerDialog customer={dialog === 'new' ? undefined : dialog} onClose={() => setDialog(null)} onDone={done}/>} {profile && <CustomerProfileDialog customer={profile} onClose={() => setProfile(null)}/>} {archive && <ConfirmDialog title="Archive customer" message={`Archive ${archive.display_name}? Existing billing history is preserved, but new subscriptions are blocked.`} confirmLabel="Archive" danger busy={busy} onCancel={() => setArchive(null)} onConfirm={() => void archiveCustomer()}/>} {toastNode}
  </Page>
}

function PlansPage() {
  const { plans, subscriptions, can, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [dialog, setDialog] = useState<'new' | Plan | null>(null)
  const [statusTarget, setStatusTarget] = useState<Plan | null>(null)
  const [busy, setBusy] = useState(false)
  const subscriberCount = (plan: Plan) => subscriptions.filter(item => item.plan_id === plan.id && !['cancelled', 'expired'].includes(item.status)).length
  const defaultPrice = (plan: Plan) => plan.prices.find(price => price.is_default && price.status === 'active') ?? plan.prices.find(price => price.status === 'active')
  async function changeStatus() { if (!statusTarget) return; setBusy(true); const next = statusTarget.status === 'active' ? 'archived' : 'active'; try { await api.patch(`/plans/${statusTarget.id}/status`, { status: next }); await refresh(); setStatusTarget(null); done(`Plan ${next}.`) } catch (caught) { fail(caught, 'Unable to change the plan status.') } finally { setBusy(false) } }
  return <Page title="Subscription Plans" action={can('subscription:admin') && <button className="button primary" onClick={() => setDialog('new')}><Plus size={18}/>Add plan</button>}><DataBoundary>
    {plans.length ? <section className="plan-grid">{plans.map((plan, index) => { const price = defaultPrice(plan); return <article className={`plan-card tone-${index % 4} ${plan.is_featured ? 'featured' : ''}`} key={plan.id}><div className="plan-card-head"><span className="plan-icon"><Package size={23}/></span>{plan.is_featured && <span className="featured-label">Featured</span>}</div><h2>{plan.name}</h2><p>{plan.description || 'No plan description has been provided.'}</p><div className="prices">{price ? <><b>{money(price.unit_amount_minor, price.currency)}</b><span>/ {price.billing_interval}</span></> : <b>No active price</b>}</div><ul><li>✓ {plan.trial_days ? `${plan.trial_days}-day trial` : 'No trial'}</li><li>✓ {price?.billing_interval === 'year' ? 'Annual billing' : 'Monthly billing'}</li><li>✓ {subscriberCount(plan)} active subscriber{subscriberCount(plan) === 1 ? '' : 's'}</li></ul><div className="plan-footer"><Status>{plan.status}</Status>{can('subscription:admin') && <><button type="button" className="icon-button" aria-label={`Edit ${plan.name}`} onClick={() => setDialog(plan)}><Settings size={17}/></button><button type="button" className="icon-button" aria-label={`${plan.status === 'active' ? 'Archive' : 'Activate'} ${plan.name}`} onClick={() => setStatusTarget(plan)}>{plan.status === 'active' ? <Archive size={17}/> : <CheckCircle2 size={17}/>}</button></>}</div></article> })}</section> : <EmptyState title="No plans" copy="Create the first plan and price to start subscriptions."/>}
    <section className="card table-card"><DataTable rows={plans} rowKey={row => row.id} searchPlaceholder="Search plans" searchText={row => `${row.plan_code} ${row.name} ${row.description ?? ''}`} statusOf={row => row.status} statuses={['draft', 'active', 'inactive', 'archived']} columns={[{ key: 'name', label: 'Plan', render: row => <><b>{row.name}</b><small className="stacked">{row.plan_code}</small></> }, { key: 'price', label: 'Current price', render: row => { const price = defaultPrice(row); return price ? `${money(price.unit_amount_minor, price.currency)} / ${price.billing_interval}` : '—' } }, { key: 'trial', label: 'Trial', render: row => `${row.trial_days} days` }, { key: 'subscribers', label: 'Subscribers', render: subscriberCount }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'created', label: 'Created', render: row => shortDate(row.created_at) }]} actions={can('subscription:admin') ? row => [{ label: 'Edit plan', onClick: () => setDialog(row) }, { label: row.status === 'active' ? 'Archive plan' : 'Activate plan', danger: row.status === 'active', onClick: () => setStatusTarget(row) }] : undefined}/></section>
  </DataBoundary>{dialog && <PlanDialog plan={dialog === 'new' ? undefined : dialog} onClose={() => setDialog(null)} onDone={done}/>} {statusTarget && <ConfirmDialog title={statusTarget.status === 'active' ? 'Archive plan' : 'Activate plan'} message={statusTarget.status === 'active' ? `Archive ${statusTarget.name}? Existing subscriptions continue, but the plan cannot be selected for new subscriptions.` : `Make ${statusTarget.name} available for new subscriptions?`} confirmLabel={statusTarget.status === 'active' ? 'Archive' : 'Activate'} danger={statusTarget.status === 'active'} busy={busy} onCancel={() => setStatusTarget(null)} onConfirm={() => void changeStatus()}/>} {toastNode}</Page>
}

function trialLabel(subscription: Subscription) {
  if (subscription.status !== 'trialing' || !subscription.trial_end_at) return shortDate(subscription.current_period_end ?? subscription.next_billing_at)
  const days = Math.max(0, Math.ceil((new Date(subscription.trial_end_at).getTime() - Date.now()) / 86400000))
  return `${days} day${days === 1 ? '' : 's'} left`
}

function SubscriptionsPage() {
  const { subscriptions, customers, plans, can, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [createOpen, setCreateOpen] = useState(false)
  const [command, setCommand] = useState<{ subscription: Subscription; mode: 'change-plan' | 'schedule-cancel' | 'cancel-now' } | null>(null)
  const [detail, setDetail] = useState<Subscription | null>(null)
  const customerName = (item: Subscription) => customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Unknown customer'
  const planName = (item: Subscription) => plans.find(plan => plan.id === item.plan_id)?.name ?? 'Unknown plan'
  async function revoke(item: Subscription) { try { await api.post(`/subscriptions/${item.id}/revoke-cancellation`, { expected_version: item.version, reason: 'Cancellation revoked from the dashboard' }); await refresh(); done('Scheduled cancellation revoked.') } catch (caught) { fail(caught, 'Unable to revoke cancellation.') } }
  async function toggleRenewal(item: Subscription) { try { await api.patch(`/subscriptions/${item.id}/auto-renew`, { expected_version: item.version, auto_renew: !item.auto_renew }); await refresh(); done(`Auto renewal ${item.auto_renew ? 'disabled' : 'enabled'}.`) } catch (caught) { fail(caught, 'Unable to change auto renewal.') } }
  const openStatuses = ['trialing', 'pending_payment', 'active', 'past_due', 'suspended']
  return <Page title="Subscriptions" action={can('subscription:billing') && <button className="button primary" onClick={() => setCreateOpen(true)}><Plus size={18}/>New subscription</button>}><DataBoundary>
    <div className="metric-grid"><Metric icon={<ReceiptText/>} label="Total subscriptions" value={String(subscriptions.length)}/><Metric icon={<CheckCircle2/>} label="Active" value={String(subscriptions.filter(item => item.status === 'active').length)} tone="green"/><Metric icon={<CalendarDays/>} label="Trialing" value={String(subscriptions.filter(item => item.status === 'trialing').length)} tone="orange"/><Metric icon={<CircleDollarSign/>} label="Needs payment" value={String(subscriptions.filter(item => ['pending_payment', 'past_due'].includes(item.status)).length)} tone="red"/></div>
    <section className="card table-card"><DataTable rows={subscriptions} rowKey={row => row.id} searchPlaceholder="Search subscriptions" searchText={row => `${row.subscription_number} ${customerName(row)} ${planName(row)}`} statusOf={row => row.status} statuses={['trialing', 'pending_payment', 'active', 'past_due', 'suspended', 'cancelled', 'expired']} planOf={planName} planOptions={plans.map(plan => plan.name)} columns={[{ key: 'number', label: 'Subscription', render: row => row.subscription_number }, { key: 'customer', label: 'Customer', render: customerName }, { key: 'plan', label: 'Plan', render: planName }, { key: 'period', label: 'Trial / period end', render: trialLabel }, { key: 'renewal', label: 'Auto renewal', render: row => row.auto_renew ? 'On' : 'Off' }, { key: 'status', label: 'Status', render: row => <><Status>{row.status}</Status>{row.cancel_at_period_end && <small className="stacked warning-text">Cancels at period end</small>}</> }]} actions={row => [{ label: 'View details', onClick: () => setDetail(row) }, ...(can('subscription:billing') && openStatuses.includes(row.status) ? [{ label: 'Change plan at period end', onClick: () => setCommand({ subscription: row, mode: 'change-plan' as const }) }, { label: row.auto_renew ? 'Disable auto renewal' : 'Enable auto renewal', onClick: () => void toggleRenewal(row) }, ...(row.cancel_at_period_end ? [{ label: 'Revoke scheduled cancellation', onClick: () => void revoke(row) }] : [{ label: 'Cancel at period end', danger: true, onClick: () => setCommand({ subscription: row, mode: 'schedule-cancel' as const }) }])] : []), ...(can('subscription:admin') && !['cancelled', 'expired'].includes(row.status) ? [{ label: 'Cancel immediately', danger: true, onClick: () => setCommand({ subscription: row, mode: 'cancel-now' as const }) }] : [])]}/></section>
  </DataBoundary>{createOpen && <SubscriptionDialog onClose={() => setCreateOpen(false)} onDone={done}/>} {command && <SubscriptionCommandDialog subscription={command.subscription} mode={command.mode} onClose={() => setCommand(null)} onDone={done}/>} {detail && <Modal title={detail.subscription_number} description={`${customerName(detail)} · ${planName(detail)}`} onClose={() => setDetail(null)}><div className="detail-list"><div><span>Status</span><Status>{detail.status}</Status></div><div><span>Started</span><b>{shortDate(detail.starts_at)}</b></div><div><span>Trial ends</span><b>{shortDate(detail.trial_end_at)}</b></div><div><span>Current period ends</span><b>{shortDate(detail.current_period_end)}</b></div><div><span>Next billing</span><b>{shortDate(detail.next_billing_at)}</b></div><div><span>Auto renewal</span><b>{detail.auto_renew ? 'Enabled' : 'Disabled'}</b></div>{detail.pending_plan_id && <div><span>Pending plan change</span><b>{plans.find(plan => plan.id === detail.pending_plan_id)?.name ?? 'Scheduled'}</b></div>}</div><div className="modal-actions"><button className="button primary" onClick={() => setDetail(null)}>Done</button></div></Modal>} {toastNode}</Page>
}

function PaymentsPage() {
  const { payments, customers, can } = useAppData()
  const { done, toastNode } = useFeedback()
  const [open, setOpen] = useState(false)
  const customerName = (item: Payment) => customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Unknown customer'
  const total = payments.reduce((sum, item) => sum + item.amount_minor, 0)
  const allocated = payments.reduce((sum, item) => sum + item.amount_minor - item.unallocated_minor, 0)
  const unallocated = payments.reduce((sum, item) => sum + item.unallocated_minor, 0)
  const exportRows = () => downloadCsv('payments.csv', [['Reference', 'Customer', 'Method', 'Amount', 'Allocated', 'Status', 'Date'], ...payments.map(item => [item.payment_reference, customerName(item), item.payment_method, money(item.amount_minor, item.currency), money(item.amount_minor - item.unallocated_minor, item.currency), item.status, shortDate(item.received_at)])])
  return <Page title="Payments" action={<>{can('subscription:billing') && <button className="button primary" onClick={() => setOpen(true)}><Plus size={18}/>Add payment</button>}<ExportButton onClick={exportRows}/></>}><DataBoundary><div className="metric-grid"><Metric icon={<WalletCards/>} label="Recorded payments" value={money(total)} note={`${payments.length} transactions`} tone="green"/><Metric icon={<CircleDollarSign/>} label="Allocated" value={money(allocated)} note="Applied to invoices"/><Metric icon={<CalendarDays/>} label="Unallocated credit" value={money(unallocated)} note="Available on account" tone="orange"/><Metric icon={<CreditCard/>} label="Manual payments" value={String(payments.filter(item => item.payment_method === 'manual_bank' || item.payment_method === 'manual_cash').length)} tone="purple"/></div><div className="dashboard-charts one-chart"><section className="card chart-card"><div className="card-head"><h2>Allocated revenue</h2></div><RevenueChart payments={payments}/></section></div><section className="card table-card"><DataTable rows={payments} rowKey={row => row.id} searchPlaceholder="Search payments" searchText={row => `${row.payment_reference} ${row.external_reference ?? ''} ${customerName(row)} ${row.payment_method}`} statusOf={row => row.status} statuses={['completed', 'void']} columns={[{ key: 'reference', label: 'Reference', render: row => <><b>{row.payment_reference}</b><small className="stacked">{row.external_reference ?? 'No external reference'}</small></> }, { key: 'customer', label: 'Customer', render: customerName }, { key: 'method', label: 'Method', render: row => row.payment_method.replaceAll('_', ' ') }, { key: 'amount', label: 'Amount', render: row => money(row.amount_minor, row.currency) }, { key: 'allocated', label: 'Allocated', render: row => money(row.amount_minor - row.unallocated_minor, row.currency) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'date', label: 'Received', render: row => shortDate(row.received_at) }]}/></section></DataBoundary>{open && <PaymentDialog onClose={() => setOpen(false)} onDone={done}/>} {toastNode}</Page>
}

function InvoicesPage() {
  const { invoices, customers, can, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [createOpen, setCreateOpen] = useState(false)
  const [detail, setDetail] = useState<Invoice | null>(null)
  const [command, setCommand] = useState<{ invoice: Invoice; type: 'finalize' | 'void' } | null>(null)
  const [busy, setBusy] = useState(false)
  const customerName = (item: Invoice) => customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Unknown customer'
  async function runCommand() { if (!command) return; setBusy(true); try { if (command.type === 'finalize') await api.post(`/invoices/${command.invoice.id}/finalize`); else await api.post(`/invoices/${command.invoice.id}/void`, { expected_version: 1, reason: 'Voided from invoice management' }); await refresh(); setCommand(null); done(`Invoice ${command.type === 'finalize' ? 'finalized' : 'voided'}.`) } catch (caught) { fail(caught, 'Unable to update the invoice.') } finally { setBusy(false) } }
  const exportRows = () => downloadCsv('invoices.csv', [['Invoice', 'Customer', 'Total', 'Paid', 'Balance', 'Due', 'Status'], ...invoices.map(item => [item.invoice_number, customerName(item), money(item.amounts.total_minor, item.currency), money(item.amounts.paid_minor, item.currency), money(item.amounts.balance_minor, item.currency), shortDate(item.due_date), item.status])])
  return <Page title="Invoices" action={<>{can('subscription:billing') && <button className="button primary" onClick={() => setCreateOpen(true)}><Plus size={18}/>Generate invoice</button>}<ExportButton onClick={exportRows}/></>}><DataBoundary><div className="metric-grid"><Metric icon={<FileText/>} label="Total invoices" value={String(invoices.length)}/><Metric icon={<CheckCircle2/>} label="Paid" value={String(invoices.filter(item => item.status === 'paid').length)} tone="green"/><Metric icon={<CalendarDays/>} label="Open balance" value={money(invoices.reduce((sum, item) => sum + item.amounts.balance_minor, 0))} tone="orange"/><Metric icon={<CircleDollarSign/>} label="Overdue" value={String(invoices.filter(item => item.status === 'overdue').length)} tone="red"/></div><section className="card table-card"><DataTable rows={invoices} rowKey={row => row.id} searchPlaceholder="Search invoices" searchText={row => `${row.invoice_number} ${customerName(row)} ${row.notes ?? ''}`} statusOf={row => row.status} statuses={['draft', 'open', 'paid', 'overdue', 'void']} columns={[{ key: 'number', label: 'Invoice', render: row => row.invoice_number }, { key: 'customer', label: 'Customer', render: customerName }, { key: 'total', label: 'Total', render: row => money(row.amounts.total_minor, row.currency) }, { key: 'balance', label: 'Balance', render: row => money(row.amounts.balance_minor, row.currency) }, { key: 'due', label: 'Due', render: row => shortDate(row.due_date) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }]} actions={row => [{ label: 'View and download', onClick: () => setDetail(row) }, ...(can('subscription:billing') && row.status === 'draft' ? [{ label: 'Finalize invoice', onClick: () => setCommand({ invoice: row, type: 'finalize' as const }) }] : []), ...(can('subscription:admin') && !['paid', 'void'].includes(row.status) ? [{ label: 'Void invoice', danger: true, onClick: () => setCommand({ invoice: row, type: 'void' as const }) }] : [])]}/></section></DataBoundary>{createOpen && <InvoiceDialog onClose={() => setCreateOpen(false)} onDone={done}/>} {detail && <InvoiceDetailDialog invoice={detail} onClose={() => setDetail(null)}/>} {command && <ConfirmDialog title={command.type === 'finalize' ? 'Finalize invoice' : 'Void invoice'} message={command.type === 'finalize' ? `Finalize ${command.invoice.invoice_number}? Its amount becomes payable.` : `Void ${command.invoice.invoice_number}? Its balance will no longer be collectible.`} confirmLabel={command.type === 'finalize' ? 'Finalize' : 'Void'} danger={command.type === 'void'} busy={busy} onCancel={() => setCommand(null)} onConfirm={() => void runCommand()}/>} {toastNode}</Page>
}

function ReportsPage() {
  const { payments, customers, subscriptions, plans, mrr } = useAppData()
  const [months, setMonths] = useState(6)
  const allocated = payments.reduce((sum, item) => sum + item.amount_minor - item.unallocated_minor, 0)
  const priceById = Object.fromEntries(plans.flatMap(plan => plan.prices.map(price => [price.id, price])))
  const planRevenue = plans.map(plan => ({ name: plan.name, amount: subscriptions.filter(item => item.plan_id === plan.id && ['active', 'trialing', 'past_due'].includes(item.status)).reduce((sum, item) => { const price = priceById[item.plan_price_id]; return sum + (price?.billing_interval === 'year' ? Math.round(price.unit_amount_minor / 12) : price?.unit_amount_minor ?? 0) }, 0) })).sort((a, b) => b.amount - a.amount)
  const customerRevenue = customers.map(customer => ({ name: customer.display_name, amount: payments.filter(item => item.customer_id === customer.id).reduce((sum, item) => sum + item.amount_minor - item.unallocated_minor, 0) })).filter(item => item.amount > 0).sort((a, b) => b.amount - a.amount)
  const exportReport = () => downloadCsv('subscription-report.csv', [['Metric', 'Value'], ['Allocated revenue', money(allocated)], ['MRR', money(mrr?.mrr_minor ?? 0)], ['Active subscriptions', mrr?.active_subscription_count ?? 0], ['Customers', customers.length], [], ['Plan', 'Estimated MRR'], ...planRevenue.map(item => [item.name, money(item.amount)])])
  return <Page title="Reports" action={<><label className="inline-select"><span>Range</span><select aria-label="Report period" value={months} onChange={event => setMonths(Number(event.target.value))}><option value={6}>6 months</option><option value={12}>12 months</option></select></label><ExportButton label="Export report" onClick={exportReport}/></>}><DataBoundary><div className="report-metrics"><Metric icon={<CircleDollarSign/>} label="Allocated revenue" value={money(allocated)}/><Metric icon={<ReceiptText/>} label="Monthly recurring revenue" value={money(mrr?.mrr_minor ?? 0)} tone="purple"/><Metric icon={<Users/>} label="Customers" value={String(customers.length)} tone="green"/><Metric icon={<CreditCard/>} label="Active subscriptions" value={String(mrr?.active_subscription_count ?? 0)} tone="orange"/><Metric icon={<ShieldCheck/>} label="At-risk MRR" value={money(mrr?.at_risk_mrr_minor ?? 0)} tone="red"/></div><div className="report-charts"><section className="card chart-card"><div className="card-head"><h2>Collected revenue</h2><small>Only invoice-allocated payments are counted</small></div><RevenueChart payments={payments} months={months}/></section><section className="card status-card"><h2>Subscription status</h2><StatusChart subscriptions={subscriptions}/></section></div><div className="report-panels"><section className="card mini-report"><h2>Estimated MRR by plan</h2>{planRevenue.length ? planRevenue.map(item => <div key={item.name}><span>{item.name}</span><b>{money(item.amount)}</b></div>) : <p>No subscription revenue.</p>}</section><section className="card mini-report"><h2>Top customers by allocated revenue</h2>{customerRevenue.length ? customerRevenue.slice(0, 8).map(item => <div key={item.name}><span>{item.name}</span><b>{money(item.amount)}</b></div>) : <p>No allocated payments.</p>}</section></div></DataBoundary></Page>
}

function NotificationsPage() {
  const { notifications, customers, can, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [createOpen, setCreateOpen] = useState(false)
  const [selected, setSelected] = useState<Notification | null>(null)
  const recipient = (item: Notification) => item.customer_id ? customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Unknown customer' : 'All users'
  const readStatus = (item: Notification) => item.read_at ? 'read' : 'unread'
  async function markRead(item: Notification) { try { await api.post(`/notifications/${item.id}/mark-read`); await refresh(); setSelected(current => current?.id === item.id ? { ...item, read_at: new Date().toISOString() } : current); done('Notification marked as read.') } catch (caught) { fail(caught, 'Unable to mark the notification as read.') } }
  return <Page title="Notifications" action={can('subscription:billing') && <button className="button primary" onClick={() => setCreateOpen(true)}><Plus size={18}/>New notification</button>}><DataBoundary><div className="metric-grid"><Metric icon={<Bell/>} label="Total notifications" value={String(notifications.length)}/><Metric icon={<CheckCircle2/>} label="Read" value={String(notifications.filter(item => item.read_at).length)} tone="green"/><Metric icon={<CalendarDays/>} label="Unread" value={String(notifications.filter(item => !item.read_at).length)} tone="orange"/><Metric icon={<Users/>} label="Customer-specific" value={String(notifications.filter(item => item.customer_id).length)} tone="purple"/></div><div className="notification-layout"><section className="card table-card"><DataTable rows={notifications} rowKey={row => row.id} searchPlaceholder="Search notifications" searchText={row => `${row.title} ${row.body} ${row.notification_type} ${recipient(row)}`} statusOf={readStatus} statuses={['unread', 'read']} onRowClick={setSelected} columns={[{ key: 'message', label: 'Notification', render: row => <><b>{row.title}</b><small className="stacked truncate">{row.body}</small></> }, { key: 'type', label: 'Type', render: row => row.notification_type.replaceAll('_', ' ') }, { key: 'recipient', label: 'Recipient', render: recipient }, { key: 'date', label: 'Sent', render: row => shortDate(row.sent_at) }, { key: 'status', label: 'Status', render: row => <Status>{readStatus(row)}</Status> }]} actions={row => [{ label: 'View notification', onClick: () => setSelected(row) }, ...(!row.read_at ? [{ label: 'Mark as read', onClick: () => void markRead(row) }] : [])]}/></section><aside className="notification-preview card">{selected ? <><div className="preview-icon"><Bell size={44}/></div><Status>{readStatus(selected)}</Status><h2>{selected.title}</h2><p>{selected.body}</p><dl><dt>Recipient</dt><dd>{recipient(selected)}</dd><dt>Sent</dt><dd>{shortDate(selected.sent_at)}</dd></dl>{!selected.read_at && <button className="button primary" onClick={() => void markRead(selected)}>Mark as read</button>}</> : <><Bell size={70}/><h2>Notification preview</h2><p>Select a row to read its full message.</p></>}</aside></div></DataBoundary>{createOpen && <NotificationDialog onClose={() => setCreateOpen(false)} onDone={done}/>} {toastNode}</Page>
}

function SettingsPage() {
  const { settings, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [form, setForm] = useState<SystemSettings | null>(settings)
  const [busy, setBusy] = useState(false)
  const [maintenance, setMaintenance] = useState<'preview' | 'run' | null>(null)
  useEffect(() => setForm(settings), [settings])
  if (!form) return <Page title="Settings"><DataBoundary><EmptyState title="Settings unavailable" copy="No organization settings record was returned."/></DataBoundary></Page>
  const update = <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => setForm(current => current ? { ...current, [key]: value } : current)
  async function save(event: FormEvent) { event.preventDefault(); if (!form) return; setBusy(true); try { const { default_currency, timezone, invoice_due_days, grace_period_days, allow_partial_payments, auto_renew_default, auto_generate_invoices, invoice_prefix, payment_prefix, subscription_prefix, customer_prefix } = form; await api.patch('/settings', { default_currency, timezone, invoice_due_days, grace_period_days, allow_partial_payments, auto_renew_default, auto_generate_invoices, invoice_prefix, payment_prefix, subscription_prefix, customer_prefix }); await refresh(); done('Settings saved.'); } catch (caught) { fail(caught, 'Unable to save settings.') } finally { setBusy(false) } }
  async function processDue() { if (!maintenance) return; setBusy(true); try { const response = await api.post('/maintenance/process-due', { dry_run: maintenance === 'preview', batch_size: 100 }, { headers: { 'Idempotency-Key': requestKey() } }); await refresh(); done(`${maintenance === 'preview' ? 'Preview complete' : 'Due processing complete'}: ${JSON.stringify(response.data.data)}`); setMaintenance(null) } catch (caught) { fail(caught, 'Unable to process due subscriptions.') } finally { setBusy(false) } }
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  return <Page title="Settings"><DataBoundary><div className="settings-layout"><aside className="settings-nav card"><button onClick={() => jump('general-settings')}><Settings size={17}/>General</button><button onClick={() => jump('billing-settings')}><ReceiptText size={17}/>Billing</button><button onClick={() => jump('numbering-settings')}><FileText size={17}/>Numbering</button><button onClick={() => jump('maintenance-settings')}><RefreshCw size={17}/>Maintenance</button></aside><form className="settings-cards" onSubmit={save}><section id="general-settings" className="card setting-card"><h2><Settings size={20}/>General</h2><label>Default currency<select value={form.default_currency} onChange={event => update('default_currency', event.target.value)}><option value="PHP">PHP — Philippine Peso</option><option value="USD">USD — US Dollar</option></select></label><label>Time zone<select value={form.timezone} onChange={event => update('timezone', event.target.value)}><option value="Asia/Manila">Asia/Manila</option><option value="UTC">UTC</option></select></label></section><section id="billing-settings" className="card setting-card"><h2><ReceiptText size={20}/>Billing rules</h2><label>Invoice due days<input type="number" min="0" max="365" value={form.invoice_due_days} onChange={event => update('invoice_due_days', Number(event.target.value))}/></label><label>Grace period days<input type="number" min="0" max="365" value={form.grace_period_days} onChange={event => update('grace_period_days', Number(event.target.value))}/></label><label className="toggle-row"><span>Auto renewal by default</span><input type="checkbox" checked={form.auto_renew_default} onChange={event => update('auto_renew_default', event.target.checked)}/></label><label className="toggle-row"><span>Allow partial payments</span><input type="checkbox" checked={form.allow_partial_payments} onChange={event => update('allow_partial_payments', event.target.checked)}/></label><label className="toggle-row"><span>Auto-generate renewal invoices</span><input type="checkbox" checked={form.auto_generate_invoices} onChange={event => update('auto_generate_invoices', event.target.checked)}/></label></section><section id="numbering-settings" className="card setting-card"><h2><FileText size={20}/>Record prefixes</h2><label>Invoice prefix<input required pattern="[A-Z]{2,8}" value={form.invoice_prefix} onChange={event => update('invoice_prefix', event.target.value.toUpperCase())}/></label><label>Payment prefix<input required pattern="[A-Z]{2,8}" value={form.payment_prefix} onChange={event => update('payment_prefix', event.target.value.toUpperCase())}/></label><label>Subscription prefix<input required pattern="[A-Z]{2,8}" value={form.subscription_prefix} onChange={event => update('subscription_prefix', event.target.value.toUpperCase())}/></label><label>Customer prefix<input required pattern="[A-Z]{2,8}" value={form.customer_prefix} onChange={event => update('customer_prefix', event.target.value.toUpperCase())}/></label></section><div className="settings-save"><button className="button primary" disabled={busy}>{busy ? 'Saving…' : 'Save all settings'}</button></div><section id="maintenance-settings" className="card setting-card"><h2><RefreshCw size={20}/>Lifecycle maintenance</h2><p>Preview or process trials, renewals, overdue invoices, retries, and scheduled cancellations using the backend lifecycle engine.</p><div className="button-row"><button type="button" className="button" onClick={() => setMaintenance('preview')}>Preview due work</button><button type="button" className="button danger" onClick={() => setMaintenance('run')}>Process due work</button></div></section></form></div></DataBoundary>{maintenance && <ConfirmDialog title={maintenance === 'preview' ? 'Preview due work' : 'Process due work'} message={maintenance === 'preview' ? 'Run the lifecycle engine in dry-run mode without changing records?' : 'Apply all currently due lifecycle transitions to the local database?'} confirmLabel={maintenance === 'preview' ? 'Run preview' : 'Process now'} danger={maintenance === 'run'} busy={busy} onCancel={() => setMaintenance(null)} onConfirm={() => void processDue()}/>} {toastNode}</Page>
}

function NotFoundPage() {
  return <Page title="Page not found"><div className="state-panel"><h2>404</h2><p>The requested page does not exist.</p><Link className="button primary" to="/dashboard">Return to dashboard</Link></div></Page>
}

function LoginPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (localStorage.getItem(tokenKey) && readUser()) return <Navigate to="/dashboard" replace/>
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    if (mode === 'signup' && password !== confirmPassword) { setError('Passwords do not match.'); setBusy(false); return }
    try {
      const endpoint = mode === 'signup' ? '/auth/signup' : '/auth/login'
      const payload = mode === 'signup' ? { name, email, password } : { email, password }
      const response = await api.post<Envelope<{ access_token: string; user: AuthUser }>>(endpoint, payload)
      saveSession(response.data.data.access_token, response.data.data.user)
      navigate('/dashboard', { replace: true })
      window.location.reload()
    } catch (caught) { setError(apiMessage(caught, mode === 'signup' ? 'Unable to create the account.' : 'Unable to sign in.')) } finally { setBusy(false) }
  }
  return <div className="login"><form onSubmit={submit}><span className="brand-logo"><LayoutDashboard size={25}/></span><h1>{mode === 'signup' ? 'Create your account' : 'Welcome to Argo'}</h1><p>{mode === 'signup' ? 'Create the first live account for this organization.' : 'Sign in to Subscription Management'}</p>{mode === 'signup' && <label>Full name<input value={name} onChange={event => setName(event.target.value)} type="text" required minLength={2} maxLength={160} autoComplete="name"/></label>}<label>Email<input value={email} onChange={event => setEmail(event.target.value)} type="email" required autoComplete="username"/></label><label>Password<input value={password} onChange={event => setPassword(event.target.value)} type="password" required minLength={8} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}/></label>{mode === 'signup' && <label>Confirm password<input value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} type="password" required minLength={8} autoComplete="new-password"/></label>}{error && <p className="error" role="alert">{error}</p>}<button className="button primary" disabled={busy}>{busy ? (mode === 'signup' ? 'Creating account…' : 'Signing in…') : mode === 'signup' ? 'Create account' : 'Sign in'}</button><button type="button" className="button" onClick={() => { setMode(mode === 'signup' ? 'login' : 'signup'); setError(''); setConfirmPassword('') }}>{mode === 'signup' ? 'Back to sign in' : 'Create a live account'}</button></form></div>
}

function ProtectedApp() {
  const user = readUser()
  if (!localStorage.getItem(tokenKey) || !user) return <Navigate to="/login" replace/>
  const has = (scope: string) => user.scopes.includes(scope) || user.scopes.includes('subscription:admin')
  return <AppDataProvider user={user}><Shell><Routes><Route path="/dashboard" element={<DashboardPage/>}/><Route path="/customers" element={<CustomersPage/>}/><Route path="/plans" element={<PlansPage/>}/><Route path="/subscriptions" element={<SubscriptionsPage/>}/><Route path="/payments" element={<PaymentsPage/>}/><Route path="/invoices" element={<InvoicesPage/>}/><Route path="/reports" element={has('subscription:reports') ? <ReportsPage/> : <Navigate to="/dashboard" replace/>}/><Route path="/notifications" element={<NotificationsPage/>}/><Route path="/settings" element={has('subscription:admin') ? <SettingsPage/> : <Navigate to="/dashboard" replace/>}/><Route path="*" element={<NotFoundPage/>}/></Routes></Shell></AppDataProvider>
}

function App() {
  return <Routes><Route path="/login" element={<LoginPage/>}/><Route path="/*" element={<ProtectedApp/>}/></Routes>
}

createRoot(document.getElementById('root')!).render(<BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><App/></BrowserRouter>)
