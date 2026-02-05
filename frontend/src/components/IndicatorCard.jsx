import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatNumber, formatChange, getTrendIcon } from '../utils/format';

export default function IndicatorCard({ indicator, linked = false }) {
  const { id, name, name_vi, value, unit, change, change_pct, trend, updated_at } = indicator;

  const getTrendColor = () => {
    // For most indicators, up = bad (red), down = good (green)
    // Exception: credit_growth, gdp where up = good
    const inverseIndicators = ['credit_growth', 'gdp', 'export'];
    const isInverse = inverseIndicators.some(i => id?.includes(i));

    if (trend === 'up') return isInverse ? 'text-green-600' : 'text-red-600';
    if (trend === 'down') return isInverse ? 'text-red-600' : 'text-green-600';
    return 'text-gray-500';
  };

  const getTrendBgColor = () => {
    if (trend === 'up') return 'bg-red-50';
    if (trend === 'down') return 'bg-green-50';
    return 'bg-gray-50';
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <div
      className={`p-3 rounded-lg border transition-all ${
        linked
          ? 'border-primary-300 bg-primary-50 ring-2 ring-primary-200'
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <div className="text-xs text-gray-500 font-medium uppercase tracking-wide">
          {name_vi || name || id}
        </div>
        {linked && (
          <span className="text-xs bg-primary-100 text-primary-700 px-1.5 py-0.5 rounded">
            🔗 Linked
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold text-gray-900">
          {formatNumber(value)}
        </span>
        {unit && (
          <span className="text-sm text-gray-500">{unit}</span>
        )}
      </div>

      {(change !== null && change !== undefined) && (
        <div className={`flex items-center gap-1 mt-1 text-sm ${getTrendColor()}`}>
          <TrendIcon className="w-3.5 h-3.5" />
          <span>{formatChange(change, unit)}</span>
          {change_pct !== null && change_pct !== undefined && (
            <span className="text-gray-400">
              ({change_pct > 0 ? '+' : ''}{change_pct?.toFixed(2)}%)
            </span>
          )}
        </div>
      )}
    </div>
  );
}
