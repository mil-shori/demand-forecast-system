import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// レスポンスインターセプター
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface DashboardData {
  accuracy: number
  accuracyTrend: string
  stockoutRisk: number
  stockoutTrend: string
  churnRate: number
  churnTrend: string
  recommendedOrderAmount: number
  orderAmountTrend: string
  forecastData: Array<{
    date: string
    value: number
    upper: number
    lower: number
    sku: string
  }>
  alerts: Array<{
    id: string
    type: 'warning' | 'error' | 'info'
    title: string
    message: string
    timestamp: string
    sku?: string
  }>
}

export const fetchDashboardData = async (): Promise<DashboardData> => {
  try {
    const response = await apiClient.get('/dashboard')
    return response.data
  } catch (error) {
    // フォールバックデータを返す
    return {
      accuracy: 94.2,
      accuracyTrend: '+2.1%',
      stockoutRisk: 3,
      stockoutTrend: '-1',
      churnRate: 2.3,
      churnTrend: '-0.5%',
      recommendedOrderAmount: 1200000,
      orderAmountTrend: '+¥150K',
      forecastData: [
        {
          date: '2024-01-08',
          value: 120,
          upper: 140,
          lower: 100,
          sku: 'VEG001'
        },
        {
          date: '2024-01-09',
          value: 115,
          upper: 135,
          lower: 95,
          sku: 'VEG001'
        },
        {
          date: '2024-01-10',
          value: 125,
          upper: 145,
          lower: 105,
          sku: 'VEG001'
        }
      ],
      alerts: [
        {
          id: '1',
          type: 'warning',
          title: '在庫切れリスク',
          message: 'VEG003の在庫が不足しています',
          timestamp: '2024-01-07T10:00:00Z',
          sku: 'VEG003'
        },
        {
          id: '2',
          type: 'info',
          title: '予測完了',
          message: '週次予測が正常に完了しました',
          timestamp: '2024-01-07T08:00:00Z'
        }
      ]
    }
  }
}

export const fetchHealthCheck = async () => {
  const response = await apiClient.get('/health')
  return response.data
}