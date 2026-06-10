import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { CloudArrowUpIcon, TrashIcon } from '@heroicons/react/24/outline'
import {
  fetchExpenses,
  createExpense,
  deleteExpense,
  syncExpense,
  ExpenseInput,
} from '../../api/accounting'

const statusBadge: Record<string, string> = {
  synced: 'bg-success-100 text-success-800',
  draft: 'bg-gray-100 text-gray-800',
  confirmed: 'bg-primary-100 text-primary-800',
  failed: 'bg-error-100 text-error-800',
}

const paymentMethodLabels: Record<string, string> = {
  cash: '現金',
  credit_card: 'クレジットカード',
  bank_transfer: '銀行振込',
}

const emptyForm: ExpenseInput = {
  expense_date: new Date().toISOString().slice(0, 10),
  amount: 0,
  category: '',
  description: '',
  payment_method: 'cash',
  partner_name: '',
}

const ExpensePanel: React.FC = () => {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<ExpenseInput>(emptyForm)

  const { data: expenses } = useQuery({
    queryKey: ['expenses'],
    queryFn: () => fetchExpenses(),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['expenses'] })
    queryClient.invalidateQueries({ queryKey: ['journalEntries'] })
  }

  const createMutation = useMutation({
    mutationFn: createExpense,
    onSuccess: () => {
      toast.success('経費を登録しました')
      setForm(emptyForm)
      invalidate()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail ?? '経費の登録に失敗しました')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteExpense,
    onSuccess: () => {
      toast.success('経費を削除しました')
      invalidate()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail ?? '削除に失敗しました')
    },
  })

  const syncMutation = useMutation({
    mutationFn: syncExpense,
    onSuccess: () => {
      toast.success('freeeに登録しました')
      invalidate()
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail ?? 'freee同期に失敗しました')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.category || form.amount <= 0) {
      toast.error('カテゴリと正の金額を入力してください')
      return
    }
    createMutation.mutate(form)
  }

  const handleDelete = (id: number) => {
    if (window.confirm('この経費を削除しますか？')) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">経費登録</h3>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label className="form-label">日付</label>
                <input
                  type="date"
                  className="form-input"
                  value={form.expense_date}
                  onChange={(e) => setForm({ ...form, expense_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="form-label">金額（円）</label>
                <input
                  type="number"
                  className="form-input"
                  min={1}
                  value={form.amount || ''}
                  onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
                  required
                />
              </div>
              <div>
                <label className="form-label">カテゴリ</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="例: 交通費、消耗品費"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="form-label">支払方法</label>
                <select
                  className="form-select"
                  value={form.payment_method}
                  onChange={(e) => setForm({ ...form, payment_method: e.target.value })}
                >
                  <option value="cash">現金</option>
                  <option value="credit_card">クレジットカード</option>
                  <option value="bank_transfer">銀行振込</option>
                </select>
              </div>
              <div>
                <label className="form-label">取引先（任意）</label>
                <input
                  type="text"
                  className="form-input"
                  value={form.partner_name ?? ''}
                  onChange={(e) => setForm({ ...form, partner_name: e.target.value })}
                />
              </div>
              <div>
                <label className="form-label">摘要（任意）</label>
                <input
                  type="text"
                  className="form-input"
                  value={form.description ?? ''}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
              登録
            </button>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">経費一覧</h3>
        </div>
        <div className="card-body overflow-x-auto">
          {expenses && expenses.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>日付</th>
                  <th>カテゴリ</th>
                  <th className="text-right">金額</th>
                  <th>支払方法</th>
                  <th>取引先</th>
                  <th>ステータス</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((expense) => (
                  <tr key={expense.id}>
                    <td>{expense.expense_date}</td>
                    <td>
                      {expense.category}
                      {expense.description && (
                        <div className="text-xs text-gray-500">{expense.description}</div>
                      )}
                    </td>
                    <td className="text-right">¥{Number(expense.amount).toLocaleString()}</td>
                    <td>{paymentMethodLabels[expense.payment_method ?? ''] ?? expense.payment_method}</td>
                    <td>{expense.partner_name ?? '-'}</td>
                    <td>
                      <span className={`px-2 py-0.5 rounded text-xs ${statusBadge[expense.status] ?? ''}`}>
                        {expense.status}
                      </span>
                    </td>
                    <td className="space-x-2 whitespace-nowrap">
                      {expense.status !== 'synced' && (
                        <>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => syncMutation.mutate(expense.id)}
                            disabled={syncMutation.isPending}
                          >
                            <CloudArrowUpIcon className="h-4 w-4 mr-1 inline" />
                            freee同期
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDelete(expense.id)}
                            disabled={deleteMutation.isPending}
                          >
                            <TrashIcon className="h-4 w-4 inline" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-gray-500">経費はまだ登録されていません。</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default ExpensePanel
