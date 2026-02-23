import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * Format gold price in triệu/lượng (e.g., 181,600,000 → "181.600")
 * Uses thousands format: 181,600
 */
function formatGoldPrice(value) {
  if (!value && value !== 0) return '-';
  const num = parseFloat(value);
  if (isNaN(num)) return '-';
  // Gold prices from SJC are in VND (e.g., 181600000)
  // Convert to thousands: 181,600
  const inThousands = num / 1000;
  return inThousands.toLocaleString('vi-VN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

/**
 * Get display name for gold indicator
 */
function getGoldDisplayName(indicator, showRegion = false) {
  if (showRegion && indicator.attributes?.organization) {
    return indicator.attributes.organization;
  }
  // Use short Vietnamese name from attributes, fallback to name_vi, name, or id
  return indicator.name_vi || indicator.name || indicator.id;
}

/**
 * Compact table for gold prices showing Mua (Buy) and Bán (Sell) columns
 */
export default function GoldPriceTable({ 
  indicators = [], 
  compact = false, 
  showRegion = false,
  linkedIndicators = [] 
}) {
  if (indicators.length === 0) {
    return <div className="text-sm text-gray-400 py-2">No data available</div>;
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-gray-500 text-xs">
            <th className="text-left py-1.5 px-2 font-medium">
              {showRegion ? 'Khu vực' : 'Loại'}
            </th>
            <th className="text-right py-1.5 px-2 font-medium">Mua</th>
            <th className="text-right py-1.5 px-2 font-medium">Bán</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {indicators.map((indicator) => {
            const buyPrice = indicator.attributes?.buy_price || indicator.value;
            const sellPrice = indicator.attributes?.sell_price;
            const isLinked = linkedIndicators.includes(indicator.id);
            const isPrimary = indicator.attributes?.is_primary;

            return (
              <tr
                key={indicator.id}
                className={`
                  ${isLinked ? 'bg-primary-50' : 'bg-white hover:bg-gray-50'}
                  ${isPrimary && compact ? 'font-semibold' : ''}
                  transition-colors
                `}
              >
                <td className="py-1.5 px-2">
                  <div className="flex items-center gap-1">
                    {isLinked && (
                      <span className="text-primary-500 text-xs">🔗</span>
                    )}
                    <span className={`text-gray-700 ${compact ? 'text-sm' : 'text-xs'}`}>
                      {getGoldDisplayName(indicator, showRegion)}
                    </span>
                    {indicator.trend && (
                      <TrendIndicator trend={indicator.trend} />
                    )}
                  </div>
                </td>
                <td className="text-right py-1.5 px-2 tabular-nums text-gray-900">
                  {formatGoldPrice(buyPrice)}
                </td>
                <td className="text-right py-1.5 px-2 tabular-nums text-gray-900">
                  {formatGoldPrice(sellPrice)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {/* Unit note */}
      <div className="text-[10px] text-gray-400 px-2 py-1 bg-gray-50 text-right">
        Đơn vị: nghìn VND/lượng
      </div>
    </div>
  );
}

function TrendIndicator({ trend }) {
  if (trend === 'up') {
    return <TrendingUp className="w-3 h-3 text-red-500" />;
  }
  if (trend === 'down') {
    return <TrendingDown className="w-3 h-3 text-green-500" />;
  }
  return <Minus className="w-3 h-3 text-gray-400" />;
}
