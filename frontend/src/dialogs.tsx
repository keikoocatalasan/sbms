import { FormEvent, useEffect, useState } from 'react'
import { AlertCircle, LoaderCircle } from 'lucide-react'
import { api, apiMessage, requestKey } from './api'
import { downloadCsv, Modal, money, shortDate, Status } from './components'
import { useAppData } from './app-data'
import type { Customer, Envelope, Invoice, Plan, Subscription } from './types'

type DialogProps = { onClose: () => void; onDone: (message: string) => Promise<void> | void }

function FormError({ message }: { message: string }) {
  return message ? <p className="form-error" role="alert"><AlertCircle size={16}/>{message}</p> : null
}

function SubmitButton({ busy, label = 'Save' }: { busy: boolean; label?: string }) {
  return <button className="button primary" disabled={busy}>{busy ? <><LoaderCircle className="spin" size={16}/> Saving</> : label}</button>
}

export function CustomerDialog({ customer, onClose, onDone }: DialogProps & { customer?: Customer }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    const payload = { display_name: form.get('display_name'), company_name: form.get('company_name') || null, email: form.get('email') || null, phone: form.get('phone') || null, notes: form.get('notes') || null }
    try {
      if (customer) await api.patch(`/customers/${customer.id}`, payload)
      else await api.post('/customers', { ...payload, customer_type: form.get('customer_type') })
      await onDone(customer ? 'Customer updated.' : 'Customer created.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to save the customer.')) } finally { setBusy(false) }
  }
  return <Modal title={customer ? 'Edit customer' : 'Add customer'} description="Customer changes are saved immediately to the subscription database." onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Customer name<input name="display_name" required maxLength={160} defaultValue={customer?.display_name}/></label>
      {!customer && <label>Customer type<select name="customer_type" defaultValue="individual"><option value="individual">Individual</option><option value="organization">Organization</option></select></label>}
      <label>Company name<input name="company_name" maxLength={160} defaultValue={customer?.company_name ?? ''}/></label>
      <label>Email<input name="email" type="email" defaultValue={customer?.email ?? ''}/></label>
      <label>Phone<input name="phone" maxLength={32} defaultValue={customer?.phone ?? ''}/></label>
      <label className="span-2">Notes<textarea name="notes" maxLength={2000} defaultValue={customer?.notes ?? ''}/></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy}/></div>
    </form>
  </Modal>
}

export function PlanDialog({ plan, onClose, onDone }: DialogProps & { plan?: Plan }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      if (plan) {
        await api.patch(`/plans/${plan.id}`, { name: form.get('name'), description: form.get('description') || null, trial_days: Number(form.get('trial_days')), is_featured: form.get('is_featured') === 'on' })
      } else {
        const code = String(form.get('plan_code')).trim().toUpperCase().replace(/[^A-Z0-9_-]+/g, '-')
        const created = await api.post<Envelope<Plan>>('/plans', { plan_code: code, name: form.get('name'), description: form.get('description') || null, trial_days: Number(form.get('trial_days')), is_featured: form.get('is_featured') === 'on' })
        await api.post(`/plans/${created.data.data.id}/prices`, { price_code: `${code}-${String(form.get('billing_interval')).toUpperCase()}`, billing_interval: form.get('billing_interval'), currency: 'PHP', unit_amount_minor: Math.round(Number(form.get('amount')) * 100), setup_fee_minor: 0, is_default: true })
        await api.patch(`/plans/${created.data.data.id}/status`, { status: 'active' })
      }
      await onDone(plan ? 'Plan details updated. Existing subscription prices were preserved.' : 'Plan and active price created.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to save the plan.')) } finally { setBusy(false) }
  }
  const price = plan?.prices.find(item => item.is_default) ?? plan?.prices[0]
  return <Modal title={plan ? `Edit ${plan.name}` : 'Create subscription plan'} description={plan ? 'Plan prices are immutable billing records. Create a new price when commercial terms change.' : 'Create the plan and its first active price together.'} onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Plan name<input name="name" required maxLength={120} defaultValue={plan?.name}/></label>
      {!plan && <label>Plan code<input name="plan_code" required pattern="[A-Za-z0-9_-]+" placeholder="PROFESSIONAL"/></label>}
      {!plan && <label>Billing interval<select name="billing_interval" defaultValue="month"><option value="month">Monthly</option><option value="year">Annual</option></select></label>}
      {!plan && <label>Price (PHP)<input name="amount" required type="number" min="0" step="0.01" defaultValue={price ? price.unit_amount_minor / 100 : ''}/></label>}
      <label>Trial days<input name="trial_days" type="number" min="0" max="365" defaultValue={plan?.trial_days ?? 7}/></label>
      <label className="checkbox"><input name="is_featured" type="checkbox" defaultChecked={plan?.is_featured}/> Highlight this plan</label>
      <label className="span-2">Description and included features<textarea name="description" maxLength={2000} defaultValue={plan?.description ?? ''} placeholder="Describe the intended customer and included service."/></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy}/></div>
    </form>
  </Modal>
}

export function SubscriptionDialog({ onClose, onDone }: DialogProps) {
  const { customers, plans, settings } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const prices = plans.flatMap(plan => plan.prices.filter(price => plan.status === 'active' && price.status === 'active').map(price => ({ plan, price })))
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const response = await api.post('/subscriptions', { customer_id: form.get('customer_id'), plan_price_id: form.get('price_id'), starts_at: new Date().toISOString(), auto_renew: form.get('auto_renew') === 'on', use_trial: form.get('use_trial') === 'on' }, { headers: { 'Idempotency-Key': requestKey() } })
      const hasInvoice = Boolean(response.data.data.invoice)
      await onDone(hasInvoice ? 'Subscription created with an open invoice. Allocate a payment to activate it.' : 'Trial subscription started.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to create the subscription.')) } finally { setBusy(false) }
  }
  return <Modal title="New subscription" description="Trials begin immediately. Non-trial subscriptions create an invoice and remain pending until that invoice is paid." onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Customer<select name="customer_id" required defaultValue=""><option value="" disabled>Select customer</option>{customers.filter(customer => customer.status === 'active').map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label>
      <label>Plan and price<select name="price_id" required defaultValue=""><option value="" disabled>Select active price</option>{prices.map(({ plan, price }) => <option key={price.id} value={price.id}>{plan.name} — {money(price.unit_amount_minor, price.currency)} / {price.billing_interval}</option>)}</select></label>
      <label className="checkbox"><input name="use_trial" type="checkbox" defaultChecked/> Use the plan trial when eligible</label>
      <label className="checkbox"><input name="auto_renew" type="checkbox" defaultChecked={settings?.auto_renew_default ?? true}/> Renew automatically</label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Create subscription"/></div>
    </form>
  </Modal>
}

export function PaymentDialog({ onClose, onDone }: DialogProps) {
  const { customers, invoices } = useAppData()
  const [customerId, setCustomerId] = useState('')
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const openInvoices = invoices.filter(invoice => invoice.customer_id === customerId && invoice.amounts.balance_minor > 0 && !['void', 'paid'].includes(invoice.status))
  useEffect(() => { setInvoiceId(''); setAmount('') }, [customerId])
  function chooseInvoice(id: string) {
    setInvoiceId(id)
    const invoice = invoices.find(item => item.id === id)
    setAmount(invoice ? String(invoice.amounts.balance_minor / 100) : '')
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    const amountMinor = Math.round(Number(amount) * 100)
    const allocations = invoiceId ? [{ invoice_id: invoiceId, amount_minor: amountMinor }] : []
    try {
      await api.post('/payments', { customer_id: customerId, payment_method: form.get('payment_method'), amount_minor: amountMinor, currency: 'PHP', external_reference: form.get('reference') || null, notes: form.get('notes') || null, allocations }, { headers: { 'Idempotency-Key': requestKey() } })
      await onDone(invoiceId ? 'Payment recorded and allocated to the invoice.' : 'On-account payment recorded as unallocated credit.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to record the payment.')) } finally { setBusy(false) }
  }
  return <Modal title="Record payment" description="Choose an invoice to reduce its balance and activate a pending subscription when fully paid." onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Customer<select required value={customerId} onChange={event => setCustomerId(event.target.value)}><option value="" disabled>Select customer</option>{customers.filter(customer => customer.status === 'active').map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label>
      <label>Invoice allocation<select value={invoiceId} onChange={event => chooseInvoice(event.target.value)} disabled={!customerId}><option value="">Unallocated account credit</option>{openInvoices.map(invoice => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} — {money(invoice.amounts.balance_minor, invoice.currency)} due</option>)}</select></label>
      <label>Payment method<select name="payment_method" defaultValue="manual_bank"><option value="manual_bank">Bank transfer</option><option value="manual_cash">Cash</option></select></label>
      <label>Amount (PHP)<input required type="number" min="0.01" step="0.01" value={amount} onChange={event => setAmount(event.target.value)}/></label>
      <label>Reference<input name="reference" maxLength={128} placeholder="BANK-2026-001"/></label>
      <label>Notes<input name="notes" maxLength={2000}/></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Record payment"/></div>
    </form>
  </Modal>
}

export function InvoiceDialog({ onClose, onDone }: DialogProps) {
  const { customers } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      await api.post('/invoices', { customer_id: form.get('customer_id'), issue_date: new Date().toISOString().slice(0, 10), due_date: form.get('due_date'), currency: 'PHP', notes: form.get('notes') || null, items: [{ item_type: 'adjustment', description: form.get('description'), quantity: 1, unit_amount_minor: Math.round(Number(form.get('amount')) * 100), tax_rate_bps: 0 }] }, { headers: { 'Idempotency-Key': requestKey() } })
      await onDone('Draft invoice created. Finalize it when ready to send.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to create the invoice.')) } finally { setBusy(false) }
  }
  const due = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10)
  return <Modal title="Generate invoice" description="Manual invoices start as drafts so they can be reviewed before finalization." onClose={onClose}>
    <form onSubmit={submit} className="form-grid"><label>Customer<select name="customer_id" required defaultValue=""><option value="" disabled>Select customer</option>{customers.filter(customer => customer.status === 'active').map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label><label>Due date<input name="due_date" type="date" required defaultValue={due}/></label><label className="span-2">Description<input name="description" required maxLength={255}/></label><label>Amount (PHP)<input name="amount" required type="number" min="0" step="0.01"/></label><label>Notes<input name="notes" maxLength={2000}/></label><FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Create draft"/></div></form>
  </Modal>
}

export function NotificationDialog({ onClose, onDone }: DialogProps) {
  const { customers } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      await api.post('/notifications', { customer_id: form.get('customer_id') || null, notification_type: form.get('notification_type'), title: form.get('title'), body: form.get('body') })
      await onDone('Notification created.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to create the notification.')) } finally { setBusy(false) }
  }
  return <Modal title="New notification" description="Create an in-app notice for one customer or the whole account." onClose={onClose}>
    <form onSubmit={submit} className="form-grid"><label>Recipient<select name="customer_id"><option value="">All users</option>{customers.map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label><label>Type<select name="notification_type" defaultValue="manual_notice"><option value="manual_notice">General notice</option><option value="payment_reminder">Payment reminder</option><option value="subscription_update">Subscription update</option></select></label><label className="span-2">Title<input name="title" required maxLength={160}/></label><label className="span-2">Message<textarea name="body" required maxLength={4000}/></label><FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy}/></div></form>
  </Modal>
}

export function SubscriptionCommandDialog({ subscription, mode, onClose, onDone }: DialogProps & { subscription: Subscription; mode: 'change-plan' | 'schedule-cancel' | 'cancel-now' }) {
  const { plans } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const prices = plans.flatMap(plan => plan.prices.filter(price => plan.status === 'active' && price.status === 'active' && price.id !== subscription.plan_price_id).map(price => ({ plan, price })))
  const title = mode === 'change-plan' ? 'Schedule plan change' : mode === 'cancel-now' ? 'Cancel subscription now' : 'Schedule cancellation'
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      if (mode === 'change-plan') await api.post(`/subscriptions/${subscription.id}/schedule-plan-change`, { expected_version: subscription.version, target_plan_price_id: form.get('target_price_id'), reason: form.get('reason') || null })
      else await api.post(`/subscriptions/${subscription.id}/${mode === 'cancel-now' ? 'cancel-now' : 'schedule-cancellation'}`, { expected_version: subscription.version, reason: form.get('reason') || null })
      await onDone(mode === 'change-plan' ? 'Plan change scheduled for the end of the current period.' : mode === 'cancel-now' ? 'Subscription cancelled immediately.' : 'Cancellation scheduled for the end of the current period.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to update the subscription.')) } finally { setBusy(false) }
  }
  return <Modal title={title} description={mode === 'cancel-now' ? 'Access ends immediately. This action cannot be reversed.' : 'The customer keeps access through the current billing or trial period.'} onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      {mode === 'change-plan' && <label className="span-2">New plan<select name="target_price_id" required defaultValue=""><option value="" disabled>Select active price</option>{prices.map(({ plan, price }) => <option value={price.id} key={price.id}>{plan.name} — {money(price.unit_amount_minor, price.currency)} / {price.billing_interval}</option>)}</select></label>}
      <label className="span-2">Reason<textarea name="reason" maxLength={2000} placeholder="Optional internal note"/></label><FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label={mode === 'change-plan' ? 'Schedule change' : mode === 'cancel-now' ? 'Cancel now' : 'Schedule cancellation'}/></div>
    </form>
  </Modal>
}

export function CustomerProfileDialog({ customer, onClose }: { customer: Customer; onClose: () => void }) {
  const { subscriptions, plans, invoices, payments } = useAppData()
  const customerSubscriptions = subscriptions.filter(item => item.customer_id === customer.id)
  const customerInvoices = invoices.filter(item => item.customer_id === customer.id)
  const customerPayments = payments.filter(item => item.customer_id === customer.id)
  return <Modal title={customer.display_name} description={`${customer.customer_code} · ${customer.email ?? 'No email'}`} onClose={onClose} wide>
    <div className="detail-grid"><section><h3>Subscriptions</h3>{customerSubscriptions.length ? customerSubscriptions.map(item => <div className="detail-line" key={item.id}><span>{plans.find(plan => plan.id === item.plan_id)?.name ?? item.subscription_number}</span><Status>{item.status}</Status></div>) : <p>No subscriptions.</p>}</section><section><h3>Billing</h3><div className="detail-line"><span>Invoices</span><b>{customerInvoices.length}</b></div><div className="detail-line"><span>Paid total</span><b>{money(customerPayments.reduce((sum, item) => sum + item.amount_minor - item.unallocated_minor, 0))}</b></div><div className="detail-line"><span>Outstanding</span><b>{money(customerInvoices.reduce((sum, item) => sum + item.amounts.balance_minor, 0))}</b></div></section></div>
  </Modal>
}

export function InvoiceDetailDialog({ invoice, onClose }: { invoice: Invoice; onClose: () => void }) {
  const { customers } = useAppData()
  const [detail, setDetail] = useState<(Invoice & { items?: Array<{ id: string; description: string; quantity: number; unit_amount_minor: number }> }) | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get<Envelope<Invoice & { items: Array<{ id: string; description: string; quantity: number; unit_amount_minor: number }> }>>(`/invoices/${invoice.id}`).then(response => setDetail(response.data.data)).catch(caught => setError(apiMessage(caught))) }, [invoice.id])
  const customer = customers.find(item => item.id === invoice.customer_id)
  const exportInvoice = () => downloadCsv(`${invoice.invoice_number}.csv`, [['Invoice', invoice.invoice_number], ['Customer', customer?.display_name ?? invoice.customer_id], ['Status', invoice.status], ['Issue date', invoice.issue_date], ['Due date', invoice.due_date], ['Total', money(invoice.amounts.total_minor, invoice.currency)], ['Paid', money(invoice.amounts.paid_minor, invoice.currency)], ['Balance', money(invoice.amounts.balance_minor, invoice.currency)], [], ['Description', 'Quantity', 'Amount'], ...(detail?.items ?? []).map(item => [item.description, item.quantity, money(item.unit_amount_minor, invoice.currency)])])
  return <Modal title={invoice.invoice_number} description={`${customer?.display_name ?? 'Customer'} · issued ${shortDate(invoice.issue_date)}`} onClose={onClose} wide>{error && <FormError message={error}/>}<div className="invoice-summary"><Status>{invoice.status}</Status><span>Total <b>{money(invoice.amounts.total_minor, invoice.currency)}</b></span><span>Paid <b>{money(invoice.amounts.paid_minor, invoice.currency)}</b></span><span>Balance <b>{money(invoice.amounts.balance_minor, invoice.currency)}</b></span></div>{detail ? <div className="invoice-items">{(detail.items ?? []).map(item => <div key={item.id}><span>{item.description} × {item.quantity}</span><b>{money(item.unit_amount_minor * item.quantity, invoice.currency)}</b></div>)}</div> : !error && <p>Loading invoice items…</p>}<div className="modal-actions"><button type="button" className="button" onClick={onClose}>Close</button><button type="button" className="button primary" onClick={exportInvoice}>Download CSV</button></div></Modal>
}
