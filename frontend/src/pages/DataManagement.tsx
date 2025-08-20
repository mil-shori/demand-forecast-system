import React from 'react'
import { DocumentArrowUpIcon, TableCellsIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

const DataManagement: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div>
        <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
          データ管理
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          CSV/Excelファイルの取り込みとデータ品質管理
        </p>
      </div>

      {/* データ取り込みセクション */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <DocumentArrowUpIcon className="h-5 w-5 text-primary-600 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">
                データ取り込み
              </h3>
            </div>
          </div>
          <div className="card-body">
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
              <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4">
                <p className="text-sm text-gray-600">
                  CSVまたはExcelファイルをドラッグ&ドロップ
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  対応形式: .csv, .xlsx (最大10MB)
                </p>
              </div>
              <div className="mt-4">
                <button type="button" className="btn btn-primary">
                  ファイルを選択
                </button>
              </div>
            </div>
            
            <div className="mt-4 space-y-2">
              <div className="text-sm font-medium text-gray-700">サンプルテンプレート:</div>
              <div className="space-y-1">
                <button className="text-sm text-primary-600 hover:text-primary-800">
                  📄 orders.csv - 注文データ
                </button>
                <button className="text-sm text-primary-600 hover:text-primary-800">
                  📄 products.csv - 商品マスタ
                </button>
                <button className="text-sm text-primary-600 hover:text-primary-800">
                  📄 subscriptions.csv - 定期便データ
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* データ品質チェック */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <CheckCircleIcon className="h-5 w-5 text-success-600 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">
                データ品質レポート
              </h3>
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-sm text-gray-600">総レコード数</span>
                <span className="text-sm font-medium text-gray-900">1,247</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-sm text-gray-600">有効レコード数</span>
                <span className="text-sm font-medium text-success-600">1,245</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-gray-200">
                <span className="text-sm text-gray-600">エラーレコード数</span>
                <span className="text-sm font-medium text-error-600">2</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-sm text-gray-600">データ品質スコア</span>
                <span className="text-sm font-medium text-success-600">99.8%</span>
              </div>
            </div>
            
            <div className="mt-4">
              <button className="btn btn-secondary btn-sm">
                詳細レポートを表示
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 最近の取り込み履歴 */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center">
            <TableCellsIcon className="h-5 w-5 text-gray-600 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">
              最近の取り込み履歴
            </h3>
          </div>
        </div>
        <div className="card-body">
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ファイル名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    種類
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    レコード数
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    取り込み日時
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ステータス
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    orders_20240107.csv
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    注文データ
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    1,247
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2024/01/07 10:30
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="badge badge-success">完了</span>
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    products_20240107.csv
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    商品マスタ
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    25
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    2024/01/07 09:15
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="badge badge-success">完了</span>
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

export default DataManagement