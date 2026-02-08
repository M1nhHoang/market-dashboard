import React from 'react';
import { formatDate } from '../../utils/format';

/**
 * Simple SVG-based strength timeline chart
 * Shows theme strength over time
 */
export default function StrengthTimelineChart({ data = [], maxStrength = 10 }) {
  // Default mock data if none provided
  const chartData = data.length > 0 ? data : [
    { date: '2026-02-01', strength: 2.0 },
    { date: '2026-02-03', strength: 4.5 },
    { date: '2026-02-05', strength: 7.2 },
    { date: '2026-02-07', strength: 9.1 },
    { date: '2026-02-08', strength: 8.2 },
  ];

  const height = 100;
  const width = 300;
  const padding = { top: 20, right: 20, bottom: 25, left: 35 };
  
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Find peak
  const peakIndex = chartData.reduce((maxIdx, d, i, arr) => 
    d.strength > arr[maxIdx].strength ? i : maxIdx, 0);

  // Calculate points
  const points = chartData.map((d, i) => {
    const x = padding.left + (i / (chartData.length - 1 || 1)) * chartWidth;
    const y = padding.top + chartHeight - (d.strength / maxStrength) * chartHeight;
    return { x, y, ...d, isPeak: i === peakIndex };
  });

  // Create path
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  // Threshold line (active = 5.0)
  const thresholdY = padding.top + chartHeight - (5 / maxStrength) * chartHeight;

  return (
    <div className="w-full">
      <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">📈 Strength Timeline</h5>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
        {/* Threshold line */}
        <line
          x1={padding.left}
          y1={thresholdY}
          x2={width - padding.right}
          y2={thresholdY}
          stroke="#f97316"
          strokeDasharray="4,4"
          strokeWidth="1"
        />
        <text
          x={width - padding.right + 5}
          y={thresholdY + 3}
          className="text-[9px] fill-orange-500"
        >
          Active
        </text>

        {/* Y-axis labels */}
        {[2, 5, 8, 10].map(val => {
          const y = padding.top + chartHeight - (val / maxStrength) * chartHeight;
          return (
            <text
              key={val}
              x={padding.left - 8}
              y={y + 3}
              textAnchor="end"
              className="text-[10px] fill-gray-400"
            >
              {val}
            </text>
          );
        })}

        {/* X-axis labels (first, middle, last) */}
        {[0, Math.floor(points.length / 2), points.length - 1].filter((v, i, a) => a.indexOf(v) === i).map(i => (
          <text
            key={i}
            x={points[i]?.x}
            y={height - 5}
            textAnchor="middle"
            className="text-[9px] fill-gray-500"
          >
            {formatDate(points[i]?.date, 'MMM d')}
          </text>
        ))}

        {/* Area fill */}
        <path
          d={`${linePath} L ${points[points.length - 1]?.x} ${padding.top + chartHeight} L ${padding.left} ${padding.top + chartHeight} Z`}
          fill="url(#strengthGradient)"
          opacity="0.3"
        />

        {/* Gradient definition */}
        <defs>
          <linearGradient id="strengthGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#f97316" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke="#f97316"
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
              r={p.isPeak ? 5 : 3}
              fill={p.isPeak ? '#dc2626' : '#f97316'}
              stroke="white"
              strokeWidth="2"
            />
            {/* Peak label */}
            {p.isPeak && (
              <text
                x={p.x}
                y={p.y - 10}
                textAnchor="middle"
                className="text-[9px] fill-red-600 font-medium"
              >
                peak
              </text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}
