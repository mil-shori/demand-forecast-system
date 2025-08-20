import React from 'react'
import { 
  PlayCircleIcon, 
  ClockIcon, 
  ChartBarIcon, 
  CogIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'

const ForecastExecution: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div>
        <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
          予測実行
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          需要予測モデルの実行と管理
        </p>
      </div>

      {/* 予測実行コントロール */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <PlayCircleIcon className="h-5 w-5 text-primary-600 mr-2" />
                  <h3 className="text-lg font-medium text-gray-900">
                    予測実行設定
                  </h3>
                </div>
                <button className="btn btn-primary">
                  <PlayCircleIcon className="h-4 w-4 mr-2" />
                  予測開始
                </button>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      予測期間
                    </label>
                    <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                      <option value="30">30日</option>
                      <option value="60">60日</option>
                      <option value="90" selected>90日</option>
                      <option value="180">180日</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      予測モデル
                    </label>
                    <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                      <option value="auto">自動選択</option>
                      <option value="arima">AutoARIMA</option>
                      <option value="ets">AutoETS</option>
                      <option value="croston">Croston</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    対象商品
                  </label>
                  <div className="mt-2 space-y-2">
                    <label className="inline-flex items-center">
                      <input 
                        type="radio" 
                        name="target" 
                        value="all" 
                        className="form-radio text-primary-600" 
                        defaultChecked 
                      />
                      <span className="ml-2 text-sm text-gray-700">全商品</span>
                    </label>
                    <label className="inline-flex items-center">
                      <input 
                        type="radio" 
                        name="target" 
                        value="category" 
                        className="form-radio text-primary-600" 
                      />
                      <span className="ml-2 text-sm text-gray-700">カテゴリ別</span>
                    </label>
                    <label className="inline-flex items-center">
                      <input 
                        type="radio" 
                        name="target" 
                        value="selected" 
                        className="form-radio text-primary-600" 
                      />
                      <span className="ml-2 text-sm text-gray-700">選択商品のみ</span>
                    </label>
                  </div>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                  <div className="flex">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-yellow-800">
                        予測実行の注意事項
                      </h3>
                      <div className="mt-2 text-sm text-yellow-700">
                        <ul className="list-disc list-inside space-y-1">
                          <li>全商品の予測には約5-10分かかります</li>
                          <li>実行中は他の予測を開始できません</li>
                          <li>最新のデータが使用されます</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 実行状況 */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <ChartBarIcon className="h-5 w-5 text-success-600 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">
                実行状況
              </h3>
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="text-center">
                <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-success-100 text-success-800">
                  待機中
                </div>
              </div>
              
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">進捗</span>
                  <span className="font-medium text-gray-900">0 / 25 商品</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className="bg-primary-600 h-2 rounded-full" style={{ width: '0%' }}></div>
                </div>
              </div>

              <div className="border-t border-gray-200 pt-3 space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">最終実行</span>
                  <span className="text-gray-900">2024/01/07 14:30</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">実行時間</span>
                  <span className="text-gray-900">6分32秒</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-600">成功率</span>
                  <span className="text-success-600 font-medium">100%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 最近の実行履歴 */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <ClockIcon className="h-5 w-5 text-gray-600 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">
                実行履歴
              </h3>
            </div>
            <button className="btn btn-secondary btn-sm">
              <CogIcon className="h-4 w-4 mr-2" />
              設定
            </button>
          </div>
        </div>
        <div className="card-body">
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    実行日時
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    対象
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    モデル
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    期間
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    実行時間
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ステータス
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    2024/01/07 14:30
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    全商品 (25件)
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    自動選択
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    90日
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    6分32秒
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="badge badge-success">完了</span>
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    2024/01/06 09:15
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    定期便商品 (15件)
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    AutoARIMA
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    60日
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    4分18秒
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="badge badge-success">完了</span>
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    2024/01/05 16:45
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    全商品 (25件)
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    自動選択
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    90日
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    7分05秒
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="badge badge-warning">警告あり</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ForecastExecution