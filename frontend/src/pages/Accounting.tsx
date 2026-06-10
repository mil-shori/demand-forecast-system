import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { clsx } from 'clsx'
import FreeeConnectionCard from '../components/accounting/FreeeConnectionCard'
import SalesSyncPanel from '../components/accounting/SalesSyncPanel'
import ExpensePanel from '../components/accounting/ExpensePanel'
import MonthlyReportPanel from '../components/accounting/MonthlyReportPanel'

type Tab = 'connection' | 'sales' | 'expenses' | 'reports'

const tabs: Array<{ key: Tab; label: string }> = [
  { key: 'connection', label: 'freee接続' },
  { key: 'sales', label: '売上同期' },
  { key: 'expenses', label: '経費管理' },
  { key: 'reports', label: '月次レポート' },
]

const Accounting: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<Tab>('connection')

  // OAuthコールバック後のリダイレクトを検知して結果を通知する
  useEffect(() => {
    const connected = searchParams.get('connected')
    if (connected === '1') {
      toast.success('freeeと接続しました')
      setSearchParams({}, { replace: true })
    } else if (connected === '0') {
      toast.error('freee接続に失敗しました。認可をやり直してください。')
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">経理</h2>
        <p className="mt-1 text-sm text-gray-500">
          freee会計と連携した売上仕訳・経費管理・月次レポート
        </p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={clsx(
                'whitespace-nowrap py-3 px-1 border-b-2 text-sm font-medium',
                activeTab === tab.key
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'connection' && <FreeeConnectionCard />}
      {activeTab === 'sales' && <SalesSyncPanel />}
      {activeTab === 'expenses' && <ExpensePanel />}
      {activeTab === 'reports' && <MonthlyReportPanel />}
    </div>
  )
}

export default Accounting
