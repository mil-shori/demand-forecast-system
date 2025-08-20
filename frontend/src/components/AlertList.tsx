import React from 'react'
import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'
import { clsx } from 'clsx'

interface Alert {
  id: string
  type: 'warning' | 'error' | 'info' | 'success'
  title: string
  message: string
  timestamp: string
  sku?: string
}

interface AlertListProps {
  alerts: Alert[]
  className?: string
}

const AlertList: React.FC<AlertListProps> = ({ alerts, className }) => {
  const getAlertIcon = (type: Alert['type']) => {
    const iconClasses = 'h-5 w-5'
    
    switch (type) {
      case 'warning':
        return <ExclamationTriangleIcon className={`${iconClasses} text-warning-500`} />
      case 'error':
        return <XCircleIcon className={`${iconClasses} text-error-500`} />
      case 'success':
        return <CheckCircleIcon className={`${iconClasses} text-success-500`} />
      case 'info':
      default:
        return <InformationCircleIcon className={`${iconClasses} text-primary-500`} />
    }
  }

  const getAlertBgColor = (type: Alert['type']) => {
    switch (type) {
      case 'warning':
        return 'bg-warning-50 border-warning-200'
      case 'error':
        return 'bg-error-50 border-error-200'
      case 'success':
        return 'bg-success-50 border-success-200'
      case 'info':
      default:
        return 'bg-primary-50 border-primary-200'
    }
  }

  if (alerts.length === 0) {
    return (
      <div className={clsx('text-center py-6', className)}>
        <CheckCircleIcon className="mx-auto h-8 w-8 text-success-400" />
        <p className="mt-2 text-sm text-gray-500">
          現在アラートはありません
        </p>
      </div>
    )
  }

  return (
    <div className={clsx('space-y-3', className)}>
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={clsx(
            'p-4 rounded-md border',
            getAlertBgColor(alert.type)
          )}
        >
          <div className="flex">
            <div className="flex-shrink-0">
              {getAlertIcon(alert.type)}
            </div>
            <div className="ml-3 flex-1">
              <h4 className="text-sm font-medium text-gray-900">
                {alert.title}
                {alert.sku && (
                  <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                    {alert.sku}
                  </span>
                )}
              </h4>
              <p className="mt-1 text-sm text-gray-700">
                {alert.message}
              </p>
              <p className="mt-2 text-xs text-gray-500">
                {new Date(alert.timestamp).toLocaleString('ja-JP')}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default AlertList