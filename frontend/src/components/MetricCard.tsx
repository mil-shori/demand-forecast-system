import React from 'react'
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/outline'
import { clsx } from 'clsx'

interface MetricCardProps {
  title: string
  value: string
  previousValue?: string
  trend?: 'up' | 'down' | 'neutral'
  icon?: React.ComponentType<{ className?: string }>
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'gray'
  className?: string
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  previousValue,
  trend = 'neutral',
  icon: Icon,
  color = 'blue',
  className
}) => {
  const colorClasses = {
    blue: 'border-blue-200 bg-blue-50',
    green: 'border-green-200 bg-green-50',
    yellow: 'border-yellow-200 bg-yellow-50', 
    red: 'border-red-200 bg-red-50',
    gray: 'border-gray-200 bg-gray-50'
  }

  const iconColorClasses = {
    blue: 'text-blue-600',
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    red: 'text-red-600',
    gray: 'text-gray-600'
  }

  const getTrendIcon = () => {
    if (trend === 'up') {
      return <ArrowUpIcon className="h-4 w-4 text-green-500" />
    }
    if (trend === 'down') {
      return <ArrowDownIcon className="h-4 w-4 text-red-500" />
    }
    return null
  }

  const getTrendColor = () => {
    if (trend === 'up') return 'text-green-600'
    if (trend === 'down') return 'text-red-600'
    return 'text-gray-500'
  }

  return (
    <div className={clsx(
      'card border-2',
      colorClasses[color],
      className
    )}>
      <div className="card-body">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            {Icon && (
              <Icon className={clsx(
                'h-8 w-8',
                iconColorClasses[color]
              )} />
            )}
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">
                {title}
              </dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">
                  {value}
                </div>
                {previousValue && (
                  <div className="ml-2 flex items-baseline text-sm">
                    {getTrendIcon()}
                    <span className={clsx('ml-1', getTrendColor())}>
                      前回: {previousValue}
                    </span>
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MetricCard