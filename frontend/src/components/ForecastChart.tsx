import React from 'react'

interface ForecastChartProps {
  data: Array<{
    date: string
    value: number
    upper?: number
    lower?: number
    sku?: string
  }>
  height?: number
  className?: string
}

const ForecastChart: React.FC<ForecastChartProps> = ({
  data,
  height = 300,
  className
}) => {
  return (
    <div className={`chart-container ${className || ''}`} style={{ height }}>
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <div className="text-center">
          <div className="text-gray-400 mb-2">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          <p className="text-gray-500 text-sm">
            予測チャート
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Chart.jsライブラリを使用してここに表示されます
          </p>
        </div>
      </div>
    </div>
  )
}

export default ForecastChart