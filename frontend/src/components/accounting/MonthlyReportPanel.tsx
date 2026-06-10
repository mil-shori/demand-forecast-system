import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { DocumentArrowDownIcon } from '@heroicons/react/24/outline'
import { downloadMonthlyReport, fetchTrialBalance, fetchFreeeStatus } from '../../api/accounting'

const MonthlyReportPanel: React.FC = () => {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [trialType, setTrialType] = useState<'pl' | 'bs'>('pl')

  const { data: freeeStatus } = useQuery({
    queryKey: ['freeeStatus'],
    queryFn: fetchFreeeStatus,
  })

  const downloadMutation = useMutation({
    mutationFn: ({ format }: { format: 'xlsx' | 'csv' }) =>
      downloadMonthlyReport(year, month, format),
    onSuccess: () => toast.success('レポートをダウンロードしました'),
    onError: () => toast.error('レポートのダウンロードに失敗しました'),
  })

  const {
    data: trialBalance,
    refetch: refetchTrialBalance,
    isFetching: trialLoading,
  } = useQuery({
    queryKey: ['trialBalance', year, month, trialType],
    queryFn: () => fetchTrialBalance(year, month, trialType),
    enabled: false,
  })

  const balances = (trialBalance?.trial_balance?.balances ?? []) as Array<{
    account_item_name?: string
    account_category_name?: string
    closing_balance?: number
  }>

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">月次レポート</h3>
        </div>
        <div className="card-body space-y-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className="form-label">年</label>
              <input
                type="number"
                className="form-input"
                min={2000}
                max={2100}
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="form-label">月</label>
              <select
                className="form-select"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>{m}月</option>
                ))}
              </select>
            </div>
          </div>
          <p className="text-sm text-gray-500">
            Excel版には「売上集計」「経費一覧」「freee試算表（接続時のみ）」「同期状況」の4シートが含まれます。
          </p>
          <div className="flex space-x-3">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => downloadMutation.mutate({ format: 'xlsx' })}
              disabled={downloadMutation.isPending}
            >
              <DocumentArrowDownIcon className="h-5 w-5 mr-1 inline" />
              Excelダウンロード
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => downloadMutation.mutate({ format: 'csv' })}
              disabled={downloadMutation.isPending}
            >
              CSVダウンロード
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">freee試算表</h3>
        </div>
        <div className="card-body space-y-4">
          {freeeStatus?.connected ? (
            <>
              <div className="flex items-end space-x-3">
                <div>
                  <label className="form-label">種類</label>
                  <select
                    className="form-select"
                    value={trialType}
                    onChange={(e) => setTrialType(e.target.value as 'pl' | 'bs')}
                  >
                    <option value="pl">損益計算書（PL）</option>
                    <option value="bs">貸借対照表（BS）</option>
                  </select>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => refetchTrialBalance()}
                  disabled={trialLoading}
                >
                  {trialLoading ? '取得中...' : '試算表を取得'}
                </button>
              </div>
              {balances.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>勘定科目</th>
                        <th className="text-right">残高</th>
                      </tr>
                    </thead>
                    <tbody>
                      {balances.map((balance, index) => (
                        <tr key={index}>
                          <td>{balance.account_item_name ?? balance.account_category_name ?? '-'}</td>
                          <td className="text-right">
                            ¥{Number(balance.closing_balance ?? 0).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-500">
              試算表を表示するにはfreeeと接続してください。
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default MonthlyReportPanel
