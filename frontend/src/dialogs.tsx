import { FormEvent, useEffect, useState } from 'react'
import { AlertCircle, Eye, EyeOff, LoaderCircle, Pencil, Plus, Trash2 } from 'lucide-react'
import { api, apiMessage, requestKey } from './api'
import { ConfirmDialog, downloadCsv, EmptyState, Modal, money, shortDate, Status } from './components'
import { useAppData } from './app-data'
import type { Customer, Envelope, Feature, Invoice, Payment, Plan, PlanPrice, PlatformOrganization, Subscription } from './types'

type DialogProps = { onClose: () => void; onDone: (message: string) => Promise<void> | void }

function FormError({ message }: { message: string }) {
  return message ? <p className="form-error" role="alert"><AlertCircle size={16}/>{message}</p> : null
}

function SubmitButton({ busy, label = 'Save' }: { busy: boolean; label?: string }) {
  return <button className="button primary" disabled={busy}>{busy ? <><LoaderCircle className="spin" size={16}/> Saving</> : label}</button>
}

export function PlatformUserDialog({ organizations, onClose, onDone }: DialogProps & { organizations: PlatformOrganization[] }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      await api.post('/platform/users', { organization_id: form.get('organization_id'), name: form.get('name'), email: form.get('email'), password: form.get('password'), role: form.get('role') })
      await onDone('User created. Share the temporary password securely; it will not be shown again.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to create the platform user.')) } finally { setBusy(false) }
  }
  return <Modal wide title="Create platform user" description="Create a subscriber or organization administrator inside an active organization. Super Admin accounts are managed through the platform allowlist." onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Organization<select name="organization_id" required defaultValue=""><option value="" disabled>Select organization</option>{organizations.filter(item => item.status === 'active').map(organization => <option key={organization.id} value={organization.id}>{organization.name}</option>)}</select></label>
      <label>Role<select name="role" defaultValue="user"><option value="user">Subscriber user</option><option value="org_admin">Organization administrator</option></select></label>
      <label>Full name<input name="name" required minLength={2} maxLength={160} autoComplete="name"/></label>
      <label>Email<input name="email" type="email" required autoComplete="username"/></label>
      <label className="span-2">Temporary password<div className="login-password-field"><input name="password" type={showPassword ? 'text' : 'password'} required minLength={8} maxLength={128} autoComplete="new-password"/><button type="button" className="login-password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(value => !value)}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div><small className="form-hint">The password is stored securely and is not returned after creation.</small></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Create user"/></div>
    </form>
  </Modal>
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
  const { settings } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      if (plan) {
        await api.patch(`/plans/${plan.id}`, { name: form.get('name'), description: form.get('description') || null, trial_days: Number(form.get('trial_days')), is_featured: form.get('is_featured') === 'on', display_order: Number(form.get('display_order')) })
      } else {
        const code = String(form.get('plan_code')).trim().toUpperCase().replace(/[^A-Z0-9_-]+/g, '-')
        const currency = settings?.default_currency ?? 'PHP'
        const monthlyList = Math.round(Number(form.get('monthly_amount')) * 100)
        const monthlyDiscount = Math.round(Number(form.get('monthly_discount') || 0) * 100)
        const annualInput = String(form.get('annual_amount') ?? '').trim()
        const annualDiscount = Math.round(Number(form.get('annual_discount') || 0) * 100)
        if (annualInput && annualDiscount <= monthlyDiscount) {
          setError('Annual discount must be greater than the monthly discount.')
          setBusy(false)
          return
        }
        const created = await api.post<Envelope<Plan>>('/plans', { plan_code: code, name: form.get('name'), description: form.get('description') || null, trial_days: Number(form.get('trial_days')), is_featured: form.get('is_featured') === 'on' })
        await api.post(`/plans/${created.data.data.id}/prices`, { price_code: `${code}-MONTH`, billing_interval: 'month', currency, list_amount_minor: monthlyList, unit_amount_minor: Math.round(monthlyList * (10000 - monthlyDiscount) / 10000), discount_bps: monthlyDiscount, setup_fee_minor: 0, is_default: true })
        if (annualInput) {
          const annualList = Math.round(Number(annualInput) * 100)
          await api.post(`/plans/${created.data.data.id}/prices`, { price_code: `${code}-YEAR`, billing_interval: 'year', currency, list_amount_minor: annualList, unit_amount_minor: Math.round(annualList * (10000 - annualDiscount) / 10000), discount_bps: annualDiscount, setup_fee_minor: 0, is_default: true })
        }
        await api.patch(`/plans/${created.data.data.id}/status`, { status: 'active' })
      }
      await onDone(plan ? 'Plan details updated. Existing subscription prices were preserved.' : 'Plan and active price created.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to save the plan.')) } finally { setBusy(false) }
  }
  return <Modal title={plan ? `Edit ${plan.name}` : 'Create subscription plan'} description={plan ? 'Plan prices are immutable billing records. Create a new price when commercial terms change.' : 'Create the plan and its first active price together.'} onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Plan name<input name="name" required maxLength={120} defaultValue={plan?.name}/></label>
      {!plan && <label>Plan code<input name="plan_code" required pattern="[A-Za-z0-9_-]+" placeholder="PROFESSIONAL"/></label>}
      {!plan && <label>Monthly list price ({settings?.default_currency ?? 'PHP'})<input name="monthly_amount" required type="number" min="0" step="0.01"/></label>}
      {!plan && <label>Monthly discount (%)<input name="monthly_discount" type="number" min="0" max="100" step="0.01" defaultValue="0"/></label>}
      {!plan && <label>Annual list price ({settings?.default_currency ?? 'PHP'})<input name="annual_amount" type="number" min="0" step="0.01"/></label>}
      {!plan && <label>Annual discount (%)<input name="annual_discount" type="number" min="0" max="100" step="0.01" defaultValue="0"/></label>}
      <label>Trial days<input name="trial_days" type="number" min="0" max="365" defaultValue={plan?.trial_days ?? 7}/></label>
      <label>Display order<input name="display_order" type="number" min="0" max="10000" defaultValue={plan?.display_order ?? 0}/></label>
      <label className="checkbox"><input name="is_featured" type="checkbox" defaultChecked={plan?.is_featured}/> Highlight this plan</label>
      <label className="span-2">Description and included features<textarea name="description" maxLength={2000} defaultValue={plan?.description ?? ''} placeholder="Describe the intended customer and included service."/></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy}/></div>
    </form>
  </Modal>
}

export function PlanPriceDialog({ plan, price, used = false, onClose, onDone }: DialogProps & { plan: Plan; price?: PlanPrice; used?: boolean }) {
  const { settings } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      if (price) {
        const payload: Record<string, unknown> = { is_default: form.get('is_default') === 'on', status: form.get('status') }
        if (!used) {
          const listAmountMinor = Math.round(Number(form.get('amount')) * 100)
          const discountBps = Math.round(Number(form.get('discount') || 0) * 100)
          payload.list_amount_minor = listAmountMinor
          payload.unit_amount_minor = Math.round(listAmountMinor * (10000 - discountBps) / 10000)
          payload.setup_fee_minor = Math.round(Number(form.get('setup_fee')) * 100)
          payload.effective_from = form.get('effective_from')
          payload.discount_bps = discountBps
        }
        await api.patch(`/plans/${plan.id}/prices/${price.id}`, payload)
        await onDone('Plan price updated.');
      } else {
        const listAmountMinor = Math.round(Number(form.get('amount')) * 100)
        const discountBps = Math.round(Number(form.get('discount') || 0) * 100)
        await api.post(`/plans/${plan.id}/prices`, { price_code: String(form.get('price_code')).trim().toUpperCase(), billing_interval: form.get('billing_interval'), interval_count: Number(form.get('interval_count')), currency: form.get('currency'), list_amount_minor: listAmountMinor, unit_amount_minor: Math.round(listAmountMinor * (10000 - discountBps) / 10000), discount_bps: discountBps, setup_fee_minor: Math.round(Number(form.get('setup_fee')) * 100), effective_from: form.get('effective_from'), is_default: form.get('is_default') === 'on' })
        await onDone('New plan price created. Existing subscription prices were preserved.');
      }
      onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to create the plan price.')) } finally { setBusy(false) }
  }
  return <Modal title={price ? `Edit ${plan.name} price` : `Add price to ${plan.name}`} description={price ? used ? 'This price is used by existing subscriptions. Only its default and availability status can change.' : 'Amount, setup fee, effective date, default status, and availability can be edited until the price is used by a subscription.' : 'Price codes, intervals, and currencies identify a billing record. Create a new version when commercial terms change.'} onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      {!price && <label>Price code<input name="price_code" required pattern="[A-Za-z0-9_-]+" defaultValue={`${plan.plan_code}-MONTH-${Date.now().toString().slice(-4)}`}/></label>}
      {price && <label>Price code<input value={price.price_code} readOnly/></label>}
      <label>Billing interval<select name="billing_interval" defaultValue={price?.billing_interval ?? 'month'} disabled={Boolean(price)}><option value="month">Monthly</option><option value="year">Annual</option></select></label>
      <label>Interval count<input name="interval_count" type="number" min="1" max="12" defaultValue={price?.interval_count ?? 1} readOnly={Boolean(price)}/></label>
      <label>Currency<select name="currency" defaultValue={price?.currency ?? settings?.default_currency ?? 'PHP'} disabled={Boolean(price)}><option value="PHP">PHP - Philippine Peso</option><option value="USD">USD - US Dollar</option></select></label>
      <label>List price ({price?.currency ?? settings?.default_currency ?? 'PHP'})<input name="amount" required type="number" min="0" step="0.01" defaultValue={price ? (price.list_amount_minor ?? price.unit_amount_minor) / 100 : ''} disabled={used}/></label>
      <label>Discount (%)<input name="discount" required type="number" min="0" max="100" step="0.01" defaultValue={price ? price.discount_bps / 100 : 0} disabled={used}/></label>
      <label>Setup fee ({price?.currency ?? settings?.default_currency ?? 'PHP'})<input name="setup_fee" required type="number" min="0" step="0.01" defaultValue={price ? price.setup_fee_minor / 100 : 0} disabled={used}/></label>
      <label>Effective from<input name="effective_from" type="date" required defaultValue={price?.effective_from ?? new Date().toISOString().slice(0, 10)} disabled={used}/></label>
      <label>Status<select name="status" defaultValue={price?.status ?? 'active'}><option value="active">Active</option><option value="inactive">Inactive</option><option value="archived">Archived</option></select></label>
      <label className="checkbox"><input name="is_default" type="checkbox" defaultChecked={price?.is_default ?? true}/> Make default for this interval</label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Create price"/></div>
    </form>
  </Modal>
}

export function FeatureDialog({ feature, onClose, onDone }: DialogProps & { feature?: Feature }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const values = { name: form.get('name'), description: form.get('description') || null, unit_label: form.get('unit_label') || null }
      if (feature) await api.patch(`/features/${feature.id}`, { ...values, status: form.get('status') })
      else await api.post('/features', { feature_code: String(form.get('feature_code')).trim().toUpperCase(), ...values, value_type: form.get('value_type') })
      await onDone(feature ? 'Feature updated.' : 'Feature created.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to save the feature.')) } finally { setBusy(false) }
  }
  return <Modal title={feature ? `Edit ${feature.name}` : 'Create feature'} description={feature ? 'Feature names, descriptions, units, and availability can be updated. The value type is immutable after creation.' : 'Create a reusable capability that can be assigned to any subscription plan.'} onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      {!feature && <label>Feature code<input name="feature_code" required pattern="[A-Za-z0-9_-]+" placeholder="PRIORITY_SUPPORT"/></label>}
      {feature && <label>Feature code<input value={feature.feature_code} readOnly/></label>}
      <label>Feature name<input name="name" required maxLength={120} defaultValue={feature?.name}/></label>
      {!feature && <label>Value type<select name="value_type" defaultValue="boolean"><option value="boolean">Included / not included</option><option value="number">Numeric limit</option><option value="text">Text value</option></select></label>}
      {feature && <label>Value type<input value={feature.value_type} readOnly/></label>}
      <label>Unit label<input name="unit_label" maxLength={40} defaultValue={feature?.unit_label ?? ''} placeholder="users, GB, calls"/></label>
      {feature && <label>Status<select name="status" defaultValue={feature.status}><option value="active">Active</option><option value="inactive">Inactive</option><option value="archived">Archived</option></select></label>}
      <label className="span-2">Description<textarea name="description" maxLength={2000} defaultValue={feature?.description ?? ''}/></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy}/></div>
    </form>
  </Modal>
}

export function PlanFeaturesDialog({ plan, onClose, onDone }: DialogProps & { plan: Plan }) {
  const { features } = useAppData()
  const existing = plan.features ?? []
  const [selected, setSelected] = useState<Record<string, boolean>>(() => Object.fromEntries(existing.map(item => [item.feature_id, item.is_included])))
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(existing.map(item => [item.feature_id, item.value_number != null ? String(item.value_number) : item.value_text ?? ''])))
  const [intervals, setIntervals] = useState<Record<string, string>>(() => Object.fromEntries(existing.map(item => [item.feature_id, item.billing_interval ?? ''])))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      for (const [index, feature] of features.entries()) {
        if (selected[feature.id]) {
          const raw = values[feature.id] ?? ''
          await api.put(`/plans/${plan.id}/features`, { feature_id: feature.id, billing_interval: intervals[feature.id] || null, is_included: true, value_boolean: feature.value_type === 'boolean' ? true : null, value_number: feature.value_type === 'number' && raw !== '' ? Number(raw) : null, value_text: feature.value_type === 'text' ? raw || null : null, display_order: index })
        }
      }
      for (const item of existing) if (!selected[item.feature_id]) await api.delete(`/plans/${plan.id}/features/${item.feature_id}`)
      await onDone('Plan features updated.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to update plan features.')) } finally { setBusy(false) }
  }
  return <Modal wide title={`Features for ${plan.name}`} description="Choose the capabilities included in this plan. Values are stored with the plan and shown to subscribers." onClose={onClose}>
    <form onSubmit={submit} className="feature-form">
      {features.length ? <div className="feature-list">{features.map(feature => <div className="feature-edit-row" key={feature.id}><label className="checkbox"><input type="checkbox" checked={Boolean(selected[feature.id])} onChange={event => setSelected(current => ({ ...current, [feature.id]: event.target.checked }))}/><span><b>{feature.name}</b><small>{feature.description || feature.feature_code}</small></span></label><select value={intervals[feature.id] ?? ''} disabled={!selected[feature.id]} onChange={event => setIntervals(current => ({ ...current, [feature.id]: event.target.value }))} aria-label={`Billing cycle for ${feature.name}`}><option value="">All cycles</option><option value="month">Monthly only</option><option value="year">Annual only</option></select>{feature.value_type === 'number' && <input type="number" min="0" value={values[feature.id] ?? ''} disabled={!selected[feature.id]} onChange={event => setValues(current => ({ ...current, [feature.id]: event.target.value }))} placeholder={feature.unit_label ?? 'Limit'}/>} {feature.value_type === 'text' && <input value={values[feature.id] ?? ''} disabled={!selected[feature.id]} onChange={event => setValues(current => ({ ...current, [feature.id]: event.target.value }))} placeholder={feature.unit_label ?? 'Value'}/>}</div>)}</div> : <p className="empty-state">No features exist yet. Create them from the feature catalog.</p>}
      <FormError message={error}/><div className="modal-actions"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Save features"/></div>
    </form>
  </Modal>
}

export function FeatureCatalogDialog({ onClose, onDone }: DialogProps) {
  const { features } = useAppData()
  const [editor, setEditor] = useState<'new' | Feature | null>(null)
  const [removeTarget, setRemoveTarget] = useState<Feature | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function remove() {
    if (!removeTarget) return
    setBusy(true); setError('')
    try { await api.delete(`/features/${removeTarget.id}`); await onDone('Feature removed.'); setRemoveTarget(null) } catch (caught) { setError(apiMessage(caught, 'Unable to remove the feature.')) } finally { setBusy(false) }
  }
  return <Modal wide title="Feature catalog" description="Create and maintain reusable plan capabilities. Removing a linked feature archives it to preserve plan history." onClose={onClose}>
    <div className="feature-catalog"><button type="button" className="button primary" onClick={() => setEditor('new')}><Plus size={16}/>Add feature</button>{features.map(feature => <div className="feature-catalog-row" key={feature.id}><div><b>{feature.name}</b><small>{feature.feature_code} · {feature.value_type}{feature.unit_label ? ` · ${feature.unit_label}` : ''}</small></div><div><button type="button" className="icon-button" aria-label={`Edit ${feature.name}`} onClick={() => setEditor(feature)}><Pencil size={15}/></button><button type="button" className="icon-button danger-text" aria-label={`Remove ${feature.name}`} onClick={() => setRemoveTarget(feature)}><Trash2 size={15}/></button></div></div>)}{!features.length && <EmptyState title="No features" copy="Create the first feature to assign capabilities to a plan."/>}{error && <FormError message={error}/>}</div>{editor && <FeatureDialog feature={editor === 'new' ? undefined : editor} onClose={() => setEditor(null)} onDone={onDone}/>} {removeTarget && <ConfirmDialog title="Remove feature" message={`Remove ${removeTarget.name}? Linked plan features will be archived instead of deleted.`} confirmLabel="Remove feature" danger busy={busy} onCancel={() => setRemoveTarget(null)} onConfirm={() => void remove()}/>}</Modal>
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
  const { customers, invoices, settings } = useAppData()
  const [customerId, setCustomerId] = useState('')
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const openInvoices = invoices.filter(invoice => invoice.customer_id === customerId && invoice.amounts.balance_minor > 0 && invoice.status !== 'void')
  const selectedInvoice = invoices.find(invoice => invoice.id === invoiceId)
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
      await api.post('/payments', { customer_id: customerId, payment_method: form.get('payment_method'), amount_minor: amountMinor, currency: selectedInvoice?.currency ?? settings?.default_currency ?? 'PHP', external_reference: form.get('reference') || null, notes: form.get('notes') || null, allocations }, { headers: { 'Idempotency-Key': requestKey() } })
      await onDone(invoiceId ? 'Payment recorded and allocated to the invoice.' : 'On-account payment recorded as unallocated credit.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to record the payment.')) } finally { setBusy(false) }
  }
  return <Modal title="Record payment" description="Choose an invoice to reduce its balance and activate a pending subscription when fully paid." onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label>Customer<select required value={customerId} onChange={event => setCustomerId(event.target.value)}><option value="" disabled>Select customer</option>{customers.filter(customer => customer.status === 'active').map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label>
      <label>Invoice allocation<select value={invoiceId} onChange={event => chooseInvoice(event.target.value)} disabled={!customerId}><option value="">Unallocated account credit</option>{openInvoices.map(invoice => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} — {money(invoice.amounts.balance_minor, invoice.currency)} due</option>)}</select></label>
      <label>Payment method<select name="payment_method" defaultValue="manual_bank"><option value="manual_bank">Bank transfer</option><option value="manual_cash">Cash</option></select></label>
      <label>Amount ({selectedInvoice?.currency ?? settings?.default_currency ?? 'PHP'})<input required type="number" min="0.01" step="0.01" value={amount} onChange={event => setAmount(event.target.value)}/></label>
      <label>Reference<input name="reference" maxLength={128} placeholder="BANK-2026-001"/></label>
      <label>Notes<input name="notes" maxLength={2000}/></label>
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Record payment"/></div>
    </form>
  </Modal>
}

export function PaymentAllocationDialog({ payment, onClose, onDone }: DialogProps & { payment: Payment }) {
  const { customers, invoices, settings } = useAppData()
  const [invoiceId, setInvoiceId] = useState('')
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const customer = customers.find(item => item.id === payment.customer_id)
  const openInvoices = invoices.filter(invoice => invoice.customer_id === payment.customer_id && invoice.currency === payment.currency && invoice.amounts.balance_minor > 0 && invoice.status !== 'void')
  const selectedInvoice = openInvoices.find(invoice => invoice.id === invoiceId)
  useEffect(() => {
    if (!selectedInvoice) { setAmount(''); return }
    const maximum = Math.min(payment.unallocated_minor, selectedInvoice.amounts.balance_minor)
    setAmount(String(maximum / 100))
  }, [payment.unallocated_minor, selectedInvoice])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const amountMinor = Math.round(Number(amount) * 100)
    try {
      await api.post(`/payments/${payment.id}/allocate`, { allocations: [{ invoice_id: invoiceId, amount_minor: amountMinor }] }, { headers: { 'Idempotency-Key': requestKey() } })
      await onDone('Existing payment credit allocated and billing status synchronized.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to allocate the payment.')) } finally { setBusy(false) }
  }
  return <Modal title="Allocate payment credit" description={`Apply ${money(payment.unallocated_minor, payment.currency)} of ${customer?.display_name ?? 'this customer'}'s existing credit to an open invoice.`} onClose={onClose}>
    <form onSubmit={submit} className="form-grid">
      <label className="span-2">Invoice<select required value={invoiceId} onChange={event => setInvoiceId(event.target.value)}><option value="" disabled>Select open invoice</option>{openInvoices.map(invoice => <option key={invoice.id} value={invoice.id}>{invoice.invoice_number} — {money(invoice.amounts.balance_minor, invoice.currency)} due</option>)}</select></label>
      <label>Amount ({payment.currency})<input required type="number" min="0.01" step="0.01" max={selectedInvoice ? Math.min(payment.unallocated_minor, selectedInvoice.amounts.balance_minor) / 100 : undefined} value={amount} onChange={event => setAmount(event.target.value)} disabled={!selectedInvoice}/></label>
      <p className="form-hint">{settings?.allow_partial_payments === false ? 'Partial payments are disabled; the full invoice balance is required.' : 'A fully allocated invoice activates a pending subscription.'}</p>
      {!openInvoices.length && <FormError message="No open invoice matches this payment's customer and currency."/>}
      <FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Allocate credit"/></div>
    </form>
  </Modal>
}

export function InvoiceDialog({ onClose, onDone }: DialogProps) {
  const { customers, settings } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      await api.post('/invoices', { customer_id: form.get('customer_id'), issue_date: new Date().toISOString().slice(0, 10), due_date: form.get('due_date'), currency: settings?.default_currency ?? 'PHP', notes: form.get('notes') || null, items: [{ item_type: 'adjustment', description: form.get('description'), quantity: 1, unit_amount_minor: Math.round(Number(form.get('amount')) * 100), tax_rate_bps: 0 }] }, { headers: { 'Idempotency-Key': requestKey() } })
      await onDone('Draft invoice created. Finalize it when ready to send.'); onClose()
    } catch (caught) { setError(apiMessage(caught, 'Unable to create the invoice.')) } finally { setBusy(false) }
  }
  const due = new Date(Date.now() + (settings?.invoice_due_days ?? 7) * 86400000).toISOString().slice(0, 10)
  return <Modal title="Generate invoice" description="Manual invoices start as drafts so they can be reviewed before finalization." onClose={onClose}>
    <form onSubmit={submit} className="form-grid"><label>Customer<select name="customer_id" required defaultValue=""><option value="" disabled>Select customer</option>{customers.filter(customer => customer.status === 'active').map(customer => <option key={customer.id} value={customer.id}>{customer.display_name}</option>)}</select></label><label>Due date<input name="due_date" type="date" required defaultValue={due}/></label><label className="span-2">Description<input name="description" required maxLength={255}/></label><label>Amount ({settings?.default_currency ?? 'PHP'})<input name="amount" required type="number" min="0" step="0.01"/></label><label>Notes<input name="notes" maxLength={2000}/></label><FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy} label="Create draft"/></div></form>
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
  return <Modal title="New notification" description="Create an in-app notice for all account users or attach it to a customer record." onClose={onClose}>
    <form onSubmit={submit} className="form-grid"><label>Audience<select name="customer_id"><option value="">All account users</option>{customers.map(customer => <option key={customer.id} value={customer.id}>Customer context: {customer.display_name}</option>)}</select></label><label>Type<select name="notification_type" defaultValue="manual_notice"><option value="manual_notice">General notice</option><option value="payment_reminder">Payment reminder</option><option value="subscription_update">Subscription update</option></select></label><label className="span-2">Title<input name="title" required maxLength={160}/></label><label className="span-2">Message<textarea name="body" required maxLength={4000}/></label><FormError message={error}/><div className="modal-actions span-2"><button type="button" className="button" onClick={onClose}>Cancel</button><SubmitButton busy={busy}/></div></form>
  </Modal>
}

export function SubscriptionCommandDialog({ subscription, mode, selfService = false, onClose, onDone }: DialogProps & { subscription: Subscription; mode: 'change-plan' | 'schedule-cancel' | 'cancel-now'; selfService?: boolean }) {
  const { plans } = useAppData()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const prices = plans.flatMap(plan => plan.prices.filter(price => plan.status === 'active' && price.status === 'active' && price.id !== subscription.plan_price_id).map(price => ({ plan, price })))
  const title = mode === 'change-plan' ? 'Schedule plan change' : mode === 'cancel-now' ? 'Cancel subscription now' : 'Schedule cancellation'
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const prefix = selfService ? `/me/subscriptions/${subscription.id}` : `/subscriptions/${subscription.id}`
      if (mode === 'change-plan') await api.post(`${prefix}/schedule-plan-change`, { expected_version: subscription.version, target_plan_price_id: form.get('target_price_id'), reason: form.get('reason') || null })
      else await api.post(`${prefix}/${mode === 'cancel-now' ? 'cancel-now' : 'schedule-cancellation'}`, { expected_version: subscription.version, reason: form.get('reason') || null })
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
  const paidTotal = customerPayments.reduce((sum, item) => sum + (item.status === 'completed' ? item.amount_minor - item.unallocated_minor : 0), 0)
  return <Modal title={customer.display_name} description={`${customer.customer_code} · ${customer.email ?? 'No email'}`} onClose={onClose} wide>
    <div className="detail-grid"><section><h3>Subscriptions</h3>{customerSubscriptions.length ? customerSubscriptions.map(item => <div className="detail-line" key={item.id}><span>{plans.find(plan => plan.id === item.plan_id)?.name ?? item.subscription_number}</span><Status>{item.status}</Status></div>) : <p>No subscriptions.</p>}</section><section><h3>Billing</h3><div className="detail-line"><span>Invoices</span><b>{customerInvoices.length}</b></div><div className="detail-line"><span>Paid total</span><b>{money(paidTotal)}</b></div><div className="detail-line"><span>Outstanding</span><b>{money(customerInvoices.reduce((sum, item) => sum + item.amounts.balance_minor, 0))}</b></div></section></div>
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
