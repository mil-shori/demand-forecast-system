import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { LinkIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import {
  fetchFreeeStatus,
  fetchFreeeAuthUrl,
  selectFreeeCompany,
  disconnectFreee,
} from '../../api/accounting'

const FreeeConnectionCard: React.FC = () => {
  const queryClient = useQueryClient()

  const { data: status, isLoading } = useQuery({
    queryKey: ['freeeStatus'],
    queryFn: fetchFreeeStatus,
  })

  const connectMutation = useMutation({
    mutationFn: fetchFreeeAuthUrl,
    onSuccess: (authUrl) => {
      // freeeの認可画面へ遷移（コールバック後にこの画面へ戻ってくる）
      window.location.href = authUrl
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail ?? 'freee接続の開始に失敗しました')
    },
  })

  const selectCompanyMutation = useMutation({
    mutationFn: selectFreeeCompany,
    onSuccess: () => {
      toast.success('事業所を切り替えました')
      queryClient.invalidateQueries({ queryKey: ['freeeStatus'] })
    },
    onError: () => toast.error('事業所の切り替えに失敗しました'),
  })

  const disconnectMutation = useMutation({
    mutationFn: disconnectFreee,
    onSuccess: () => {
      toast.success('freee接続を解除しました')
      queryClient.invalidateQueries({ queryKey: ['freeeStatus'] })
    },
    onError: () => toast.error('接続解除に失敗しました'),
  })

  const handleDisconnect = () => {
    if (window.confirm('freee接続を解除します。保存済みのトークンが削除されますがよろしいですか？')) {
      disconnectMutation.mutate()
    }
  }

  if (isLoading) {
    return (
      <div className="card">
        <div className="card-body text-sm text-gray-500">接続状態を確認中...</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center">
          <LinkIcon className="h-5 w-5 text-gray-600 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">freee接続</h3>
        </div>
      </div>
      <div className="card-body space-y-4">
        {!status?.configured && (
          <div className="flex items-start text-sm text-warning-700 bg-warning-50 rounded-md p-3">
            <ExclamationTriangleIcon className="h-5 w-5 mr-2 flex-shrink-0" />
            <div>
              freee連携が未設定です。backend/.env に FREEE_CLIENT_ID / FREEE_CLIENT_SECRET /
              DATA_ENCRYPTION_KEY を設定してください（backend/env.freee.example 参照）。
            </div>
          </div>
        )}

        {status?.connected ? (
          <>
            <div className="flex items-center text-sm text-success-700">
              <CheckCircleIcon className="h-5 w-5 mr-2" />
              freeeと接続済みです
            </div>
            <div>
              <label className="form-label">使用する事業所</label>
              <select
                className="form-select"
                value={status.companies.find((c) => c.is_active)?.company_id ?? ''}
                onChange={(e) => selectCompanyMutation.mutate(Number(e.target.value))}
              >
                {status.companies.map((company) => (
                  <option key={company.company_id} value={company.company_id}>
                    {company.company_name ?? `事業所 ${company.company_id}`}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={handleDisconnect}
              disabled={disconnectMutation.isPending}
            >
              接続を解除
            </button>
          </>
        ) : (
          <>
            <p className="text-sm text-gray-500">
              freeeアカウントと接続すると、売上の自動仕訳・経費同期・試算表の取得ができます。
            </p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => connectMutation.mutate()}
              disabled={!status?.configured || connectMutation.isPending}
            >
              freeeと接続
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default FreeeConnectionCard
