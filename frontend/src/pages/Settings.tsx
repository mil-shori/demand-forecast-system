import React from 'react'
import { 
  CogIcon,
  UserIcon,
  BellIcon,
  ShieldCheckIcon,
  CircleStackIcon,
  ClockIcon
} from '@heroicons/react/24/outline'

const Settings: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div>
        <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl">
          設定
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          システムの設定とユーザー環境設定
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* メインコンテンツ */}
        <div className="lg:col-span-2 space-y-6">
          {/* ユーザー設定 */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center">
                <UserIcon className="h-5 w-5 text-gray-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">
                  ユーザー設定
                </h3>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      表示名
                    </label>
                    <input
                      type="text"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                      defaultValue="田中太郎"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      メールアドレス
                    </label>
                    <input
                      type="email"
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                      defaultValue="tanaka@example.com"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    タイムゾーン
                  </label>
                  <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                    <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* 予測設定 */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center">
                <CogIcon className="h-5 w-5 text-primary-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">
                  予測設定
                </h3>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      デフォルト予測期間
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
                      デフォルト信頼区間
                    </label>
                    <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                      <option value="80">80%</option>
                      <option value="90">90%</option>
                      <option value="95" selected>95%</option>
                      <option value="99">99%</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      defaultChecked
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      季節性を自動検出
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      defaultChecked
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      外れ値を自動除外
                    </span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      予測実行時にメール通知
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* データ設定 */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center">
                <CircleStackIcon className="h-5 w-5 text-blue-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">
                  データ設定
                </h3>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    データ保持期間
                  </label>
                  <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500">
                    <option value="365">1年</option>
                    <option value="730" selected>2年</option>
                    <option value="1095">3年</option>
                    <option value="1825">5年</option>
                  </select>
                  <p className="mt-1 text-sm text-gray-500">
                    古いデータは自動的に削除されます
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    CSVエクスポート形式
                  </label>
                  <div className="mt-2 space-y-2">
                    <label className="inline-flex items-center">
                      <input 
                        type="radio" 
                        name="export_format" 
                        value="utf8" 
                        className="form-radio text-primary-600" 
                        defaultChecked 
                      />
                      <span className="ml-2 text-sm text-gray-700">UTF-8</span>
                    </label>
                    <label className="inline-flex items-center">
                      <input 
                        type="radio" 
                        name="export_format" 
                        value="sjis" 
                        className="form-radio text-primary-600" 
                      />
                      <span className="ml-2 text-sm text-gray-700">Shift-JIS (Excel互換)</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      defaultChecked
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      データ取り込み時に自動バックアップ
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* サイドバー */}
        <div className="space-y-6">
          {/* 通知設定 */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center">
                <BellIcon className="h-5 w-5 text-yellow-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">
                  通知設定
                </h3>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-3">
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      defaultChecked
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      予測完了通知
                    </span>
                  </label>
                </div>
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      defaultChecked
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      エラー通知
                    </span>
                  </label>
                </div>
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      週次レポート
                    </span>
                  </label>
                </div>
                <div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      月次レポート
                    </span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* セキュリティ */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center">
                <ShieldCheckIcon className="h-5 w-5 text-green-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">
                  セキュリティ
                </h3>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-3">
                <div>
                  <button type="button" className="btn btn-secondary btn-sm w-full">
                    パスワード変更
                  </button>
                </div>
                <div>
                  <button type="button" className="btn btn-secondary btn-sm w-full">
                    ログアウト
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* システム情報 */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center">
                <ClockIcon className="h-5 w-5 text-gray-600 mr-2" />
                <h3 className="text-lg font-medium text-gray-900">
                  システム情報
                </h3>
              </div>
            </div>
            <div className="card-body">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">バージョン:</span>
                  <span className="text-gray-900">v1.0.0</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">最終更新:</span>
                  <span className="text-gray-900">2024/01/07</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">DB更新:</span>
                  <span className="text-gray-900">2024/01/07 10:30</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 保存ボタン */}
      <div className="flex justify-end space-x-3">
        <button type="button" className="btn btn-secondary">
          キャンセル
        </button>
        <button type="button" className="btn btn-primary">
          設定を保存
        </button>
      </div>
    </div>
  )
}

export default Settings