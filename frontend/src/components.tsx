import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight, Download, Ellipsis, LoaderCircle, Search, X } from 'lucide-react'

export function money(minor = 0, currency = 'PHP') {
  return new Intl.NumberFormat('en-PH', { style: 'currency', currency }).format(minor / 100)
}

export function shortDate(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-PH', { month: 'short', day: 'numeric', year: 'numeric' }).format(date)
}

export function initials(name = '') {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]?.toUpperCase()).join('') || '—'
}

export function Status({ children }: { children: string }) {
  return <span className={`badge ${children.toLowerCase().replaceAll('_', '-').replaceAll(' ', '-')}`}>{children.replaceAll('_', ' ')}</span>
}

export function Metric({ icon, label, value, note, tone = 'blue' }: { icon: React.ReactNode; label: string; value: string; note?: string; tone?: string }) {
  return <article className="metric-card"><span className={`metric-icon ${tone}`}>{icon}</span><div><p>{label}</p><strong>{value}</strong>{note && <small>{note}</small>}</div></article>
}

export function LoadingState({ label = 'Loading data' }: { label?: string }) {
  return <div className="state-panel"><LoaderCircle className="spin"/><p>{label}…</p></div>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="state-panel error-state" role="alert"><AlertCircle/><p>{message}</p>{onRetry && <button className="button" onClick={onRetry}>Try again</button>}</div>
}

export function EmptyState({ title, copy }: { title: string; copy: string }) {
  return <div className="empty-state"><p>{title}</p><span>{copy}</span></div>
}

export function Toast({ message, error = false, onClose }: { message: string; error?: boolean; onClose: () => void }) {
  useEffect(() => {
    const timer = window.setTimeout(onClose, 4000)
    return () => window.clearTimeout(timer)
  }, [onClose])
  return <div className={`toast ${error ? 'toast-error' : ''}`} role={error ? 'alert' : 'status'}><span>{error ? <AlertCircle size={19}/> : <CheckCircle2 size={19}/>}</span><p>{message}</p><button type="button" onClick={onClose} aria-label="Dismiss notification"><X size={17}/></button></div>
}

export function Modal({ title, description, children, onClose, wide = false }: { title: string; description?: string; children: React.ReactNode; onClose: () => void; wide?: boolean }) {
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    panel.current?.focus()
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])
  return <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={panel} className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabIndex={-1}>
      <button type="button" className="modal-close" onClick={onClose} aria-label="Close dialog"><X size={18}/></button>
      <h2 id="modal-title">{title}</h2>
      {description && <p className="modal-copy">{description}</p>}
      {children}
    </section>
  </div>
}

export function ConfirmDialog({ title, message, confirmLabel, danger = false, busy = false, onCancel, onConfirm }: { title: string; message: string; confirmLabel: string; danger?: boolean; busy?: boolean; onCancel: () => void; onConfirm: () => void }) {
  return <Modal title={title} description={message} onClose={onCancel}><div className="modal-actions"><button type="button" className="button" onClick={onCancel}>Cancel</button><button type="button" className={`button ${danger ? 'danger' : 'primary'}`} disabled={busy} onClick={onConfirm}>{busy ? <><LoaderCircle className="spin" size={16}/> Working</> : confirmLabel}</button></div></Modal>
}

export type Column<T> = { key: string; label: string; render: (row: T) => React.ReactNode }

export function DataTable<T>({ rows, columns, rowKey, searchPlaceholder, searchText, statusOf, statuses = [], planOf, planOptions = [], pageSize = 10, actions, onRowClick }: {
  rows: T[]
  columns: Column<T>[]
  rowKey: (row: T) => string
  searchPlaceholder: string
  searchText: (row: T) => string
  statusOf?: (row: T) => string
  statuses?: string[]
  planOf?: (row: T) => string
  planOptions?: string[]
  pageSize?: number
  actions?: (row: T) => Array<{ label: string; danger?: boolean; disabled?: boolean; onClick: () => void }>
  onRowClick?: (row: T) => void
}) {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [plan, setPlan] = useState('all')
  const [page, setPage] = useState(1)
  const filtered = useMemo(() => rows.filter(row => {
    const queryMatch = !query || searchText(row).toLowerCase().includes(query.toLowerCase())
    const statusMatch = status === 'all' || statusOf?.(row) === status
    const planMatch = plan === 'all' || planOf?.(row) === plan
    return queryMatch && statusMatch && planMatch
  }), [rows, query, status, plan, searchText, statusOf, planOf])
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  useEffect(() => setPage(1), [query, status, plan, rows.length])
  useEffect(() => { if (page > totalPages) setPage(totalPages) }, [page, totalPages])
  const pageRows = filtered.slice((page - 1) * pageSize, page * pageSize)
  const start = filtered.length ? (page - 1) * pageSize + 1 : 0
  const end = Math.min(page * pageSize, filtered.length)
  return <>
    <div className="filters">
      <label className="search"><Search size={18}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder={searchPlaceholder} aria-label={searchPlaceholder}/>{query && <button type="button" className="clear-search" onClick={() => setQuery('')} aria-label="Clear search"><X size={14}/></button>}</label>
      {statusOf && <label className="filter-select"><span>Status</span><select value={status} onChange={event => setStatus(event.target.value)} aria-label="Filter by status"><option value="all">All statuses</option>{statuses.map(item => <option key={item} value={item}>{item.replaceAll('_', ' ')}</option>)}</select></label>}
      {planOf && <label className="filter-select"><span>Plan</span><select value={plan} onChange={event => setPlan(event.target.value)} aria-label="Filter by plan"><option value="all">All plans</option>{planOptions.map(item => <option key={item} value={item}>{item}</option>)}</select></label>}
    </div>
    <div className="table-scroll"><table><thead><tr>{columns.map(column => <th key={column.key}>{column.label}</th>)}{actions && <th>Actions</th>}</tr></thead><tbody>
      {pageRows.map(row => <tr key={rowKey(row)} className={onRowClick ? 'clickable-row' : ''} onClick={() => onRowClick?.(row)}>{columns.map(column => <td key={column.key}>{column.render(row)}</td>)}{actions && <td onClick={event => event.stopPropagation()}><RowActions label={searchText(row)} actions={actions(row)}/></td>}</tr>)}
      {!pageRows.length && <tr><td colSpan={columns.length + (actions ? 1 : 0)}><EmptyState title="No matching records" copy="Try changing the search or filters."/></td></tr>}
    </tbody></table></div>
    <div className="pager"><span>Showing {start} to {end} of {filtered.length}</span><div><button type="button" disabled={page === 1} onClick={() => setPage(value => value - 1)} aria-label="Previous page"><ChevronLeft size={16}/></button><span>Page {page} of {totalPages}</span><button type="button" disabled={page === totalPages} onClick={() => setPage(value => value + 1)} aria-label="Next page"><ChevronRight size={16}/></button></div></div>
  </>
}

export function RowActions({ label, actions }: { label: string; actions: Array<{ label: string; danger?: boolean; disabled?: boolean; onClick: () => void }> }) {
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [])
  return <div className="row-actions"><button type="button" className="icon-button" aria-label={`Actions for ${label}`} aria-expanded={open} onClick={() => setOpen(value => !value)}><Ellipsis size={18}/></button>{open && <div className="action-menu" role="menu">{actions.map(action => <button type="button" role="menuitem" className={action.danger ? 'danger-text' : ''} disabled={action.disabled} key={action.label} onClick={() => { setOpen(false); action.onClick() }}>{action.label}</button>)}</div>}</div>
}

export function Toggle({ label, checked, disabled = false, onChange }: { label: string; checked: boolean; disabled?: boolean; onChange: (checked: boolean) => void }) {
  return <label className="toggle-row"><span>{label}</span><button type="button" className={checked ? 'toggle on' : 'toggle'} role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)}><b/></button></label>
}

export function downloadCsv(fileName: string, rows: Array<Array<string | number>>) {
  const csv = rows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
  URL.revokeObjectURL(url)
}

export function ExportButton({ onClick, label = 'Export CSV' }: { onClick: () => void; label?: string }) {
  return <button type="button" className="button" onClick={onClick}><Download size={16}/>{label}</button>
}
