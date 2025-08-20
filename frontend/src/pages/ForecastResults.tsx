import React from 'react'
import { 
  ChartBarIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import ForecastChart from '../components/ForecastChart'

const ForecastResults: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
            予測結果
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            需要予測の結果分析とダウンロード
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <button type="button" className="btn btn-primary">
            <ArrowDownTrayIcon className="h-4 w-4 mr-2" />
            結果ダウンロード
          </button>
        </div>
      </div>

      {/* フィルター・検索 */}
      <div className="card">
        <div className="card-body">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                商品検索
              </label>
              <div className="mt-1 relative">
                <input
                  type="text"
                  className="block w-full rounded-md border-gray-300 pl-10 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  placeholder="商品名・SKUで検索"
                />
                <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                カテゴリ
              </label>
              <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                <option value="">全カテゴリ</option>
                <option value="subscription">定期便</option>
                <option value="oneoff">単発商品</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                予測精度
              </label>
              <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                <option value="">全て</option>
                <option value="high">高精度 (MAPE < 10%)</option>
                <option value="medium">中精度 (MAPE < 20%)</option>
                <option value="low">要確認 (MAPE >= 20%)</option>
              </select>
            </div>
            <div className="flex items-end">
              <button type="button" className="btn btn-secondary">
                <FunnelIcon className="h-4 w-4 mr-2" />
                フィルター適用
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 予測サマリー */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-4">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ChartBarIcon className="h-8 w-8 text-primary-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">予測済み商品</p>
                <p className="text-2xl font-semibold text-gray-900">25</p>
              </div>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-success-100 rounded-full flex items-center justify-center">
                  <span className="text-success-600 font-bold text-sm">✓</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">高精度予測</p>
                <p className="text-2xl font-semibold text-success-600">18</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <ExclamationTriangleIcon className="h-8 w-8 text-warning-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">要確認</p>
                <p className="text-2xl font-semibold text-warning-600">5</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-primary-600 font-bold text-sm">%</span>
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">平均精度</p>
                <p className="text-2xl font-semibold text-gray-900">12.3%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 選択された商品の予測チャート */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center">
            <ChartBarIcon className="h-5 w-5 text-primary-600 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">
              予測チャート - オーガニック野菜セット
            </h3>
          </div>
        </div>
        <div className="card-body">
          <ForecastChart
            data={[]}
            height="400px"
            className="w-full"
          />
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="text-center">
              <p className="text-sm text-gray-500">予測モデル</p>
              <p className="text-lg font-semibold text-gray-900">AutoARIMA</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">MAPE</p>
              <p className="text-lg font-semibold text-success-600">8.2%</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">30日後予測</p>
              <p className="text-lg font-semibold text-gray-900">145個</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-500">信頼区間</p>
              <p className="text-lg font-semibold text-gray-900">±23個</p>
            </div>
          </div>
        </div>
      </div>

      {/* 予測結果一覧 */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">
            予測結果一覧
          </h3>
        </div>
        <div className="card-body">
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    商品名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    SKU
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    モデル
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    30日予測
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    60日予測
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    90日予測
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    精度
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    アクション
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr className="hover:bg-gray-50 cursor-pointer">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    オーガニック野菜セット
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    VEG-ORG-001
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    AutoARIMA
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    145 ± 23
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    298 ± 45
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    467 ± 72
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className="badge badge-success">8.2%</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button className="text-primary-600 hover:text-primary-900">
                      詳細
                    </button>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50 cursor-pointer">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    プレミアムコーヒー豆
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    COF-PRM-002
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    AutoETS
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    89 ± 15
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    184 ± 29
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    289 ± 43
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className="badge badge-success">11.7%</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button className="text-primary-600 hover:text-primary-900">
                      詳細
                    </button>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50 cursor-pointer">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ナチュラルスキンケアセット
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    SKN-NAT-003
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    Croston
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    23 ± 8
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    51 ± 16
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                    82 ± 25
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className="badge badge-warning">24.1%</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                    <button className="text-primary-600 hover:text-primary-900">
                      詳細
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4">
            <div className="flex items-center text-sm text-gray-500">
              <span>1-3 of 25 items</span>
            </div>
            <div className="flex space-x-2">
              <button className="btn btn-secondary btn-sm" disabled>
                前へ
              </button>
              <button className="btn btn-secondary btn-sm">
                次へ
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ForecastResults