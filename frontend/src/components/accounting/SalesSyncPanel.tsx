import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ArrowPathIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline'
import {
  syncSales,
  fetchJournalEntries,
  retryJournalEntry,
  SalesSyncResult,
  getApiErrorMessage,
} from '../../api/accounting'

const statusBadge: Record<string, string> = {
  synced: 'bg-success-100 text-success-800',
  pending: 'bg-gray-100 text-gray-800',
  failed: 'bg-error-100 text-error-800',
  skipped: 'bg-gray-100 text-gray-500',
}

const firstDayOfMonth = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`
}

const today = () => new Date().toISOString().slice(0, 10)

const SalesSyncPanel: React.FC = () => {
  const queryClient = useQueryClient()
  const [startDate, setStartDate] = useState(firstDayOfMonth())
  const [endDate, setEndDate] = useState(today())
  const [granularity, setGranularity] = useState<'daily' | 'monthly'>('daily')
  const [preview, setPreview] = useState<SalesSyncResult | null>(null)

  const { data: entries } = useQuery({
    queryKey: ['journalEntries'],
    queryFn: () => fetchJournalEntries(),
  })

  const syncMutation = useMutation({
    mutationFn: syncSales,
    onSuccess: (result) => {
      if (result.dry_run) {
        setPreview(result)
        toast.success(`プレビュー: ${result.total}件の仕訳候補`)
      } else {
        setPreview(null)
        toast.success(
          `同期完了: 登録${result.synced ?? 0}件 / スキップ${result.skipped ?? 0}件 / 失敗${result.failed ?? 0}件`
        )
        queryClient.invalidateQueries({ queryKey: ['journalEntries'] })
      }
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, '売上同期に失敗しました'))
    },
  })

  const retryMutation = useMutation({
    mutationFn: retryJournalEntry,
    onSuccess: () => {
      toast.success('再送に成功しました')
      queryClient.invalidateQueries({ queryKey: ['journalEntries'] })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, '再送に失敗しました'))
    },
  })

  const runSync = (dryRun: boolean) => {
    syncMutation.mutate({
      start_date: startDate,
      end_date: endDate,
      granularity,
      dry_run: dryRun,
    })
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">売上→freee同期</h3>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="form-label">開始日</label>
              <input
                type="date"
                className="form-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div>
              <label className="form-label">終了日</label>
              <input
                type="date"
                className="form-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div>
              <label className="form-label">集計単位</label>
              <select
                className="form-select"
                value={granularity}
                onChange={(e) => setGranularity(e.target.value as 'daily' | 'monthly')}
              >
                <option value="daily">日次</option>
                <option value="monthly">月次</option>
              </select>
            </div>
          </div>
          <div className="flex space-x-3">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => runSync(true)}
              disabled={syncMutation.isPending}
            >
              プレビュー（dry run）
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => runSync(false)}
              disabled={syncMutation.isPending || !preview}
              title={!preview ? '先にプレビューで内容を確認してください' : ''}
            >
              <CloudArrowUpIcon className="h-5 w-5 mr-1 inline" />
              freeeに登録
            </button>
          </div>

          {preview?.entries && (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr>
                    <th>日付</th>
                    <th>摘要</th>
                    <th className="text-right">金額</th>
                    <th>勘定科目</th>
                    <th>状態</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.entries.map((entry) => (
                    <tr key={entry.source_key}>
                      <td>{entry.entry_date}</td>
                      <td>{entry.description}</td>
                      <td className="text-right">¥{entry.amount.toLocaleString()}</td>
                      <td>{entry.account_item_name}</td>
                      <td>
                        {entry.already_synced ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">
                            登録済み（スキップ）
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-xs bg-primary-100 text-primary-800">
                            登録対象
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">仕訳一覧</h3>
        </div>
        <div className="card-body overflow-x-auto">
          {entries && entries.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>日付</th>
                  <th>種別</th>
                  <th>摘要</th>
                  <th className="text-right">金額</th>
                  <th>ステータス</th>
                  <th>freee取引ID</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{entry.entry_date}</td>
                    <td>{entry.entry_type === 'sales' ? '売上' : '経費'}</td>
                    <td>
                      {entry.description}
                      {entry.error_message && (
                        <div className="text-xs text-error-600 mt-1">{entry.error_message}</div>
                      )}
                    </td>
                    <td className="text-right">¥{Number(entry.amount).toLocaleString()}</td>
                    <td>
                      <span className={`px-2 py-0.5 rounded text-xs ${statusBadge[entry.status] ?? ''}`}>
                        {entry.status}
                      </span>
                    </td>
                    <td>{entry.freee_deal_id ?? '-'}</td>
                    <td>
                      {entry.status === 'failed' && (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => retryMutation.mutate(entry.id)}
                          disabled={retryMutation.isPending}
                        >
                          <ArrowPathIcon className="h-4 w-4 mr-1 inline" />
                          再送
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-gray-500">仕訳はまだありません。売上同期を実行してください。</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default SalesSyncPanel
