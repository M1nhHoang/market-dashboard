import React from 'react';
import IndicatorCard from './IndicatorCard';

export default function IndicatorPanel({ groups, linkedIndicators = [] }) {
  if (!groups || Object.keys(groups).length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No indicators available
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {Object.entries(groups).map(([groupId, groupData]) => (
        <div key={groupId}>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            {groupData.display_name || groupId}
          </h3>
          <div className="space-y-2">
            {groupData.indicators && groupData.indicators.length > 0 ? (
              groupData.indicators.map((indicator) => (
                <IndicatorCard
                  key={indicator.id}
                  indicator={indicator}
                  linked={linkedIndicators.includes(indicator.id)}
                />
              ))
            ) : (
              <div className="text-sm text-gray-400 py-2">
                No data available
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
