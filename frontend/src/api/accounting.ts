import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // freee API同期は時間がかかる場合がある
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Accounting API Error:', error)
    return Promise.reject(error)
  }
)

// --- 型定義 ---

export interface CompanyInfo {
  company_id: number
  company_name: string | null
  is_active: boolean
  expires_at: string | null
}

export interface FreeeStatus {
  configured: boolean
  connected: boolean
  companies: CompanyInfo[]
}

export interface Mapping {
  id: number
  mapping_type: 'sales_category' | 'expense_category'
  source_key: string
  keywords: string | null
  freee_account_item_id: number
  freee_account_item_name: string | null
  freee_tax_code: number | null
  freee_partner_id: number | null
  priority: number
  active: boolean
}

export type MappingInput = Omit<Mapping, 'id'>

export interface SalesSyncRequest {
  start_date: string
  end_date: string
  granularity: 'daily' | 'monthly'
  dry_run: boolean
}

export interface SalesSyncPreviewEntry {
  source_key: string
  entry_date: string
  description: string
  amount: number
  order_count: number
  account_item_name: string
  already_synced: boolean
  existing_status: string | null
}

export interface SalesSyncResult {
  dry_run: boolean
  total: number
  synced?: number
  skipped?: number
  failed?: number
  entries?: SalesSyncPreviewEntry[]
  results?: Array<{
    source_key: string
    entry_date: string
    description: string
    amount: number
    account_item_name: string
    status: 'synced' | 'skipped' | 'failed'
    freee_deal_id?: number
    error?: string
  }>
}

export interface JournalEntry {
  id: number
  entry_date: string
  entry_type: 'sales' | 'expense'
  source_type: string
  source_key: string
  description: string | null
  amount: number
  status: 'pending' | 'synced' | 'failed' | 'skipped'
  freee_deal_id: number | null
  error_message: string | null
  synced_at: string | null
}

export interface Expense {
  id: number
  expense_date: string
  amount: number
  category: string
  description: string | null
  payment_method: string | null
  partner_name: string | null
  status: 'draft' | 'confirmed' | 'synced' | 'failed'
  freee_deal_id: number | null
}

export interface ExpenseInput {
  expense_date: string
  amount: number
  category: string
  description?: string
  payment_method: string
  partner_name?: string
}

// --- freee接続管理 ---

export const fetchFreeeStatus = async (): Promise<FreeeStatus> => {
  const response = await apiClient.get('/accounting/freee/status')
  return response.data
}

export const fetchFreeeAuthUrl = async (): Promise<string> => {
  const response = await apiClient.get('/accounting/freee/auth-url')
  return response.data.auth_url
}

export const selectFreeeCompany = async (companyId: number): Promise<FreeeStatus> => {
  const response = await apiClient.post('/accounting/freee/company', { company_id: companyId })
  return response.data
}

export const disconnectFreee = async (): Promise<{ deleted: number }> => {
  const response = await apiClient.post('/accounting/freee/disconnect')
  return response.data
}

// --- 勘定科目マッピング ---

export const fetchMappings = async (mappingType?: string): Promise<Mapping[]> => {
  const response = await apiClient.get('/accounting/mappings', {
    params: mappingType ? { mapping_type: mappingType } : {},
  })
  return response.data
}

export const createMapping = async (input: MappingInput): Promise<Mapping> => {
  const response = await apiClient.post('/accounting/mappings', input)
  return response.data
}

export const deleteMapping = async (id: number): Promise<void> => {
  await apiClient.delete(`/accounting/mappings/${id}`)
}

// --- 売上同期 ---

export const syncSales = async (request: SalesSyncRequest): Promise<SalesSyncResult> => {
  const response = await apiClient.post('/accounting/sales/sync', request)
  return response.data
}

export const fetchJournalEntries = async (params?: {
  start_date?: string
  end_date?: string
  status?: string
}): Promise<JournalEntry[]> => {
  const response = await apiClient.get('/accounting/journal-entries', { params })
  return response.data
}

export const retryJournalEntry = async (id: number): Promise<JournalEntry> => {
  const response = await apiClient.post(`/accounting/journal-entries/${id}/retry`)
  return response.data
}

// --- 経費 ---

export const fetchExpenses = async (params?: {
  start_date?: string
  end_date?: string
  status?: string
}): Promise<Expense[]> => {
  const response = await apiClient.get('/accounting/expenses', { params })
  return response.data
}

export const createExpense = async (input: ExpenseInput): Promise<Expense> => {
  const response = await apiClient.post('/accounting/expenses', input)
  return response.data
}

export const deleteExpense = async (id: number): Promise<void> => {
  await apiClient.delete(`/accounting/expenses/${id}`)
}

export const syncExpense = async (id: number): Promise<Expense> => {
  const response = await apiClient.post(`/accounting/expenses/${id}/sync`)
  return response.data
}

// --- レポート ---

export const downloadMonthlyReport = async (
  year: number,
  month: number,
  format: 'xlsx' | 'csv'
): Promise<void> => {
  const response = await apiClient.get('/accounting/reports/monthly', {
    params: { year, month, format },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `monthly_report_${year}-${String(month).padStart(2, '0')}.${format}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export const fetchTrialBalance = async (
  year: number,
  month: number,
  type: 'pl' | 'bs'
): Promise<{ trial_balance: { balances?: Array<Record<string, unknown>> } }> => {
  const response = await apiClient.get('/accounting/reports/trial-balance', {
    params: { year, month, type },
  })
  return response.data
}
