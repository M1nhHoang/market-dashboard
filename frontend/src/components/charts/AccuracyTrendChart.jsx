import React from 'react';

/**
 * Simple SVG-based accuracy trend chart
 * Shows weekly accuracy over the past 4 weeks
 */
export default function AccuracyTrendChart({ data = [] }) {
  // Default mock data if none provided
  const chartData = data.length > 0 ? data : [
    { week: 'W1', accuracy: 65 },
    { week: 'W2', accuracy: 70 },
    { week: 'W3', accuracy: 75 },
    { week: 'W4', accuracy: 72 },
  ];

  const maxValue = 100;
  const minValue = 0;
  const height = 120;
  const width = 280;
  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate points
  const points = chartData.map((d, i) => {
    const x = padding.left + (i / (chartData.length - 1 || 1)) * chartWidth;
    const y = padding.top + chartHeight - (d.accuracy / maxValue) * chartHeight;
    return { x, y, ...d };
  });

  // Create path
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  // Y-axis grid lines
  const gridLines = [20, 40, 60, 80];

  return (
    <div className="w-full">
      <h5 className="text-xs font-medium text-gray-500 uppercase mb-3">📊 Accuracy Trend (Last 30 days)</h5>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
        {/* Grid lines */}
        {gridLines.map(val => {
          const y = padding.top + chartHeight - (val / maxValue) * chartHeight;
          return (
            <g key={val}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#e5e7eb"
                strokeDasharray="2,2"
              />
              <text
                x={padding.left - 8}
                y={y + 4}
                textAnchor="end"
                className="text-[10px] fill-gray-400"
              >
                {val}%
              </text>
            </g>
          );
        })}

        {/* X-axis labels */}
        {points.map((p, i) => (
          <text
            key={i}
            x={p.x}
            y={height - 8}
            textAnchor="middle"
            className="text-[10px] fill-gray-500"
          >
            {p.week}
          </text>
        ))}

        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke="#6366f1"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r="4"
              fill="#6366f1"
              stroke="white"
              strokeWidth="2"
            />
            {/* Value label */}
            <text
              x={p.x}
              y={p.y - 10}
              textAnchor="middle"
              className="text-[10px] fill-gray-600 font-medium"
            >
              {p.accuracy}%
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
