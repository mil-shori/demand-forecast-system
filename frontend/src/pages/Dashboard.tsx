import React from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  CurrencyYenIcon,
  ArrowUpIcon
} from '@heroicons/react/24/outline'
import MetricCard from '../components/MetricCard'
import ForecastChart from '../components/ForecastChart'
import AlertList from '../components/AlertList'
import { fetchDashboardData } from '../api/dashboard'

const Dashboard: React.FC = () => {
  const { data: dashboardData, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardData,
    refetchInterval: 5 * 60 * 1000, // 5分毎に更新
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner spinner-lg"></div>
        <span className="ml-2 text-gray-600">ダッシュボードを読み込み中...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="alert alert-error">
        <ExclamationTriangleIcon className="h-5 w-5" />
        <span>ダッシュボードデータの読み込みに失敗しました</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl">
            ダッシュボード
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            需要予測システムの概要とKPI
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4">
          <button
            type="button"
            className="btn btn-primary"
          >
            予測を実行
          </button>
        </div>
      </div>

      {/* KPI メトリクスカード */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="今週の予測精度"
          value="94.2%"
          previousValue="92.1%"
          trend="up"
          icon={ChartBarIcon}
          color="green"
        />
        <MetricCard
          title="在庫切れリスク"
          value="3 SKU"
          previousValue="5 SKU"
          trend="down"
          icon={ExclamationTriangleIcon}
          color="yellow"
        />
        <MetricCard
          title="定期便解約予測"
          value="2.3%"
          previousValue="2.8%"
          trend="down"
          icon={ArrowTrendingUpIcon}
          color="green"
        />
        <MetricCard
          title="推奨発注額"
          value="¥1.2M"
          previousValue="¥1.05M"
          trend="up"
          icon={CurrencyYenIcon}
          color="blue"
        />
      </div>

      {/* チャートとアラート */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 需要予測チャート */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              上位SKU需要予測（今後4週間）
            </h3>
          </div>
          <div className="card-body">
            <ForecastChart
              data={dashboardData?.forecastData || []}
              height={300}
            />
          </div>
        </div>

        {/* 在庫アラート */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              在庫アラート
            </h3>
          </div>
          <div className="card-body">
            <AlertList
              alerts={dashboardData?.alerts || []}
            />
          </div>
        </div>
      </div>

      {/* 詳細統計 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 週次サマリー */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              週次サマリー
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">総注文数</span>
                <span className="text-lg font-semibold text-gray-900">1,247</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">定期便注文</span>
                <span className="text-lg font-semibold text-gray-900">873</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">単発注文</span>
                <span className="text-lg font-semibold text-gray-900">374</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">平均注文額</span>
                <span className="text-lg font-semibold text-gray-900">¥3,250</span>
              </div>
            </div>
          </div>
        </div>

        {/* トップSKU */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              売上上位SKU
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-3">
              {[
                { sku: 'VEG001', name: '有機野菜セット', sales: '¥285K' },
                { sku: 'FRUIT001', name: '季節フルーツセット', sales: '¥198K' },
                { sku: 'MEAT001', name: '国産肉セット', sales: '¥156K' },
                { sku: 'FISH001', name: '鮮魚セット', sales: '¥124K' },
                { sku: 'DAIRY001', name: '乳製品セット', sales: '¥98K' }
              ].map((item, index) => (
                <div key={item.sku} className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 w-6 h-6 bg-primary-100 rounded-full flex items-center justify-center text-xs font-medium text-primary-600">
                      {index + 1}
                    </div>
                    <div className="ml-3">
                      <p className="text-sm font-medium text-gray-900">{item.name}</p>
                      <p className="text-xs text-gray-500">{item.sku}</p>
                    </div>
                  </div>
                  <div className="text-sm font-medium text-gray-900">
                    {item.sales}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 最近のアクティビティ */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              最近のアクティビティ
            </h3>
          </div>
          <div className="card-body">
            <div className="flow-root">
              <ul className="-mb-8">
                {[
                  {
                    type: 'forecast',
                    content: '週次予測を実行しました',
                    time: '2時間前',
                    icon: ChartBarIcon,
                    iconBg: 'bg-primary-500'
                  },
                  {
                    type: 'import',
                    content: '新しい注文データを取り込みました',
                    time: '4時間前',
                    icon: ArrowUpIcon,
                    iconBg: 'bg-success-500'
                  },
                  {
                    type: 'alert',
                    content: 'VEG003の在庫切れアラート',
                    time: '6時間前',
                    icon: ExclamationTriangleIcon,
                    iconBg: 'bg-warning-500'
                  }
                ].map((item, itemIdx) => (
                  <li key={itemIdx}>
                    <div className="relative pb-8">
                      {itemIdx !== 2 && (
                        <span
                          className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                          aria-hidden="true"
                        />
                      )}
                      <div className="relative flex space-x-3">
                        <div>
                          <span className={`h-8 w-8 rounded-full flex items-center justify-center ring-8 ring-white ${item.iconBg}`}>
                            <item.icon className="h-4 w-4 text-white" aria-hidden="true" />
                          </span>
                        </div>
                        <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                          <div>
                            <p className="text-sm text-gray-500">{item.content}</p>
                          </div>
                          <div className="text-right text-sm whitespace-nowrap text-gray-500">
                            <time>{item.time}</time>
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard