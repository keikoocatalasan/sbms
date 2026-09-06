import { FormEvent, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Archive, ArrowRight, Bell, Building2, CalendarDays, Check, CheckCircle2, CircleDollarSign, CreditCard, Eye, EyeOff, FileText, LayoutDashboard, LineChart, ListChecks, LoaderCircle, LockKeyhole, LogIn, Menu, Package, Plus, ReceiptText, RefreshCw, Settings, ShieldCheck, Trash2, Users, UserRound, WalletCards } from 'lucide-react'
import './styles.css'
import { api, apiMessage, clearSession, readUser, requestKey, saveSession, tokenKey } from './api'
import { AppDataProvider, useAppData } from './app-data'
import { ConfirmDialog, DataTable, downloadCsv, EmptyState, ErrorState, ExportButton, LoadingState, Metric, Modal, money, shortDate, Status, Toast } from './components'
import { CustomerDialog, CustomerProfileDialog, FeatureCatalogDialog, InvoiceDetailDialog, InvoiceDialog, NotificationDialog, PaymentAllocationDialog, PaymentDialog, PlatformUserDialog, PlanDialog, PlanFeaturesDialog, PlanPriceDialog, SubscriptionCommandDialog, SubscriptionDialog } from './dialogs'
import type { AuthUser, Customer, Envelope, Invoice, Notification, Payment, Plan, PlanPrice, PlatformOrganization, PlatformUser, Subscription, SystemSettings, TeamUser } from './types'

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
  '/': 'Subscription operations for growing organizations',
  '/dashboard': 'Live overview of customers, billing, and subscription health',
  '/customers': 'Manage customer records and their billing relationships',
  '/plans': 'Create and manage the plans available for subscription',
  '/subscriptions': 'Manage trials, renewals, plan changes, and cancellations',
  '/payments': 'Record payments and allocate them to open invoices',
  '/invoices': 'Review, finalize, download, and void invoices',
  '/reports': 'Analyze revenue and recurring subscription performance',
  '/notifications': 'Send and review in-app account notifications',
  '/users': 'Assign organization roles and manage account access',
  '/settings': 'Configure billing rules, numbering, and notifications',
  '/portal/dashboard': 'Your subscription and billing overview',
  '/portal/subscription': 'Review your plan, features, and billing cycle',
  '/portal/invoices': 'View and download your invoices',
  '/portal/notifications': 'Keep up with account updates',
  '/portal/profile': 'Manage your account details',
  '/super-admin/dashboard': 'Platform-wide organization and account health',
  '/super-admin/organizations': 'Review tenant status and account counts',
  '/super-admin/users': 'Create and review platform user access',
  '/super-admin/reports': 'Review platform-level subscription aggregates',
  '/super-admin/notifications': 'Review platform alerts',
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
  const signOut = () => { void api.post('/auth/logout').catch(() => undefined).finally(() => { clearSession(); navigate('/login', { replace: true }) }) }
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
    <main><header><button type="button" className="mobile-menu" aria-label="Open navigation" onClick={() => setCollapsed(true)}><Menu/></button><div className="header-spacer"/><span className="date">{shortDate(new Date().toISOString())}</span><button type="button" className="notification-bell icon-button" aria-label={`${unread} unread notifications`} onClick={() => navigate('/notifications')}><Bell size={21}/>{unread > 0 && <b>{unread}</b>}</button><div className="profile-wrap"><button type="button" className="profile-button" aria-label="Open profile menu" aria-expanded={profileOpen} onClick={() => setProfileOpen(value => !value)}><span className="profile-photo">{user.name[0]}</span><span><b>{user.name}</b><small>{user.role === 'super_admin' ? 'Super Admin' : user.role === 'org_admin' ? 'Organization Administrator' : 'Subscriber User'}</small></span></button>{profileOpen && <div className="profile-menu"><p>{user.email}</p><button type="button" onClick={() => { setProfileOpen(false); signOut() }}>Sign out</button></div>}</div></header>{children}</main>
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
  const currency = payments.find(payment => payment.status === 'completed')?.currency ?? 'PHP'
  const axisLabel = (value: number) => new Intl.NumberFormat('en-PH', { style: 'currency', currency, notation: 'compact', maximumFractionDigits: 1 }).format(value / 100)
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ left: 5, right: 8, top: 5, bottom: 0 }}><defs><linearGradient id="revenueFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#2563eb" stopOpacity=".22"/><stop offset="100%" stopColor="#2563eb" stopOpacity="0"/></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf1f7"/><XAxis dataKey="label" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false} tickFormatter={axisLabel}/><Tooltip formatter={value => money(Number(value ?? 0), currency)}/><Area type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2.5} fill="url(#revenueFill)"/></AreaChart></ResponsiveContainer>
}

function StatusChart({ subscriptions }: { subscriptions: Subscription[] }) {
  const colors: Record<string, string> = { active: '#2563eb', trialing: '#18b979', pending_payment: '#f5a31a', past_due: '#ef4444', cancelled: '#94a3b8', expired: '#64748b' }
  const data = Object.entries(subscriptions.reduce<Record<string, number>>((result, item) => ({ ...result, [item.status]: (result[item.status] ?? 0) + 1 }), {})).map(([name, value]) => ({ name, value, color: colors[name] ?? '#7c3aed' }))
  if (!data.length) return <EmptyState title="No subscriptions yet" copy="Create a subscription to populate this chart."/>
  return <div className="status-body"><div className="donut"><ResponsiveContainer width={205} height={205}><PieChart><Pie data={data} dataKey="value" nameKey="name" innerRadius={59} outerRadius={90} paddingAngle={1}>{data.map(item => <Cell key={item.name} fill={item.color}/>)}</Pie></PieChart></ResponsiveContainer><div className="donut-total"><strong>{subscriptions.length}</strong><span>Total</span></div></div><div className="legend">{data.map(item => <div key={item.name}><span><i style={{ background: item.color }}/>{item.name.replaceAll('_', ' ')}</span><b>{item.value} ({((item.value / subscriptions.length) * 100).toFixed(0)}%)</b></div>)}</div></div>
}

function allocatedPaymentAmount(payment: Payment) {
  return payment.status === 'completed' ? payment.amount_minor - payment.unallocated_minor : 0
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
    <div className="dashboard-tables"><section className="card compact-table"><div className="card-head"><h2>Recent subscriptions</h2><Link to="/subscriptions">View all</Link></div><table><thead><tr><th>Customer</th><th>Plan</th><th>Status</th></tr></thead><tbody>{subscriptions.slice(0, 10).map(item => <tr key={item.id}><td>{customerById[item.customer_id]?.display_name ?? 'Unknown'}</td><td>{planById[item.plan_id]?.name ?? 'Unknown'}</td><td><Status>{item.status}</Status></td></tr>)}{!subscriptions.length && <tr><td colSpan={3}>No subscriptions yet.</td></tr>}</tbody></table></section><section className="card compact-table"><div className="card-head"><h2>Recent payments</h2><Link to="/payments">View all</Link></div><table><thead><tr><th>Customer</th><th>Amount</th><th>Status</th></tr></thead><tbody>{payments.slice(0, 10).map(item => <tr key={item.id}><td>{customerById[item.customer_id]?.display_name ?? 'Unknown'}</td><td>{money(item.amount_minor, item.currency)}</td><td><Status>{item.status}</Status></td></tr>)}{!payments.length && <tr><td colSpan={3}>No payments yet.</td></tr>}</tbody></table></section></div>
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
  return <Page title="Customers" action={can('subscription:billing') && <button className="button primary" onClick={() => setDialog('new')}><Plus size={18}/>Add customer</button>}><DataBoundary><div className="customer-layout"><section className="card table-card"><DataTable rows={customers} rowKey={row => row.id} searchPlaceholder="Search customers" searchText={row => `${row.customer_code} ${row.display_name} ${row.email ?? ''} ${row.phone ?? ''}`} statusOf={row => row.status} statuses={['active', 'archived']} planOf={planName} planOptions={plans.map(plan => plan.name)} onRowClick={setSelectedCustomer} columns={[{ key: 'customer', label: 'Customer', render: row => <span className="person"><i className="avatar-square">{row.display_name.slice(0, 2).toUpperCase()}</i><span>{row.display_name}<small>{row.customer_code}</small></span></span> }, { key: 'email', label: 'Email', render: row => row.email ?? '—' }, { key: 'phone', label: 'Phone', render: row => row.phone ?? '—' }, { key: 'plan', label: 'Plan', render: planName }, { key: 'joined', label: 'Joined', render: row => shortDate(row.created_at) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }]} actions={row => [{ label: 'View profile', onClick: () => setProfile(row) }, ...(can('subscription:billing') ? [{ label: 'Edit customer', onClick: () => setDialog(row) }] : []), ...(can('subscription:admin') && row.status === 'active' ? [{ label: 'Archive customer', danger: true, onClick: () => setArchive(row) }] : [])]}/></section>{selected && <aside className="customer-profile card"><div className="profile-summary"><span className="big-avatar">{selected.display_name.slice(0, 2).toUpperCase()}</span><div><h2>{selected.display_name}</h2><p>{selected.email ?? 'No email'}</p><Status>{selected.status}</Status></div></div><hr/><h3>Subscription summary</h3><div className="summary-box"><div><span>Current plan</span><b>{planName(selected)}</b></div><div><span>Status</span><b>{activeSubscription(selected)?.status.replaceAll('_', ' ') ?? 'None'}</b></div><div><span>Next billing</span><b>{shortDate(activeSubscription(selected)?.next_billing_at)}</b></div><hr/><div><span>Payments</span><b>{payments.filter(item => item.customer_id === selected.id).length}</b></div><div><span>Total paid</span><b>{money(payments.filter(item => item.customer_id === selected.id).reduce((sum, item) => sum + allocatedPaymentAmount(item), 0))}</b></div><div><span>Outstanding</span><b>{money(invoices.filter(item => item.customer_id === selected.id).reduce((sum, item) => sum + item.amounts.balance_minor, 0))}</b></div></div><button className="outline" onClick={() => setProfile(selected)}>View full profile</button></aside>}</div></DataBoundary>
    {dialog && <CustomerDialog customer={dialog === 'new' ? undefined : dialog} onClose={() => setDialog(null)} onDone={done}/>} {profile && <CustomerProfileDialog customer={profile} onClose={() => setProfile(null)}/>} {archive && <ConfirmDialog title="Archive customer" message={`Archive ${archive.display_name}? Existing billing history is preserved, but new subscriptions are blocked.`} confirmLabel="Archive" danger busy={busy} onCancel={() => setArchive(null)} onConfirm={() => void archiveCustomer()}/>} {toastNode}
  </Page>
}

function PlansPage() {
  const { plans, subscriptions, can, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [dialog, setDialog] = useState<'new' | Plan | null>(null)
  const [priceTarget, setPriceTarget] = useState<Plan | null>(null)
  const [priceEditTarget, setPriceEditTarget] = useState<{ plan: Plan; price: PlanPrice } | null>(null)
  const [statusTarget, setStatusTarget] = useState<Plan | null>(null)
  const [removeTarget, setRemoveTarget] = useState<Plan | null>(null)
  const [priceRemoveTarget, setPriceRemoveTarget] = useState<{ plan: Plan; price: PlanPrice } | null>(null)
  const [featurePlanTarget, setFeaturePlanTarget] = useState<Plan | null>(null)
  const [featureCatalogOpen, setFeatureCatalogOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const subscriberCount = (plan: Plan) => subscriptions.filter(item => item.plan_id === plan.id && item.status === 'active').length
  const defaultPrice = (plan: Plan) => plan.prices.find(price => price.is_default && price.status === 'active') ?? plan.prices.find(price => price.status === 'active')
  async function changeStatus() { if (!statusTarget) return; setBusy(true); const next = statusTarget.status === 'active' ? 'archived' : 'active'; try { await api.patch(`/plans/${statusTarget.id}/status`, { status: next }); await refresh(); setStatusTarget(null); done(`Plan ${next}.`) } catch (caught) { fail(caught, 'Unable to change the plan status.') } finally { setBusy(false) } }
  async function removePlan() { if (!removeTarget) return; setBusy(true); try { const response = await api.delete(`/plans/${removeTarget.id}`); const action = response.data.data.action === 'deleted' ? 'deleted' : 'archived'; await refresh(); setRemoveTarget(null); done(`Plan ${action}.`) } catch (caught) { fail(caught, 'Unable to remove the plan.') } finally { setBusy(false) } }
  async function removePrice() { if (!priceRemoveTarget) return; setBusy(true); try { const response = await api.delete(`/plans/${priceRemoveTarget.plan.id}/prices/${priceRemoveTarget.price.id}`); const action = response.data.data.action === 'deleted' ? 'deleted' : 'archived'; await refresh(); setPriceRemoveTarget(null); done(`Plan price ${action}.`) } catch (caught) { fail(caught, 'Unable to remove the plan price.') } finally { setBusy(false) } }
  return <Page title="Subscription Plans" action={can('subscription:admin') && <><button className="button" onClick={() => setFeatureCatalogOpen(true)}><ListChecks size={16}/>Feature catalog</button><button className="button primary" onClick={() => setDialog('new')}><Plus size={18}/>Add plan</button></>}><DataBoundary>
    {plans.length ? <section className="plan-grid">{plans.map((plan, index) => { const price = defaultPrice(plan); const activePrices = plan.prices.filter(item => item.status === 'active').sort((a, b) => a.billing_interval.localeCompare(b.billing_interval)); return <article className={`plan-card tone-${index % 4} ${plan.is_featured ? 'featured' : ''}`} key={plan.id}><div className="plan-card-head"><span className="plan-icon"><Package size={23}/></span>{plan.is_featured && <span className="featured-label">Featured</span>}</div><h2>{plan.name}</h2><p>{plan.description || 'No plan description has been provided.'}</p><div className="prices">{price ? <><b>{money(price.unit_amount_minor, price.currency)}</b><span>/ {price.billing_interval}</span></> : <b>No active price</b>}</div>{activePrices.length > 1 && <div className="plan-price-list">{activePrices.map(item => <div className="plan-price-row" key={item.id}><span>{item.billing_interval === 'year' ? 'Annual' : 'Monthly'} <small>{money(item.unit_amount_minor, item.currency)}</small></span>{can('subscription:admin') && <button type="button" className="icon-button" aria-label={`Edit ${item.billing_interval} price for ${plan.name}`} onClick={() => setPriceEditTarget({ plan, price: item })}><Settings size={14}/></button>}</div>)}</div>}<ul><li>✓ {plan.trial_days ? `${plan.trial_days}-day trial` : 'No trial'}</li><li>✓ {activePrices.length > 1 ? 'Monthly and annual billing' : price?.billing_interval === 'year' ? 'Annual billing' : 'Monthly billing'}</li><li>✓ {subscriberCount(plan)} active subscriber{subscriberCount(plan) === 1 ? '' : 's'}</li></ul>{Boolean(plan.features?.length) && <div className="plan-feature-summary">{plan.features?.slice(0, 3).map(item => <span key={item.id}><Check size={12}/>{item.feature?.name ?? item.feature_id}</span>)}</div>}<div className="plan-footer"><Status>{plan.status}</Status>{can('subscription:admin') && <><button type="button" className="icon-button" aria-label={`Edit ${plan.name}`} onClick={() => setDialog(plan)}><Settings size={17}/></button><button type="button" className="icon-button" aria-label={`Edit features for ${plan.name}`} onClick={() => setFeaturePlanTarget(plan)}><ListChecks size={17}/></button><button type="button" className="icon-button" aria-label={`Add price to ${plan.name}`} onClick={() => setPriceTarget(plan)}><Plus size={17}/></button><button type="button" className="icon-button" aria-label={`${plan.status === 'active' ? 'Archive' : 'Activate'} ${plan.name}`} onClick={() => setStatusTarget(plan)}>{plan.status === 'active' ? <Archive size={17}/> : <CheckCircle2 size={17}/>}</button><button type="button" className="icon-button danger-text" aria-label={`Remove ${plan.name}`} onClick={() => setRemoveTarget(plan)}><Trash2 size={17}/></button></>}</div></article> })}</section> : <EmptyState title="No plans" copy="Create the first plan and price to start subscriptions."/>}
    <section className="card table-card"><DataTable rows={plans} rowKey={row => row.id} searchPlaceholder="Search plans" searchText={row => `${row.plan_code} ${row.name} ${row.description ?? ''}`} statusOf={row => row.status} statuses={['draft', 'active', 'inactive', 'archived']} columns={[{ key: 'name', label: 'Plan', render: row => <><b>{row.name}</b><small className="stacked">{row.plan_code}</small></> }, { key: 'price', label: 'Current price', render: row => { const price = defaultPrice(row); return price ? `${money(price.unit_amount_minor, price.currency)} / ${price.billing_interval}` : 'No active price' } }, { key: 'trial', label: 'Trial', render: row => `${row.trial_days} days` }, { key: 'subscribers', label: 'Active subscribers', render: subscriberCount }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'created', label: 'Created', render: row => shortDate(row.created_at) }]} actions={can('subscription:admin') ? row => [{ label: 'Edit plan', onClick: () => setDialog(row) }, { label: 'Edit features', onClick: () => setFeaturePlanTarget(row) }, { label: 'Add price', onClick: () => setPriceTarget(row) }, ...row.prices.filter(price => price.status !== 'archived').map(price => ({ label: `Edit ${price.billing_interval} price`, onClick: () => setPriceEditTarget({ plan: row, price }) })), ...row.prices.filter(price => price.status !== 'archived').map(price => ({ label: `Remove ${price.billing_interval} price`, danger: true, onClick: () => setPriceRemoveTarget({ plan: row, price }) })), { label: row.status === 'active' ? 'Archive plan' : 'Activate plan', danger: row.status === 'active', onClick: () => setStatusTarget(row) }, { label: 'Remove plan', danger: true, onClick: () => setRemoveTarget(row) }] : undefined}/></section>
  </DataBoundary>{dialog && <PlanDialog plan={dialog === 'new' ? undefined : dialog} onClose={() => setDialog(null)} onDone={done}/>} {priceTarget && <PlanPriceDialog plan={priceTarget} onClose={() => setPriceTarget(null)} onDone={done}/>} {priceEditTarget && <PlanPriceDialog plan={priceEditTarget.plan} price={priceEditTarget.price} used={subscriptions.some(item => item.plan_price_id === priceEditTarget.price.id)} onClose={() => setPriceEditTarget(null)} onDone={done}/>} {featurePlanTarget && <PlanFeaturesDialog plan={featurePlanTarget} onClose={() => setFeaturePlanTarget(null)} onDone={done}/>} {featureCatalogOpen && <FeatureCatalogDialog onClose={() => setFeatureCatalogOpen(false)} onDone={done}/>} {statusTarget && <ConfirmDialog title={statusTarget.status === 'active' ? 'Archive plan' : 'Activate plan'} message={statusTarget.status === 'active' ? `Archive ${statusTarget.name}? Existing subscriptions continue, but the plan cannot be selected for new subscriptions.` : `Make ${statusTarget.name} available for new subscriptions?`} confirmLabel={statusTarget.status === 'active' ? 'Archive' : 'Activate'} danger={statusTarget.status === 'active'} busy={busy} onCancel={() => setStatusTarget(null)} onConfirm={() => void changeStatus()}/>} {removeTarget && <ConfirmDialog title="Remove plan" message={`Remove ${removeTarget.name}? Used plans are archived to preserve billing history. Unused draft and inactive plans are deleted.`} confirmLabel="Remove plan" danger busy={busy} onCancel={() => setRemoveTarget(null)} onConfirm={() => void removePlan()}/>} {priceRemoveTarget && <ConfirmDialog title="Remove plan price" message={`Remove the ${priceRemoveTarget.price.billing_interval} price for ${priceRemoveTarget.plan.name}? Prices used by subscriptions are archived; unused prices are deleted.`} confirmLabel="Remove price" danger busy={busy} onCancel={() => setPriceRemoveTarget(null)} onConfirm={() => void removePrice()}/>} {toastNode}</Page>
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
  const { done, fail, toastNode } = useFeedback()
  const [open, setOpen] = useState(false)
  const [allocationTarget, setAllocationTarget] = useState<Payment | null>(null)
  const [voidTarget, setVoidTarget] = useState<Payment | null>(null)
  const [busy, setBusy] = useState(false)
  const customerName = (item: Payment) => customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Unknown customer'
  const total = payments.filter(item => item.status === 'completed').reduce((sum, item) => sum + item.amount_minor, 0)
  const allocated = payments.reduce((sum, item) => sum + allocatedPaymentAmount(item), 0)
  const unallocated = payments.filter(item => item.status === 'completed').reduce((sum, item) => sum + item.unallocated_minor, 0)
  const exportRows = () => downloadCsv('payments.csv', [['Reference', 'Customer', 'Method', 'Amount', 'Allocated', 'Status', 'Date'], ...payments.map(item => [item.payment_reference, customerName(item), item.payment_method, money(item.amount_minor, item.currency), money(allocatedPaymentAmount(item), item.currency), item.status, shortDate(item.received_at)])])
  async function voidPayment() {
    if (!voidTarget) return
    setBusy(true)
    try {
      await api.post(`/payments/${voidTarget.id}/void`, { reason: 'Voided from payment management' }, { headers: { 'Idempotency-Key': requestKey() } })
      setVoidTarget(null)
      done('Payment voided.')
    } catch (caught) {
      fail(caught, 'Unable to void the payment.')
    } finally {
      setBusy(false)
    }
  }
  return <Page title="Payments" action={<>{can('subscription:billing') && <button className="button primary" onClick={() => setOpen(true)}><Plus size={18}/>Add payment</button>}<ExportButton onClick={exportRows}/></>}><DataBoundary><div className="metric-grid"><Metric icon={<WalletCards/>} label="Recorded payments" value={money(total)} note={`${payments.length} transactions`} tone="green"/><Metric icon={<CircleDollarSign/>} label="Allocated" value={money(allocated)} note="Applied to invoices"/><Metric icon={<CalendarDays/>} label="Unallocated credit" value={money(unallocated)} note="Available on account" tone="orange"/><Metric icon={<CreditCard/>} label="Manual payments" value={String(payments.filter(item => item.status === 'completed' && (item.payment_method === 'manual_bank' || item.payment_method === 'manual_cash')).length)} tone="purple"/></div><div className="dashboard-charts one-chart"><section className="card chart-card"><div className="card-head"><h2>Allocated revenue</h2></div><RevenueChart payments={payments}/></section></div><section className="card table-card"><DataTable rows={payments} rowKey={row => row.id} searchPlaceholder="Search payments" searchText={row => `${row.payment_reference} ${row.external_reference ?? ''} ${customerName(row)} ${row.payment_method}`} statusOf={row => row.status} statuses={['completed', 'void', 'voided']} columns={[{ key: 'reference', label: 'Reference', render: row => <><b>{row.payment_reference}</b><small className="stacked">{row.external_reference ?? 'No external reference'}</small></> }, { key: 'customer', label: 'Customer', render: customerName }, { key: 'method', label: 'Method', render: row => row.payment_method.replaceAll('_', ' ') }, { key: 'amount', label: 'Amount', render: row => money(row.amount_minor, row.currency) }, { key: 'allocated', label: 'Allocated', render: row => money(allocatedPaymentAmount(row), row.currency) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'date', label: 'Received', render: row => shortDate(row.received_at) }]} actions={can('subscription:billing') ? row => [{ label: 'View allocation', disabled: row.status !== 'completed' || row.unallocated_minor <= 0, onClick: () => setAllocationTarget(row) }, ...(can('subscription:admin') && row.status === 'completed' && row.unallocated_minor === row.amount_minor ? [{ label: 'Void payment', danger: true, onClick: () => setVoidTarget(row) }] : [])] : undefined}/></section></DataBoundary>{open && <PaymentDialog onClose={() => setOpen(false)} onDone={done}/>} {allocationTarget && <PaymentAllocationDialog payment={allocationTarget} onClose={() => setAllocationTarget(null)} onDone={done}/>} {voidTarget && <ConfirmDialog title="Void payment" message={`Void ${voidTarget.payment_reference}? Only fully unallocated payments can be voided.`} confirmLabel="Void payment" danger busy={busy} onCancel={() => setVoidTarget(null)} onConfirm={() => void voidPayment()}/>} {toastNode}</Page>
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
  const allocated = payments.reduce((sum, item) => sum + allocatedPaymentAmount(item), 0)
  const priceById = Object.fromEntries(plans.flatMap(plan => plan.prices.map(price => [price.id, price])))
  const planRevenue = plans.map(plan => ({ name: plan.name, amount: subscriptions.filter(item => item.plan_id === plan.id && ['active', 'trialing', 'past_due'].includes(item.status)).reduce((sum, item) => { const price = priceById[item.plan_price_id]; return sum + (price?.billing_interval === 'year' ? Math.round(price.unit_amount_minor / 12) : price?.unit_amount_minor ?? 0) }, 0) })).sort((a, b) => b.amount - a.amount)
  const customerRevenue = customers.map(customer => ({ name: customer.display_name, amount: payments.filter(item => item.customer_id === customer.id).reduce((sum, item) => sum + allocatedPaymentAmount(item), 0) })).filter(item => item.amount > 0).sort((a, b) => b.amount - a.amount)
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

type SettingsCategory = { key: string; label: string; icon: IconType; copy: string }
const settingsCategories: SettingsCategory[] = [
  { key: 'general', label: 'General', icon: Settings, copy: 'Currency and time zone used across the organization' },
  { key: 'billing', label: 'Billing', icon: ReceiptText, copy: 'Invoice timing, renewals, and payment retry behavior' },
  { key: 'numbering', label: 'Numbering', icon: FileText, copy: 'Prefixes applied to generated invoices, payments, and records' },
  { key: 'notifications', label: 'Notifications', icon: Bell, copy: 'In-app notices and customer reminder scheduling' },
  { key: 'maintenance', label: 'Maintenance', icon: RefreshCw, copy: 'Run background billing and subscription lifecycle jobs' },
]

function SettingsNav({ active }: { active: string }) {
  return <aside className="settings-nav card" aria-label="Settings categories">{settingsCategories.map(({ key, label, icon: Icon }) => <Link key={key} to={`/settings/${key}`} className={active === key ? 'selected' : ''}><Icon size={17}/>{label}</Link>)}</aside>
}

function SettingsApp() {
  const { settings, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [form, setForm] = useState<SystemSettings | null>(settings)
  const [busy, setBusy] = useState(false)
  const [maintenance, setMaintenance] = useState<'preview' | 'run' | null>(null)
  useEffect(() => setForm(settings), [settings])
  const update = <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => setForm(current => current ? { ...current, [key]: value } : current)
  async function save(event: FormEvent) { event.preventDefault(); if (!form) return; setBusy(true); try { const { default_currency, timezone, invoice_due_days, grace_period_days, max_payment_retries, retry_interval_days, trial_reminder_days, invoice_due_reminder_days, allow_partial_payments, auto_renew_default, auto_generate_invoices, enable_in_app_notifications, invoice_prefix, payment_prefix, subscription_prefix, customer_prefix } = form; await api.patch('/settings', { default_currency, timezone, invoice_due_days, grace_period_days, max_payment_retries, retry_interval_days, trial_reminder_days, invoice_due_reminder_days, allow_partial_payments, auto_renew_default, auto_generate_invoices, enable_in_app_notifications, invoice_prefix, payment_prefix, subscription_prefix, customer_prefix }); await refresh(); done('Settings saved.') } catch (caught) { fail(caught, 'Unable to save settings.') } finally { setBusy(false) } }
  async function processDue() { if (!maintenance) return; setBusy(true); try { const response = await api.post('/maintenance/process-due', { dry_run: maintenance === 'preview', batch_size: 100 }, { headers: { 'Idempotency-Key': requestKey() } }); await refresh(); done(`${maintenance === 'preview' ? 'Preview complete' : 'Due processing complete'}: ${JSON.stringify(response.data.data)}`); setMaintenance(null) } catch (caught) { fail(caught, 'Unable to process due subscriptions.') } finally { setBusy(false) } }
  if (!form) return <Page title="Settings"><DataBoundary><EmptyState title="Settings unavailable" copy="No organization settings record was returned."/></DataBoundary></Page>
  return <Page title="Settings"><DataBoundary><div className="settings-layout"><SettingsNav active={window.location.pathname.replace('/settings/', '') || 'general'}/><Routes><Route index element={<Navigate to="/settings/general" replace/>}/><Route path="general" element={<SettingsGeneralPage form={form} update={update} save={save} toastNode={toastNode}/>}/><Route path="billing" element={<SettingsBillingPage form={form} update={update} save={save} toastNode={toastNode}/>}/><Route path="numbering" element={<SettingsNumberingPage form={form} update={update} save={save} toastNode={toastNode}/>}/><Route path="notifications" element={<SettingsNotificationsPage form={form} update={update} save={save} toastNode={toastNode}/>}/><Route path="maintenance" element={<SettingsMaintenancePage maintenance={maintenance} setMaintenance={setMaintenance} busy={busy} processDue={processDue} toastNode={toastNode}/>}/><Route path="*" element={<Navigate to="/settings/general" replace/>}/></Routes></div></DataBoundary></Page>
}

function SettingsCategoryPage({ category, children, action }: { category: string; children: React.ReactNode; action?: React.ReactNode }) {
  const meta = settingsCategories.find(item => item.key === category) ?? settingsCategories[0]
  const Icon = meta.icon
  return <section className="settings-category"><header className="settings-category-head"><span className="settings-category-icon"><Icon size={20}/></span><div><h2>{meta.label}</h2><p>{meta.copy}</p></div>{action}</header><div className="settings-category-body">{children}</div></section>
}

function SettingsGeneralPage({ form, update, save, toastNode }: { form: SystemSettings; update: <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => void; save: (event: FormEvent) => void; toastNode: React.ReactNode }) {
  return <form onSubmit={save}><SettingsCategoryPage category="general"><div className="card setting-card"><div className="form-grid"><label>Default currency<select value={form.default_currency} onChange={event => update('default_currency', event.target.value)}><option value="PHP">PHP - Philippine Peso</option><option value="USD">USD - US Dollar</option></select></label><label>Time zone<select value={form.timezone} onChange={event => update('timezone', event.target.value)}><option value="Asia/Manila">Asia/Manila</option><option value="UTC">UTC</option></select></label></div></div></SettingsCategoryPage>{toastNode}</form>
}

function SettingsBillingPage({ form, update, save, toastNode }: { form: SystemSettings; update: <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => void; save: (event: FormEvent) => void; toastNode: React.ReactNode }) {
  return <form onSubmit={save}><SettingsCategoryPage category="billing"><div className="card setting-card"><div className="form-grid"><label>Invoice due days<input type="number" min="0" max="365" value={form.invoice_due_days} onChange={event => update('invoice_due_days', Number(event.target.value))}/></label><label>Grace period days<input type="number" min="0" max="365" value={form.grace_period_days} onChange={event => update('grace_period_days', Number(event.target.value))}/></label><label>Max payment retries<input type="number" min="0" max="20" value={form.max_payment_retries} onChange={event => update('max_payment_retries', Number(event.target.value))}/></label><label>Retry interval days<input type="number" min="0" max="60" value={form.retry_interval_days} onChange={event => update('retry_interval_days', Number(event.target.value))}/></label></div><div className="setting-toggles"><label className="toggle-row"><span>Auto renewal by default<span className="setting-note">New subscriptions renew automatically unless turned off.</span></span><input type="checkbox" checked={form.auto_renew_default} onChange={event => update('auto_renew_default', event.target.checked)}/></label><label className="toggle-row"><span>Allow partial payments<span className="setting-note">Let customers pay part of an invoice balance.</span></span><input type="checkbox" checked={form.allow_partial_payments} onChange={event => update('allow_partial_payments', event.target.checked)}/></label><label className="toggle-row"><span>Auto generate invoices<span className="setting-note">Create renewal invoices when a subscription period ends.</span></span><input type="checkbox" checked={form.auto_generate_invoices} onChange={event => update('auto_generate_invoices', event.target.checked)}/></label></div></div></SettingsCategoryPage>{toastNode}</form>
}

function SettingsNumberingPage({ form, update, save, toastNode }: { form: SystemSettings; update: <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => void; save: (event: FormEvent) => void; toastNode: React.ReactNode }) {
  return <form onSubmit={save}><SettingsCategoryPage category="numbering"><div className="card setting-card"><p className="setting-note">Prefixes are added to reference numbers on generated documents. Use 2 to 8 uppercase letters.</p><div className="form-grid"><label>Invoice prefix<input value={form.invoice_prefix} maxLength={8} pattern="[A-Z]{2,8}" onChange={event => update('invoice_prefix', event.target.value.toUpperCase())}/></label><label>Payment prefix<input value={form.payment_prefix} maxLength={8} pattern="[A-Z]{2,8}" onChange={event => update('payment_prefix', event.target.value.toUpperCase())}/></label><label>Subscription prefix<input value={form.subscription_prefix} maxLength={8} pattern="[A-Z]{2,8}" onChange={event => update('subscription_prefix', event.target.value.toUpperCase())}/></label><label>Customer prefix<input value={form.customer_prefix} maxLength={8} pattern="[A-Z]{2,8}" onChange={event => update('customer_prefix', event.target.value.toUpperCase())}/></label></div></div></SettingsCategoryPage>{toastNode}</form>
}

function SettingsNotificationsPage({ form, update, save, toastNode }: { form: SystemSettings; update: <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => void; save: (event: FormEvent) => void; toastNode: React.ReactNode }) {
  return <form onSubmit={save}><SettingsCategoryPage category="notifications"><div className="card setting-card"><label className="toggle-row"><span>In-app notifications<span className="setting-note">Show notices in the account notification center.</span></span><input type="checkbox" checked={form.enable_in_app_notifications} onChange={event => update('enable_in_app_notifications', event.target.checked)}/></label><div className="form-grid"><label>Trial reminder days<input type="number" min="0" max="30" value={form.trial_reminder_days} onChange={event => update('trial_reminder_days', Number(event.target.value))}/></label><label>Invoice due reminder days<input type="number" min="0" max="30" value={form.invoice_due_reminder_days} onChange={event => update('invoice_due_reminder_days', Number(event.target.value))}/></label></div><p className="setting-note">Reminders are sent the given number of days before a trial ends or an invoice is due.</p></div></SettingsCategoryPage>{toastNode}</form>
}

function SettingsMaintenancePage({ maintenance, setMaintenance, busy, processDue, toastNode }: { maintenance: 'preview' | 'run' | null; setMaintenance: (value: 'preview' | 'run' | null) => void; busy: boolean; processDue: () => void; toastNode: React.ReactNode }) {
  const options: Array<{ key: 'preview' | 'run'; title: string; copy: string }> = [
    { key: 'preview', title: 'Preview due processing', copy: 'Simulate renewals, overdue marking, and activations without writing changes.' },
    { key: 'run', title: 'Run due processing', copy: 'Apply lifecycle changes for subscriptions reaching their period end or due date.' },
  ]
  return <><SettingsCategoryPage category="maintenance" action={maintenance ? <button type="button" className="button" onClick={() => setMaintenance(null)} disabled={busy}>Cancel</button> : undefined}><div className="card setting-card"><div className="maintenance-options">{options.map(option => <label key={option.key} className={`maintenance-option ${maintenance === option.key ? 'selected' : ''}`}><input type="radio" name="maintenance-mode" checked={maintenance === option.key} onChange={() => setMaintenance(option.key)}/><span><b>{option.title}</b><small>{option.copy}</small></span></label>)}</div>{maintenance && <div className="save-bar"><span className="page-note">{maintenance === 'preview' ? 'No records will be changed.' : 'This writes billing and lifecycle changes.'}</span><div className="save-bar-actions"><button type="button" className={`button ${maintenance === 'run' ? 'danger' : 'primary'}`} onClick={processDue} disabled={busy}>{busy ? <><LoaderCircle className="spin" size={16}/> Working</> : maintenance === 'preview' ? 'Run preview' : 'Run now'}</button></div></div>}</div></SettingsCategoryPage>{toastNode}</>
}

function UsersPage() {
  const { user: currentUser } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [users, setUsers] = useState<TeamUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [command, setCommand] = useState<{ user: TeamUser; action: 'role' | 'status' } | null>(null)
  const [busy, setBusy] = useState(false)
  async function load() { setLoading(true); setError(''); try { const response = await api.get<Envelope<TeamUser[]>>('/users?page_size=100'); setUsers(response.data.data) } catch (caught) { setError(apiMessage(caught, 'Unable to load organization users.')) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  async function runCommand() {
    if (!command) return
    setBusy(true)
    try {
      if (command.action === 'role') await api.patch(`/users/${command.user.id}/role`, { role: command.user.role === 'org_admin' ? 'user' : 'org_admin' })
      else await api.patch(`/users/${command.user.id}/status`, { status: command.user.status === 'active' ? 'suspended' : 'active' })
      await load(); setCommand(null); await done('User access updated.')
    } catch (caught) { fail(caught, 'Unable to update user access.') } finally { setBusy(false) }
  }
  return <Page title="Users and Roles" action={<span className="page-note">Invite workflow will be connected after email delivery is configured.</span>}>{loading ? <LoadingState label="Loading users"/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : <section className="card table-card"><DataTable rows={users} rowKey={row => row.id} searchPlaceholder="Search users" searchText={row => `${row.name} ${row.email} ${row.role}`} statusOf={row => row.status} statuses={['active', 'suspended', 'inactive']} columns={[{ key: 'name', label: 'User', render: row => <span className="person"><i className="avatar-square">{row.name.slice(0, 2).toUpperCase()}</i><span>{row.name}<small>{row.email}</small></span></span> }, { key: 'role', label: 'Role', render: row => row.role === 'org_admin' ? 'Organization admin' : 'Subscriber user' }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'created', label: 'Joined', render: row => shortDate(row.created_at) }]} actions={row => row.id === currentUser.id ? [{ label: 'Your account', disabled: true, onClick: () => undefined }] : [{ label: row.role === 'org_admin' ? 'Make subscriber user' : 'Make organization admin', onClick: () => setCommand({ user: row, action: 'role' }) }, { label: row.status === 'active' ? 'Suspend access' : 'Activate access', danger: row.status === 'active', onClick: () => setCommand({ user: row, action: 'status' }) }]}/></section>}{command && <ConfirmDialog title={command.action === 'role' ? 'Change user role' : command.user.status === 'active' ? 'Suspend user' : 'Activate user'} message={command.action === 'role' ? `Change ${command.user.name} to ${command.user.role === 'org_admin' ? 'a subscriber user' : 'an organization administrator'}?` : `${command.user.status === 'active' ? 'Suspend' : 'Activate'} ${command.user.name}'s organization access?`} confirmLabel={command.action === 'role' ? 'Change role' : command.user.status === 'active' ? 'Suspend' : 'Activate'} danger={command.action === 'status' && command.user.status === 'active'} busy={busy} onCancel={() => setCommand(null)} onConfirm={() => void runCommand()}/>} {toastNode}</Page>
}

function LandingPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    let mounted = true
    api.get<Envelope<Plan[]>>('/public/plans').then(response => { if (mounted) setPlans(response.data.data) }).catch(caught => { if (mounted) setError(apiMessage(caught, 'Plans are temporarily unavailable.')) }).finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])
  return <main className="landing-page"><nav className="landing-nav"><Link className="landing-brand" to="/"><span className="brand-logo"><LayoutDashboard size={22}/></span><span><b>Subscription</b><small>Management System</small></span></Link><Link className="button primary" to="/login"><LogIn size={16}/>Sign in</Link></nav><section className="landing-hero"><div><p className="landing-kicker">Subscription operations for growing organizations</p><h1>Run billing with a clear view of every customer.</h1><p className="landing-lede">Manage plans, recurring subscriptions, invoices, payments, and customer access from one trusted workspace.</p><div className="landing-actions"><Link className="button primary" to="/login">Open your workspace <ArrowRight size={16}/></Link><a className="landing-secondary" href="#plans">View plans <ArrowRight size={16}/></a></div></div><div className="landing-hero-card"><div className="landing-hero-card-top"><span className="status-pulse"/>Live billing overview</div><div className="landing-hero-metric"><span>Collected revenue</span><strong>Clear from invoice to payment</strong></div><div className="landing-hero-lines"><i/><i/><i/></div></div></section><section className="landing-trust"><span><LockKeyhole size={16}/>Tenant-aware access</span><span><Building2 size={16}/>Built for organizations</span><span><CheckCircle2 size={16}/>Auditable billing</span></section><section className="landing-section" id="plans"><div className="landing-section-head"><div><p className="landing-kicker">Flexible billing</p><h2>Plans that make the choice clear.</h2><p>Compare the live catalog, then choose a monthly or annual billing cycle.</p></div><div className="billing-toggle" role="group" aria-label="Billing interval"><button type="button" className={billingInterval === 'month' ? 'selected' : ''} onClick={() => setBillingInterval('month')}>Monthly</button><button type="button" className={billingInterval === 'year' ? 'selected' : ''} onClick={() => setBillingInterval('year')}>Annual</button></div></div>{loading ? <div className="landing-state">Loading published plans...</div> : error ? <div className="landing-state error-state">{error}</div> : <div className="landing-plan-grid">{plans.map(plan => { const price = plan.prices.find(item => item.billing_interval === billingInterval && item.is_default) ?? plan.prices.find(item => item.billing_interval === billingInterval); const monthly = plan.prices.find(item => item.billing_interval === 'month' && item.is_default) ?? plan.prices.find(item => item.billing_interval === 'month'); const annual = plan.prices.find(item => item.billing_interval === 'year' && item.is_default) ?? plan.prices.find(item => item.billing_interval === 'year'); const savings = monthly && annual ? Math.max(0, Math.round((1 - annual.unit_amount_minor / (monthly.unit_amount_minor * 12)) * 100)) : 0; const featureRows = price?.features ?? plan.features ?? []; return <article className={`landing-plan ${plan.is_featured ? 'featured' : ''}`} key={plan.plan_code}><div className="landing-plan-top"><h3>{plan.name}</h3>{plan.is_featured && <span>Popular</span>}</div><p>{plan.description || 'A focused workspace for subscription operations.'}</p><strong>{price ? money(price.unit_amount_minor, price.currency) : 'Contact us'}</strong><small>{price ? `per ${billingInterval === 'year' ? 'year' : 'month'}` : 'for pricing'}</small>{billingInterval === 'year' && savings > 0 && <b className="landing-savings">Save {savings}% vs monthly</b>}{featureRows.length > 0 && <ul className="landing-plan-features">{featureRows.slice(0, 4).map(item => <li key={`${item.feature?.feature_code ?? item.feature_id}-${item.billing_interval ?? 'all'}`}><Check size={13}/>{item.feature?.name ?? item.feature_id}</li>)}</ul>}<Link to="/login" className="landing-plan-link">Sign in to choose <ArrowRight size={15}/></Link></article> })}</div>}</section><section className="landing-section landing-feature-section"><div><p className="landing-kicker">One source of truth</p><h2>Every billing decision stays connected.</h2></div><div className="landing-feature-grid"><article><span><Building2 size={18}/></span><h3>Organization control</h3><p>Keep each company's plans, customers, and billing records isolated and manageable.</p></article><article><span><ReceiptText size={18}/></span><h3>Subscription lifecycle</h3><p>Handle trials, renewals, plan changes, cancellations, invoices, and payment allocation in one flow.</p></article><article><span><UserRound size={18}/></span><h3>Self-service access</h3><p>Give subscribers a focused view of their own plan, invoices, notifications, and account details.</p></article></div></section><footer className="landing-footer"><span>Subscription Management System</span><span>Secure access for every organization.</span><Link to="/login">Sign in <ArrowRight size={15}/></Link></footer></main>
}

function PortalShell({ children }: { children: React.ReactNode }) {
  const { user, notifications } = useAppData()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const unread = notifications.filter(item => !item.read_at).length
  const signOut = () => { void api.post('/auth/logout').catch(() => undefined).finally(() => { clearSession(); navigate('/login', { replace: true }) }) }
  const links = [{ path: '/portal/dashboard', label: 'Dashboard', icon: LayoutDashboard }, { path: '/portal/subscription', label: 'My Subscription', icon: Package }, { path: '/portal/invoices', label: 'Invoices', icon: FileText }, { path: '/portal/notifications', label: 'Notifications', icon: Bell }, { path: '/portal/profile', label: 'Profile', icon: UserRound }]
  return <div className={`portal-shell ${collapsed ? 'collapsed' : ''}`}><aside><Link className="brand" to="/portal/dashboard" aria-label="User dashboard"><span className="brand-logo"><LayoutDashboard size={22}/></span><b>Subscription<br/>Management System</b></Link><button type="button" className="hamburger" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed} onClick={() => setCollapsed(value => !value)}><Menu/></button><nav>{links.map(({ path, label, icon: Icon }) => <Link key={path} to={path} className={location.pathname === path ? 'selected' : ''}><Icon size={20}/><span>{label}</span></Link>)}</nav><div className="side-footer">Need help? Contact your organization administrator.</div><button type="button" className="logout" onClick={signOut}>Sign out</button></aside>{collapsed && <button type="button" className="mobile-overlay" aria-label="Close navigation" onClick={() => setCollapsed(false)}/>}<main><header><button type="button" className="mobile-menu" aria-label="Open navigation" onClick={() => setCollapsed(true)}><Menu/></button><div className="header-spacer"/><span className="date">{shortDate(new Date().toISOString())}</span><button type="button" className="notification-bell icon-button" aria-label={`${unread} unread notifications`} onClick={() => navigate('/portal/notifications')}><Bell size={21}/>{unread > 0 && <b>{unread}</b>}</button><div className="portal-user"><span className="profile-photo">{user.name[0]}</span><span><b>{user.name}</b><small>Subscriber User</small></span></div></header>{children}</main></div>
}

function PortalPage({ title, children }: { title: string; children: React.ReactNode }) {
  const location = useLocation()
  return <section className="content portal-content"><div className="page-head"><div><h1>{title}</h1><p>{pageCopy[location.pathname]}</p></div></div>{children}</section>
}

function PortalDashboardExtras({ plan, price }: { plan?: Plan; price?: PlanPrice }) {
  const featureRows = (price?.features ?? plan?.features ?? []).filter(item => ['users', 'storage', 'api_calls'].includes(item.feature?.feature_code ?? item.feature_id)).slice(0, 3)
  return <div className="portal-bottom-grid"><section className="card portal-extra-card"><div className="card-head"><h2>Usage Overview</h2><span className="portal-muted">Included plan limits</span></div>{featureRows.length ? <div className="portal-usage-list">{featureRows.map(item => { const unit = item.feature?.unit_label ? ` ${item.feature.unit_label}` : ''; const limit = item.value_number !== null && item.value_number !== undefined ? `${item.value_number}${unit}` : item.value_text ?? 'Included'; return <div className="portal-usage-row" key={item.feature?.feature_code ?? item.feature_id}><span className="portal-list-icon"><Package size={16}/></span><div><b>{item.feature?.name ?? item.feature_id}</b><small>{limit} included in your plan</small></div><strong>Included</strong></div> })}</div> : <EmptyState title="No usage limits" copy="Your organization has not configured usage limits for this plan."/>}<p className="portal-extra-note">Live consumption tracking is not connected yet.</p></section><section className="card portal-extra-card"><div className="card-head"><h2>Quick Actions</h2><span className="portal-muted">Manage your account</span></div><div className="portal-quick-actions"><Link className="portal-quick-action" to="/portal/invoices"><FileText size={17}/><span>View invoices</span><ArrowRight size={15}/></Link><Link className="portal-quick-action" to="/portal/subscription"><Package size={17}/><span>Manage subscription</span><ArrowRight size={15}/></Link><Link className="portal-quick-action" to="/portal/notifications"><Bell size={17}/><span>Review notifications</span><ArrowRight size={15}/></Link><Link className="portal-quick-action" to="/portal/profile"><UserRound size={17}/><span>Open profile</span><ArrowRight size={15}/></Link></div></section></div>
}

function PortalDashboardPage() {
  const { subscriptions, invoices, notifications, plans } = useAppData()
  const subscription = subscriptions[0]
  const plan = subscription ? plans.find(item => item.id === subscription.plan_id) : undefined
  const price = subscription ? plan?.prices.find(item => item.id === subscription.plan_price_id) : undefined
  return <PortalPage title="Dashboard"><DataBoundary>{subscription ? <><div className="portal-metrics"><Metric icon={<Package/>} label="Current plan" value={plan?.name ?? 'Subscription'}/><Metric icon={<CalendarDays/>} label="Next billing date" value={shortDate(subscription.next_billing_at)} note={subscription.auto_renew ? 'Auto renewal on' : 'Auto renewal off'} tone="green"/><Metric icon={<WalletCards/>} label="Amount" value={money(price?.unit_amount_minor ?? 0, price?.currency)} note={price?.billing_interval === 'year' ? 'Annual billing' : 'Monthly billing'} tone="orange"/><Metric icon={<FileText/>} label="Payment status" value={invoices[0]?.status === 'paid' ? 'Paid' : invoices[0] ? 'Pending' : 'No invoice'} tone="red"/></div><div className="portal-grid"><section className="card portal-subscription-card"><div className="portal-card-head"><div><p className="landing-kicker">My subscription</p><h2>{plan?.name ?? 'Subscription'}</h2></div><Status>{subscription.status}</Status></div><p>{plan?.description ?? 'Your organization subscription is managed in this workspace.'}</p><div className="portal-detail-row"><span>Billing cycle</span><b>{price?.billing_interval === 'year' ? 'Annual' : 'Monthly'}</b></div><div className="portal-detail-row"><span>Next billing</span><b>{shortDate(subscription.next_billing_at)}</b></div><Link className="button primary" to="/portal/subscription">Manage subscription <ArrowRight size={15}/></Link></section><section className="card portal-list-card"><div className="card-head"><h2>Notifications</h2><Link to="/portal/notifications">View all</Link></div>{notifications.slice(0, 3).map(item => <div className="portal-list-row" key={item.id}><span className="portal-list-icon"><Bell size={16}/></span><div><b>{item.title}</b><small>{item.body}</small></div><Status>{item.read_at ? 'read' : 'unread'}</Status></div>)}{!notifications.length && <EmptyState title="No notifications" copy="You are up to date."/>}</section><section className="card portal-list-card"><div className="card-head"><h2>Recent invoices</h2><Link to="/portal/invoices">View all</Link></div>{invoices.slice(0, 3).map(item => <div className="portal-list-row" key={item.id}><span className="portal-list-icon"><FileText size={16}/></span><div><b>{item.invoice_number}</b><small>{shortDate(item.issue_date)}</small></div><strong>{money(item.amounts.total_minor, item.currency)}</strong><Status>{item.status}</Status></div>)}{!invoices.length && <EmptyState title="No invoices" copy="Your invoices will appear here."/>}</section></div><PortalDashboardExtras plan={plan} price={price}/></> : <EmptyState title="No subscription is linked to this account" copy="Ask your organization administrator to assign your subscriber profile."/>}</DataBoundary></PortalPage>
}

function PortalSubscriptionPage() {
  const { subscriptions, plans, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const subscription = subscriptions[0]
  const plan = subscription ? plans.find(item => item.id === subscription.plan_id) : undefined
  const [command, setCommand] = useState<'change-plan' | 'schedule-cancel' | null>(null)
  async function toggleRenewal() { if (!subscription) return; try { await api.patch(`/me/subscriptions/${subscription.id}/auto-renew`, { expected_version: subscription.version, auto_renew: !subscription.auto_renew }); await refresh(); await done(`Auto renewal ${subscription.auto_renew ? 'disabled' : 'enabled'}.`) } catch (caught) { fail(caught, 'Unable to change auto renewal.') } }
  async function revokeCancellation() { if (!subscription) return; try { await api.post(`/me/subscriptions/${subscription.id}/revoke-cancellation`, { expected_version: subscription.version, reason: 'Cancellation revoked by subscriber' }); await refresh(); await done('Scheduled cancellation revoked.') } catch (caught) { fail(caught, 'Unable to revoke cancellation.') } }
  return <PortalPage title="My Subscription"><DataBoundary>{subscription && plan ? <div className="portal-single-grid"><section className="card portal-subscription-card"><div className="portal-card-head"><div><p className="landing-kicker">Current plan</p><h2>{plan.name}</h2></div><Status>{subscription.status}</Status></div><p>{plan.description || 'Your current organization plan.'}</p><div className="portal-detail-row"><span>Subscription</span><b>{subscription.subscription_number}</b></div><div className="portal-detail-row"><span>Next billing</span><b>{shortDate(subscription.next_billing_at)}</b></div><div className="portal-detail-row"><span>Auto renewal</span><b>{subscription.auto_renew ? 'On' : 'Off'}</b></div><div className="portal-action-row"><button type="button" className="button primary" onClick={() => setCommand('change-plan')}>Change plan</button><button type="button" className="button" onClick={() => void toggleRenewal()}>{subscription.auto_renew ? 'Disable auto renewal' : 'Enable auto renewal'}</button>{subscription.cancel_at_period_end ? <button type="button" className="button" onClick={() => void revokeCancellation()}>Revoke cancellation</button> : <button type="button" className="button danger" onClick={() => setCommand('schedule-cancel')}>Cancel at period end</button>}</div></section><section className="card portal-catalog-card"><div className="card-head"><h2>Available billing options</h2><span className="portal-muted">Managed by your organization</span></div>{plans.filter(item => item.status === 'active').map(item => <div className="portal-plan-option" key={item.id}><div><b>{item.name}</b><small>{item.description || 'Subscription plan'}</small></div><div>{item.prices.filter(price => price.status === 'active').map(price => <span key={price.id}>{money(price.unit_amount_minor, price.currency)} / {price.billing_interval}</span>)}</div></div>)}</section></div> : <EmptyState title="No subscription linked" copy="Ask your organization administrator to assign your subscriber profile."/>}</DataBoundary>{command && subscription && <SubscriptionCommandDialog subscription={subscription} mode={command} selfService onClose={() => setCommand(null)} onDone={done}/>} {toastNode}</PortalPage>
}

function PortalInvoicesPage() {
  const { invoices, customers } = useAppData()
  const [detail, setDetail] = useState<Invoice | null>(null)
  const customerName = (item: Invoice) => customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Your account'
  return <PortalPage title="Invoices"><DataBoundary><section className="card table-card"><DataTable rows={invoices} rowKey={row => row.id} searchPlaceholder="Search invoices" searchText={row => `${row.invoice_number} ${row.notes ?? ''}`} statusOf={row => row.status} statuses={['draft', 'open', 'paid', 'overdue', 'void']} columns={[{ key: 'number', label: 'Invoice', render: row => row.invoice_number }, { key: 'customer', label: 'Account', render: customerName }, { key: 'total', label: 'Total', render: row => money(row.amounts.total_minor, row.currency) }, { key: 'balance', label: 'Balance', render: row => money(row.amounts.balance_minor, row.currency) }, { key: 'due', label: 'Due', render: row => shortDate(row.due_date) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }]} actions={row => [{ label: 'View and download', onClick: () => setDetail(row) }]}/></section></DataBoundary>{detail && <InvoiceDetailDialog invoice={detail} onClose={() => setDetail(null)}/>}</PortalPage>
}

function PortalNotificationsPage() {
  const { notifications, customers, refresh } = useAppData()
  const { done, fail, toastNode } = useFeedback()
  const [selected, setSelected] = useState<Notification | null>(null)
  const recipient = (item: Notification) => item.customer_id ? customers.find(customer => customer.id === item.customer_id)?.display_name ?? 'Your account' : 'Your account'
  async function markRead(item: Notification) { try { await api.post(`/notifications/${item.id}/mark-read`); await refresh(); setSelected(current => current?.id === item.id ? { ...item, read_at: new Date().toISOString() } : current); await done('Notification marked as read.') } catch (caught) { fail(caught, 'Unable to mark the notification as read.') } }
  return <PortalPage title="Notifications"><DataBoundary><div className="notification-layout"><section className="card table-card"><DataTable rows={notifications} rowKey={row => row.id} searchPlaceholder="Search notifications" searchText={row => `${row.title} ${row.body}`} statusOf={row => row.read_at ? 'read' : 'unread'} statuses={['unread', 'read']} onRowClick={setSelected} columns={[{ key: 'message', label: 'Notification', render: row => <><b>{row.title}</b><small className="stacked truncate">{row.body}</small></> }, { key: 'recipient', label: 'Recipient', render: recipient }, { key: 'date', label: 'Sent', render: row => shortDate(row.sent_at) }, { key: 'status', label: 'Status', render: row => <Status>{row.read_at ? 'read' : 'unread'}</Status> }]} actions={row => [{ label: 'View notification', onClick: () => setSelected(row) }, ...(!row.read_at ? [{ label: 'Mark as read', onClick: () => void markRead(row) }] : [])]}/></section><aside className="notification-preview card">{selected ? <><div className="preview-icon"><Bell size={44}/></div><Status>{selected.read_at ? 'read' : 'unread'}</Status><h2>{selected.title}</h2><p>{selected.body}</p><dl><dt>Recipient</dt><dd>{recipient(selected)}</dd><dt>Sent</dt><dd>{shortDate(selected.sent_at)}</dd></dl>{!selected.read_at && <button className="button primary" onClick={() => void markRead(selected)}>Mark as read</button>}</> : <><Bell size={70}/><h2>Notification preview</h2><p>Select a notification to read the full message.</p></>}</aside></div></DataBoundary>{toastNode}</PortalPage>
}

function PortalProfilePage() {
  const { user } = useAppData()
  return <PortalPage title="Profile"><DataBoundary><section className="card portal-profile-card"><span className="big-avatar">{user.name.slice(0, 2).toUpperCase()}</span><div><p className="landing-kicker">Account</p><h2>{user.name}</h2><p>{user.email}</p><Status>active</Status></div><div className="portal-profile-details"><div><span>Role</span><b>Subscriber User</b></div><div><span>Access</span><b>Own subscription and billing records</b></div></div></section></DataBoundary></PortalPage>
}

function PortalApp({ user }: { user: AuthUser }) {
  return <AppDataProvider user={user}><PortalShell><Routes><Route path="/portal/dashboard" element={<PortalDashboardPage/>}/><Route path="/portal/subscription" element={<PortalSubscriptionPage/>}/><Route path="/portal/invoices" element={<PortalInvoicesPage/>}/><Route path="/portal/notifications" element={<PortalNotificationsPage/>}/><Route path="/portal/profile" element={<PortalProfilePage/>}/><Route path="*" element={<Navigate to="/portal/dashboard" replace/>}/></Routes></PortalShell></AppDataProvider>
}

function PlatformShell({ user, children }: { user: AuthUser; children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const signOut = () => { void api.post('/auth/logout').catch(() => undefined).finally(() => { clearSession(); navigate('/login', { replace: true }) }) }
  const links = [{ path: '/super-admin/dashboard', label: 'Dashboard', icon: LayoutDashboard }, { path: '/super-admin/organizations', label: 'Organizations', icon: Building2 }, { path: '/super-admin/users', label: 'Users', icon: Users }, { path: '/super-admin/reports', label: 'Reports', icon: LineChart }, { path: '/super-admin/notifications', label: 'Notifications', icon: Bell }]
  return <div className={`platform-shell ${collapsed ? 'collapsed' : ''}`}><aside><Link className="brand" to="/super-admin/dashboard"><span className="brand-logo"><ShieldCheck size={22}/></span><b>SUPER ADMIN</b></Link><button type="button" className="hamburger" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed} onClick={() => setCollapsed(value => !value)}><Menu/></button><nav>{links.map(({ path, label, icon: Icon }) => <Link key={path} to={path} className={location.pathname === path ? 'selected' : ''}><Icon size={20}/><span>{label}</span></Link>)}</nav><div className="side-footer">Platform administration</div><button type="button" className="logout" onClick={signOut}>Sign out</button></aside>{collapsed && <button type="button" className="mobile-overlay" aria-label="Close navigation" onClick={() => setCollapsed(false)}/>}<main><header><button type="button" className="mobile-menu" aria-label="Open navigation" onClick={() => setCollapsed(true)}><Menu/></button><div className="header-spacer"/><span className="platform-user"><span className="profile-photo">{user.name[0]}</span><b>{user.name}</b></span></header>{children}</main></div>
}

function PlatformPage({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  const location = useLocation()
  return <section className="content platform-content"><div className="page-head"><div><h1>{title}</h1><p>{pageCopy[location.pathname] || 'Platform administration'}</p></div>{action && <div className="page-actions">{action}</div>}</div>{children}</section>
}

function PlatformDashboardPage() {
  const [summary, setSummary] = useState<{ organizations: number; active_organizations: number; total_customers: number; administrators: number; users: number; unread_notifications: number; active_sessions: number; recent_activity: Array<{ entity_type: string; action: string; actor: string; created_at: string }> } | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get<Envelope<typeof summary>>('/platform/summary').then(response => setSummary(response.data.data)).catch(caught => setError(apiMessage(caught, 'Unable to load platform summary.'))) }, [])
  if (error) return <PlatformPage title="Dashboard"><ErrorState message={error}/></PlatformPage>
  if (!summary) return <PlatformPage title="Dashboard"><LoadingState label="Loading platform data"/></PlatformPage>
  return <PlatformPage title="Dashboard"><div className="metric-grid"><Metric icon={<Users/>} label="Total customers" value={String(summary.total_customers)} note="Across all organizations" tone="purple"/><Metric icon={<Building2/>} label="Organizations" value={String(summary.organizations)} note={`${summary.active_organizations} active`} tone="green"/><Metric icon={<ShieldCheck/>} label="Administrators" value={String(summary.administrators)} note="Organization administrators"/><Metric icon={<Users/>} label="Users" value={String(summary.users)} note="Subscriber accounts"/><Metric icon={<Bell/>} label="Unread notifications" value={String(summary.unread_notifications)} note="Requires attention" tone="orange"/><Metric icon={<CheckCircle2/>} label="Active sessions" value={String(summary.active_sessions)} note="Currently active" tone="purple"/></div><section className="card platform-overview"><div><span><Building2 size={21}/></span><h2>Organization oversight</h2><p>Platform summaries are visible here. Tenant customer details remain private to each organization.</p><Link className="button primary" to="/super-admin/organizations">View organizations <ArrowRight size={15}/></Link></div><div className="platform-principles"><div><Check size={17}/>Tenant-isolated access</div><div><Check size={17}/>Auditable role changes</div><div><Check size={17}/>Live account counts</div></div></section><div className="platform-dashboard-lower"><section className="card platform-activity"><div className="card-head"><h2>Recent Activity</h2><span className="platform-muted">Latest system events</span></div>{summary.recent_activity.length ? summary.recent_activity.map((item, index) => <div className="platform-activity-row" key={`${item.created_at}-${index}`}><span className="platform-activity-icon"><Check size={15}/></span><div><b>{item.action.replaceAll('_', ' ')}</b><small>{item.entity_type.replaceAll('_', ' ')} · {item.actor}</small></div><time>{shortDate(item.created_at)}</time></div>) : <EmptyState title="No recent activity" copy="Platform activity will appear here as organizations use the system."/>}</section><section className="card platform-system-summary"><div className="card-head"><h2>System Summary</h2><span className="platform-muted">Live counts</span></div><div><span>Organizations</span><b>{summary.organizations}</b></div><div><span>Customers</span><b>{summary.total_customers}</b></div><div><span>Active sessions</span><b>{summary.active_sessions}</b></div><div><span>Operational telemetry</span><b>Not connected</b></div></section></div></PlatformPage>
}

function PlatformOrganizationsPage() {
  const [organizations, setOrganizations] = useState<PlatformOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  async function load() { setLoading(true); setError(''); try { const response = await api.get<Envelope<PlatformOrganization[]>>('/platform/organizations?page_size=100'); setOrganizations(response.data.data) } catch (caught) { setError(apiMessage(caught, 'Unable to load organizations.')) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  return <PlatformPage title="Organizations">{loading ? <LoadingState label="Loading organizations"/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : <section className="card table-card"><DataTable rows={organizations} rowKey={row => row.id} searchPlaceholder="Search organizations" searchText={row => `${row.name} ${row.slug}`} statusOf={row => row.status} statuses={['active', 'suspended', 'inactive']} columns={[{ key: 'name', label: 'Organization', render: row => <span className="person"><i className="avatar-square">{row.name.slice(0, 2).toUpperCase()}</i><span>{row.name}<small>{row.slug}</small></span></span> }, { key: 'admins', label: 'Administrators', render: row => row.administrators }, { key: 'users', label: 'Users', render: row => row.users }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'created', label: 'Created', render: row => shortDate(row.created_at) }]}/></section>}</PlatformPage>
}

function PlatformUsersPage() {
  const [users, setUsers] = useState<PlatformUser[]>([])
  const [organizations, setOrganizations] = useState<PlatformOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [toast, setToast] = useState('')
  async function load() {
    setLoading(true); setError('')
    try {
      const [usersResponse, organizationsResponse] = await Promise.all([
        api.get<Envelope<PlatformUser[]>>('/platform/users?page_size=100'),
        api.get<Envelope<PlatformOrganization[]>>('/platform/organizations?page_size=100'),
      ])
      setUsers(usersResponse.data.data)
      setOrganizations(organizationsResponse.data.data)
    } catch (caught) { setError(apiMessage(caught, 'Unable to load platform users.')) } finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])
  const roleLabel = (role: PlatformUser['role']) => role === 'super_admin' ? 'Super Admin' : role === 'org_admin' ? 'Organization administrator' : 'Subscriber user'
  const createDone = async (message: string) => { await load(); setToast(message) }
  return <PlatformPage title="Users" action={<button type="button" className="button primary" onClick={() => setDialogOpen(true)} disabled={!organizations.some(item => item.status === 'active')}><Plus size={16}/>Create user</button>}>
    {loading ? <LoadingState label="Loading platform users"/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : <section className="card table-card"><DataTable rows={users} rowKey={row => row.id} searchPlaceholder="Search users" searchText={row => `${row.name} ${row.email} ${row.organization_name} ${roleLabel(row.role)}`} statusOf={row => row.status} statuses={['active', 'suspended', 'inactive']} columns={[{ key: 'user', label: 'User', render: row => <span className="person"><i className="avatar-square">{row.name.slice(0, 2).toUpperCase()}</i><span>{row.name}<small>{row.email}</small></span></span> }, { key: 'organization', label: 'Organization', render: row => row.organization_name }, { key: 'role', label: 'Role', render: row => roleLabel(row.role) }, { key: 'status', label: 'Status', render: row => <Status>{row.status}</Status> }, { key: 'created', label: 'Created', render: row => shortDate(row.created_at) }]}/></section>}
    {dialogOpen && <PlatformUserDialog organizations={organizations} onClose={() => setDialogOpen(false)} onDone={createDone}/>} {toast && <Toast message={toast} onClose={() => setToast('')}/>}
  </PlatformPage>
}

function PlatformReportsPage() {
  const [report, setReport] = useState<{ organizations: number; active_organizations: number; subscriptions: number; active_subscriptions: number; trialing_subscriptions: number; outstanding_minor: number } | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get<Envelope<typeof report>>('/platform/reports').then(response => setReport(response.data.data)).catch(caught => setError(apiMessage(caught, 'Unable to load platform reports.'))) }, [])
  return <PlatformPage title="Reports">{error ? <ErrorState message={error}/> : !report ? <LoadingState label="Loading reports"/> : <><div className="metric-grid"><Metric icon={<Building2/>} label="Organizations" value={String(report.organizations)} tone="purple"/><Metric icon={<CheckCircle2/>} label="Active organizations" value={String(report.active_organizations)} tone="green"/><Metric icon={<ReceiptText/>} label="Subscriptions" value={String(report.subscriptions)}/><Metric icon={<WalletCards/>} label="Active subscriptions" value={String(report.active_subscriptions)} tone="orange"/></div><section className="card platform-overview"><div><span><LineChart size={21}/></span><h2>Platform billing health</h2><p>{report.trialing_subscriptions} subscriptions are currently trialing. Outstanding tenant invoice balance is {money(report.outstanding_minor)}.</p></div></section></>}</PlatformPage>
}

function PlatformNotificationsPage() {
  return <PlatformPage title="Notifications"><section className="card state-panel"><Bell size={36}/><h2>No platform alerts</h2><p>Tenant notifications remain private to their organizations. Platform alert rules will appear here when configured.</p></section></PlatformPage>
}

function PlatformApp({ user }: { user: AuthUser }) {
  return <PlatformShell user={user}><Routes><Route path="/super-admin/dashboard" element={<PlatformDashboardPage/>}/><Route path="/super-admin/organizations" element={<PlatformOrganizationsPage/>}/><Route path="/super-admin/users" element={<PlatformUsersPage/>}/><Route path="/super-admin/reports" element={<PlatformReportsPage/>}/><Route path="/super-admin/notifications" element={<PlatformNotificationsPage/>}/><Route path="*" element={<Navigate to="/super-admin/dashboard" replace/>}/></Routes></PlatformShell>
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
  const [showPassword, setShowPassword] = useState(false)
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
      const destination = response.data.data.user.role === 'super_admin' ? '/super-admin/dashboard' : response.data.data.user.role === 'user' ? '/portal/dashboard' : '/dashboard'
      navigate(destination, { replace: true })
      window.location.reload()
    } catch (caught) { setError(apiMessage(caught, mode === 'signup' ? 'Unable to create the account.' : 'Unable to sign in.')) } finally { setBusy(false) }
  }
  return <div className="login"><form onSubmit={submit}><span className="brand-logo"><LayoutDashboard size={25}/></span><h1>{mode === 'signup' ? 'Create your account' : 'Welcome to Argo'}</h1><p>{mode === 'signup' ? 'Create the first live account for this organization.' : 'Sign in to Subscription Management'}</p>{mode === 'signup' && <label>Full name<input value={name} onChange={event => setName(event.target.value)} type="text" required minLength={2} maxLength={160} autoComplete="name"/></label>}<label>Email<input value={email} onChange={event => setEmail(event.target.value)} type="email" required autoComplete="username"/></label><label>Password<div className="login-password-field"><input value={password} onChange={event => setPassword(event.target.value)} type={showPassword ? 'text' : 'password'} required minLength={8} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}/><button type="button" className="login-password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>{mode === 'signup' && <label>Confirm password<div className="login-password-field"><input value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} type={showPassword ? 'text' : 'password'} required minLength={8} autoComplete="new-password"/><button type="button" className="login-password-toggle" aria-label={showPassword ? 'Hide confirm password' : 'Show confirm password'} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></label>}{error && <p className="error" role="alert">{error}</p>}<button className="button primary" disabled={busy}>{busy ? (mode === 'signup' ? 'Creating account…' : 'Signing in…') : mode === 'signup' ? 'Create account' : 'Sign in'}</button><button type="button" className="button" onClick={() => { setMode(mode === 'signup' ? 'login' : 'signup'); setError(''); setConfirmPassword(''); setShowPassword(false) }}>{mode === 'signup' ? 'Back to sign in' : 'Create a live account'}</button><Link className="login-return" to="/">Return to landing page</Link></form></div>
}

function ProtectedApp() {
  const user = readUser()
  if (!localStorage.getItem(tokenKey) || !user) return <Navigate to="/login" replace/>
  if (user.role === 'user') return <PortalApp user={user}/>
  if (user.role === 'super_admin') return <PlatformApp user={user}/>
  const has = (scope: string) => user.scopes.includes(scope) || user.scopes.includes('subscription:admin')
  return <AppDataProvider user={user}><Shell><Routes><Route path="/dashboard" element={<DashboardPage/>}/><Route path="/customers" element={<CustomersPage/>}/><Route path="/plans" element={<PlansPage/>}/><Route path="/subscriptions" element={<SubscriptionsPage/>}/><Route path="/payments" element={<PaymentsPage/>}/><Route path="/invoices" element={<InvoicesPage/>}/><Route path="/reports" element={has('subscription:reports') ? <ReportsPage/> : <Navigate to="/dashboard" replace/>}/><Route path="/notifications" element={<NotificationsPage/>}/><Route path="/users" element={has('subscription:admin') ? <UsersPage/> : <Navigate to="/dashboard" replace/>}/><Route path="/settings/*" element={has('subscription:admin') ? <SettingsApp/> : <Navigate to="/dashboard" replace/>}/><Route path="*" element={<NotFoundPage/>}/></Routes></Shell></AppDataProvider>
}

function App() {
  return <Routes><Route path="/" element={<LandingPage/>}/><Route path="/login" element={<LoginPage/>}/><Route path="/*" element={<ProtectedApp/>}/></Routes>
}

createRoot(document.getElementById('root')!).render(<BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><App/></BrowserRouter>)
