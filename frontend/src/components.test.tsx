import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DataTable, downloadCsv, Modal } from './components'

afterEach(cleanup)

const rows = [
  { id: '1', name: 'Alpha', status: 'active', plan: 'Basic' },
  { id: '2', name: 'Beta', status: 'archived', plan: 'Premium' },
  { id: '3', name: 'Gamma', status: 'active', plan: 'Premium' },
]

describe('DataTable', () => {
  it('combines search and plan filters and clears search', () => {
    render(<DataTable rows={rows} rowKey={row => row.id} searchPlaceholder="Search customers" searchText={row => row.name} statusOf={row => row.status} statuses={['active', 'archived']} planOf={row => row.plan} planOptions={['Basic', 'Premium']} columns={[{ key: 'name', label: 'Name', render: row => row.name }]} />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Search customers' }), { target: { value: 'a' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by plan' }), { target: { value: 'Premium' } })

    expect(screen.queryByText('Alpha')).not.toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
    expect(screen.getByText('Gamma')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(screen.getByRole('textbox', { name: 'Search customers' })).toHaveValue('')
  })

  it('paginates the actual rows', () => {
    render(<DataTable rows={rows} pageSize={2} rowKey={row => row.id} searchPlaceholder="Search records" searchText={row => row.name} columns={[{ key: 'name', label: 'Name', render: row => row.name }]} />)

    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.queryByText('Gamma')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Gamma')).toBeInTheDocument()
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument()
  })
})

describe('Modal', () => {
  it('closes with Escape and backdrop clicks', () => {
    const onClose = vi.fn()
    const { container } = render(<Modal title="Test dialog" onClose={onClose}><p>Body</p></Modal>)

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
    fireEvent.mouseDown(container.querySelector('.modal-backdrop')!)
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})

describe('CSV exports', () => {
  it('creates and clicks a downloadable CSV link', () => {
    const createUrl = vi.fn(() => 'blob:csv-test')
    const revokeUrl = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createUrl })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeUrl })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)

    downloadCsv('report.csv', [['Name', 'Value'], ['Quoted "name"', 42]])

    expect(createUrl).toHaveBeenCalledOnce()
    expect(click).toHaveBeenCalledOnce()
    expect(revokeUrl).toHaveBeenCalledWith('blob:csv-test')
  })
})
