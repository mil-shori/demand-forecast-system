import React from 'react'
import { ExclamationTriangleIcon, HomeIcon } from '@heroicons/react/24/outline'

const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <ExclamationTriangleIcon className="mx-auto h-24 w-24 text-gray-400" />
          <h1 className="mt-6 text-6xl font-bold text-gray-900">404</h1>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">
            ページが見つかりません
          </h2>
          <p className="mt-4 text-base text-gray-600">
            お探しのページは存在しないか、移動された可能性があります。
          </p>
        </div>

        <div className="mt-8">
          <div className="bg-white py-8 px-6 shadow rounded-lg sm:px-10">
            <div className="space-y-4">
              <div className="text-center">
                <p className="text-sm text-gray-600">
                  以下の方法をお試しください:
                </p>
                <ul className="mt-4 space-y-2 text-sm text-gray-600 text-left">
                  <li className="flex items-center">
                    <span className="mr-2">•</span>
                    URLが正しく入力されているか確認してください
                  </li>
                  <li className="flex items-center">
                    <span className="mr-2">•</span>
                    ブラウザの戻るボタンで前のページに戻る
                  </li>
                  <li className="flex items-center">
                    <span className="mr-2">•</span>
                    ダッシュボードから目的のページに移動する
                  </li>
                </ul>
              </div>

              <div className="mt-6">
                <button 
                  type="button" 
                  className="w-full flex justify-center items-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  onClick={() => window.history.back()}
                >
                  前のページに戻る
                </button>
              </div>

              <div className="mt-4">
                <a
                  href="/"
                  className="w-full flex justify-center items-center py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  <HomeIcon className="h-4 w-4 mr-2" />
                  ダッシュボードに戻る
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center">
          <p className="text-sm text-gray-500">
            問題が続く場合は、システム管理者にお問い合わせください。
          </p>
        </div>
      </div>
    </div>
  )
}

export default NotFound