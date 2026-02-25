/**
 * TrendsPanel Component
 * 
 * Main dashboard view for the unified Trends system.
 * 
 * ## LAYOUT:
 * 1. Overview stats bar
 * 2. ★ Overall Market Consensus (weighted bullish/bearish bar)
 * 3. ★ Signal Consensus by Indicator (grid cards)
 * 4. TODAY'S FOCUS: Top 5 trends (cards with consensus + expandable indicator breakdown)
 * 5. OTHER URGENT: Remaining urgent grouped by category (compact)
 * 6. WATCHING: Trends with signals expiring 7-14 days (same card style as Focus)
 * 7. OTHER TRENDS: Low urgency (compact)
 * 8. RECENT RESULTS: Recently verified signals
 * 
 * ## PROPS:
 * - trends: Array of trend objects from API (sorted by priority_score DESC)
 * - summary: Summary stats from API
 * - onSelectTrend: Callback when trend card is clicked
 * - loading: Loading state
 */

import React, { useState, useMemo } from 'react';
import { 
  Flame, TrendingUp, TrendingDown, Clock, ChevronDown, ChevronUp,
  AlertTriangle, Eye, Archive, Check, X, Zap, Target, Layers, BarChart3
} from 'lucide-react';
import { formatRelativeTime, formatDate, formatNumber, safeParseJSON } from '../utils/format';
import { 
  computeConsensus, groupSignalsByIndicator, getDaysUntilExpiry, 
  formatTargetRange, getIndicatorIcon 
} from '../utils/consensus';

// ============================================================
// Category display config
// Maps backend category keys to emoji + Vietnamese labels
// ============================================================
const CATEGORY_CONFIG = {
  gold:        { emoji: '🥇', label: 'Vàng & Kim loại' },
  monetary:    { emoji: '🏦', label: 'Tiền tệ & Ngân hàng' },
  trade:       { emoji: '🚢', label: 'Thương mại & Thuế quan' },
  forex:       { emoji: '💱', label: 'Tỷ giá & Ngoại hối' },
  equity:      { emoji: '📈', label: 'Chứng khoán' },
  energy:      { emoji: '⛽', label: 'Năng lượng' },
  geopolitics: { emoji: '🌍', label: 'Địa chính trị' },
  realestate:  { emoji: '🏠', label: 'Bất động sản' },
  tech:        { emoji: '💻', label: 'Công nghệ' },
  agriculture: { emoji: '🌾', label: 'Nông sản' },
  macro:       { emoji: '📊', label: 'Kinh tế vĩ mô' },
  fiscal:      { emoji: '🧾', label: 'Thuế & Ngân sách' },
  other:       { emoji: '📌', label: 'Khác' },
};

const getCategoryDisplay = (cat) => CATEGORY_CONFIG[cat] || CATEGORY_CONFIG.other;

// Number of top trends to show in "Today's Focus"
const FOCUS_COUNT = 5;

// ============================================================
// Overview Stats Bar
// Shows summary statistics at top of dashboard
// ============================================================
function OverviewStats({ summary }) {
  const {
    total = 0,
    urgent_count = 0,
    watching_count = 0,
    with_signals_count = 0,
    signals_accuracy = null,
    signals_correct = 0,
    signals_total_verified = 0,
  } = summary || {};

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-2xl font-bold text-gray-900">{total}</div>
          <div className="text-sm text-gray-500">Active Trends</div>
        </div>
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-600">{urgent_count}</div>
          <div className="text-sm text-red-500">⚡ Urgent</div>
        </div>
        <div className="text-center p-3 bg-yellow-50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">{watching_count}</div>
          <div className="text-sm text-yellow-500">👁 Watching</div>
        </div>
        <div className="text-center p-3 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {signals_accuracy !== null ? `${signals_accuracy}%` : '-'}
          </div>
          <div className="text-sm text-green-500">
            Accuracy ({signals_correct}/{signals_total_verified})
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Consensus Bar Component
// Renders a bullish/bearish gradient bar with percentage labels
// ============================================================
function ConsensusBar({ consensus, size = 'normal' }) {
  const { bullishPct, bearishPct, direction, totalSignals, upCount, downCount, stableCount } = consensus;
  
  if (totalSignals === 0) return null;

  const barHeight = size === 'large' ? 'h-3' : 'h-2';
  
  const dirColors = {
    bullish: { bg: 'bg-green-500', text: 'text-green-700' },
    bearish: { bg: 'bg-red-500', text: 'text-red-700' },
    neutral: { bg: 'bg-gray-400', text: 'text-gray-600' },
  };
  const colors = dirColors[direction] || dirColors.neutral;

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className={`text-xs font-semibold ${direction === 'bearish' ? 'text-red-600' : 'text-gray-400'}`}>
          {direction === 'bearish' ? `▼ ${bearishPct}% DOWN` : `▼ ${bearishPct}%`}
        </span>
        <span className={`text-xs font-semibold ${direction === 'bullish' ? 'text-green-600' : 'text-gray-400'}`}>
          {direction === 'bullish' ? `▲ ${bullishPct}% UP` : `${bullishPct}% ▲`}
        </span>
      </div>
      <div className={`w-full ${barHeight} rounded-full bg-red-100 overflow-hidden`}>
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            direction === 'bullish' ? 'bg-green-500' : direction === 'bearish' ? 'bg-red-500' : 'bg-gray-400'
          }`}
          style={{ width: `${bullishPct}%`, marginLeft: '0' }}
        />
      </div>
      {size === 'large' && (
        <div className="text-xs text-gray-400 mt-1 text-center">
          {totalSignals} signals · {upCount}↑ {downCount}↓ {stableCount > 0 ? `${stableCount}→` : ''}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Overall Market Consensus Section
// Shows aggregate weighted consensus across ALL signals
// ============================================================
function OverallMarketConsensus({ allSignals }) {
  const consensus = useMemo(() => computeConsensus(allSignals), [allSignals]);
  const indicatorGroups = useMemo(() => groupSignalsByIndicator(allSignals), [allSignals]);

  if (consensus.totalSignals === 0) return null;

  const { direction, bullishPct, bearishPct, totalSignals } = consensus;
  
  const bgColor = direction === 'bullish' ? 'border-green-200 bg-green-50/50' 
    : direction === 'bearish' ? 'border-red-200 bg-red-50/50' 
    : 'border-gray-200 bg-gray-50/50';

  const mainLabel = direction === 'bullish' ? `BULLISH ${bullishPct}%`
    : direction === 'bearish' ? `BEARISH ${bearishPct}%`
    : `NEUTRAL ${bullishPct}%`;

  const mainColor = direction === 'bullish' ? 'text-green-700'
    : direction === 'bearish' ? 'text-red-700'
    : 'text-gray-600';

  return (
    <div className={`rounded-xl border-2 ${bgColor} p-5 mb-6`}>
      <div className="text-center mb-3">
        <div className={`text-xl font-bold ${mainColor}`}>
          {direction === 'bullish' ? '▲' : direction === 'bearish' ? '▼' : '→'} {mainLabel}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Based on {totalSignals} active signals across {indicatorGroups.length} indicators
        </div>
      </div>
      <ConsensusBar consensus={consensus} size="large" />
    </div>
  );
}

// ============================================================
// Indicator Consensus Card (for the grid)
// Single card showing consensus for one indicator
// ============================================================
function IndicatorConsensusCard({ indicator, signals, consensus }) {
  const icon = getIndicatorIcon(indicator);
  const { direction, bullishPct, bearishPct, totalSignals, upCount, downCount, stableCount } = consensus;

  const borderColor = direction === 'bullish' ? 'border-green-200 hover:border-green-300'
    : direction === 'bearish' ? 'border-red-200 hover:border-red-300'
    : 'border-gray-200 hover:border-gray-300';

  const pctLabel = direction === 'bullish' ? `▲ ${bullishPct}% UP`
    : direction === 'bearish' ? `▼ ${bearishPct}% DOWN`
    : `→ ${bullishPct}% FLAT`;

  const pctColor = direction === 'bullish' ? 'text-green-600'
    : direction === 'bearish' ? 'text-red-600'
    : 'text-gray-500';

  return (
    <div className={`bg-white rounded-lg border ${borderColor} p-3 transition-all`}>
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-base">{icon}</span>
        <span className="font-medium text-sm text-gray-800 truncate">{indicator}</span>
      </div>
      
      <div className={`text-sm font-bold ${pctColor} mb-2`}>{pctLabel}</div>
      
      <ConsensusBar consensus={consensus} size="small" />
      
      <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
        <span>{totalSignals} signals</span>
        <span>{upCount}↑ {downCount}↓{stableCount > 0 ? ` ${stableCount}→` : ''}</span>
      </div>
    </div>
  );
}

// ============================================================
// Indicator Consensus Grid Section
// Shows per-indicator consensus cards, sorted by signal count
// ============================================================
function IndicatorConsensusGrid({ allSignals }) {
  const [showAll, setShowAll] = useState(false);
  const indicatorGroups = useMemo(() => groupSignalsByIndicator(allSignals), [allSignals]);

  if (indicatorGroups.length === 0) return null;

  const DEFAULT_VISIBLE = 6;
  const visible = showAll ? indicatorGroups : indicatorGroups.slice(0, DEFAULT_VISIBLE);
  const hasMore = indicatorGroups.length > DEFAULT_VISIBLE;

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-blue-500" />
        <h2 className="text-lg font-semibold text-gray-900">Signal Consensus by Indicator</h2>
        <span className="text-xs text-gray-400">sorted by signal count</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-3 gap-3">
        {visible.map(({ indicator, signals, consensus }) => (
          <IndicatorConsensusCard
            key={indicator}
            indicator={indicator}
            signals={signals}
            consensus={consensus}
          />
        ))}
      </div>

      {hasMore && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
        >
          {showAll ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Show {indicatorGroups.length - DEFAULT_VISIBLE} more indicators
            </>
          )}
        </button>
      )}
    </div>
  );
}

// ============================================================
// Signal Row Component
// Individual signal within the indicator breakdown
// Shows: direction, prediction text, target, confidence, expiry
// ============================================================
function SignalRow({ signal }) {
  const daysUntil = getDaysUntilExpiry(signal.expires_at);
  const targetDisplay = formatTargetRange(signal);

  const dirIcon = signal.direction === 'up' ? '↑' : signal.direction === 'down' ? '↓' : '→';
  const dirColor = signal.direction === 'up' ? 'text-green-500'
    : signal.direction === 'down' ? 'text-red-500'
    : 'text-gray-400';

  const confConfig = {
    high: { color: 'text-green-600 bg-green-50', label: 'high' },
    medium: { color: 'text-yellow-600 bg-yellow-50', label: 'med' },
    low: { color: 'text-red-600 bg-red-50', label: 'low' },
  };
  const conf = confConfig[signal.confidence] || confConfig.medium;

  return (
    <div className="py-2 px-3 bg-gray-50/70 rounded-lg text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <span className={`text-base mt-0.5 ${dirColor} flex-shrink-0`}>{dirIcon}</span>
          <div className="min-w-0 flex-1">
            {signal.prediction && (
              <p className="text-gray-700 text-sm leading-snug line-clamp-2">
                {signal.prediction}
              </p>
            )}
            {!signal.prediction && (
              <p className="text-gray-500 text-sm italic">
                {signal.target_indicator} {signal.direction}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Target range */}
          <span className="text-xs font-mono text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
            {targetDisplay}
          </span>
          {/* Confidence badge */}
          <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${conf.color}`}>
            {conf.label}
          </span>
          {/* Expiry */}
          {daysUntil !== null && (
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              daysUntil <= 2 ? 'bg-red-100 text-red-700' :
              daysUntil <= 7 ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              ⏰ {daysUntil}d
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Indicator Breakdown Section (inside expanded TrendCard)
// Groups signals by indicator, shows per-indicator consensus + signal rows
// ============================================================
function IndicatorBreakdown({ signals }) {
  const groups = useMemo(() => groupSignalsByIndicator(signals), [signals]);

  if (groups.length === 0) return null;

  return (
    <div className="space-y-3">
      {groups.map(({ indicator, signals: indSignals, consensus: indConsensus }) => {
        const icon = getIndicatorIcon(indicator);
        return (
          <div key={indicator} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Indicator header + consensus */}
            <div className="px-3 py-2 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm">{icon}</span>
                  <span className="font-medium text-sm text-gray-800">{indicator}</span>
                  <span className="text-xs text-gray-400">({indSignals.length} signals)</span>
                </div>
                <span className={`text-xs font-bold ${
                  indConsensus.direction === 'bullish' ? 'text-green-600' :
                  indConsensus.direction === 'bearish' ? 'text-red-600' : 'text-gray-500'
                }`}>
                  {indConsensus.label}
                </span>
              </div>
              <ConsensusBar consensus={indConsensus} size="small" />
            </div>
            {/* Individual signals */}
            <div className="p-2 space-y-1.5">
              {indSignals
                .sort((a, b) => {
                  // Sort by expires_at ASC, then confidence DESC
                  if (a.expires_at && b.expires_at) {
                    const diff = new Date(a.expires_at) - new Date(b.expires_at);
                    if (diff !== 0) return diff;
                  }
                  const confOrder = { high: 1, medium: 2, low: 3 };
                  return (confOrder[a.confidence] || 3) - (confOrder[b.confidence] || 3);
                })
                .map((sig, idx) => (
                  <SignalRow key={sig.id || idx} signal={sig} />
                ))
              }
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// Indicator Mini Cards (compact, shown inside TrendCard before expand)
// Small cards: icon + indicator + consensus% + signal count
// ============================================================
function IndicatorMiniCards({ signals }) {
  const groups = useMemo(() => groupSignalsByIndicator(signals), [signals]);
  
  if (groups.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {groups.map(({ indicator, signals: indSignals, consensus: indConsensus }) => {
        const icon = getIndicatorIcon(indicator);
        const pctColor = indConsensus.direction === 'bullish' ? 'text-green-600'
          : indConsensus.direction === 'bearish' ? 'text-red-600'
          : 'text-gray-500';
        const borderColor = indConsensus.direction === 'bullish' ? 'border-green-200'
          : indConsensus.direction === 'bearish' ? 'border-red-200'
          : 'border-gray-200';

        return (
          <div key={indicator} className={`inline-flex items-center gap-1.5 px-2 py-1.5 rounded-lg border ${borderColor} bg-white text-xs`}>
            <span>{icon}</span>
            <span className="font-medium text-gray-700">{indicator}</span>
            <span className={`font-bold ${pctColor}`}>{indConsensus.label}</span>
            <span className="text-gray-400">{indSignals.length}sig</span>
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// Trend Card Component (REDESIGNED)
// 
// Shows: header, overall consensus bar, indicator mini-cards
// Expandable: full indicator breakdown with individual signals
// ============================================================
function TrendCard({ trend, onClick, compact = false }) {
  const [expanded, setExpanded] = useState(false);
  
  const {
    id,
    name,
    name_vi,
    narrative,
    status,
    strength,
    urgency,
    signals = [],
    signals_count = 0,
    signals_accuracy,
    signals_correct_count = 0,
    signals_verified_count = 0,
    earliest_signal_expires,
    related_indicators,
    event_count = 0,
  } = trend;

  const indicators = safeParseJSON(related_indicators, []);
  
  const activeSignals = useMemo(() => 
    (signals || []).filter(s => s.status === 'active'),
    [signals]
  );

  const trendConsensus = useMemo(() => computeConsensus(activeSignals), [activeSignals]);
  const indicatorGroups = useMemo(() => groupSignalsByIndicator(activeSignals), [activeSignals]);

  const daysLeft = getDaysUntilExpiry(earliest_signal_expires);

  // Urgency badge config
  const getUrgencyBadge = () => {
    switch (urgency) {
      case 'urgent':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold">
            <Zap className="w-3 h-3" />
            {daysLeft}d
          </span>
        );
      case 'watching':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-semibold">
            <Eye className="w-3 h-3" />
            {daysLeft}d
          </span>
        );
      case 'low':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-semibold">
            <Clock className="w-3 h-3" />
            {daysLeft}d
          </span>
        );
      default:
        return null;
    }
  };

  const getConfidenceBadge = () => {
    if (signals_verified_count === 0) return null;
    const accuracy = signals_correct_count / signals_verified_count;
    const color = accuracy >= 0.7 ? 'text-green-600' : accuracy >= 0.4 ? 'text-yellow-600' : 'text-red-600';
    return (
      <span className={`text-xs ${color}`}>
        {signals_correct_count}/{signals_verified_count} correct
      </span>
    );
  };

  if (compact) {
    return (
      <div
        onClick={() => onClick?.(trend)}
        className="bg-white rounded-lg border border-gray-200 hover:border-primary-300 p-3 cursor-pointer transition-all"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className={`w-4 h-4 ${urgency === 'urgent' ? 'text-red-500' : 'text-orange-400'}`} />
            <span className="font-medium text-gray-900 text-sm">{name_vi || name}</span>
          </div>
          <div className="flex items-center gap-2">
            {getUrgencyBadge()}
            <span className="text-xs text-gray-500">{signals_count} signals</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all overflow-hidden">
      {/* Header — clickable to open trend detail */}
      <div className="p-4 border-b border-gray-100 cursor-pointer" onClick={() => onClick?.(trend)}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <Flame className={`w-5 h-5 ${urgency === 'urgent' ? 'text-red-500' : 'text-orange-400'}`} />
            <h3 className="font-semibold text-gray-900">{name_vi || name}</h3>
          </div>
          <div className="flex items-center gap-2">
            {getUrgencyBadge()}
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              status === 'active' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'
            }`}>
              {status?.toUpperCase()}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Strength: {strength?.toFixed(1)}</span>
          <span>•</span>
          <span>{activeSignals.length} signals</span>
          <span>•</span>
          <span>{indicatorGroups.length} indicators</span>
          <span>•</span>
          <span>{event_count} events</span>
          {getConfidenceBadge() && (
            <>
              <span>•</span>
              {getConfidenceBadge()}
            </>
          )}
        </div>
      </div>

      {/* Overall Trend Consensus */}
      {trendConsensus.totalSignals > 0 && (
        <div className="px-4 py-3 border-b border-gray-100">
          <ConsensusBar consensus={trendConsensus} size="large" />
        </div>
      )}

      {/* Indicator Mini Cards (always visible) */}
      {indicatorGroups.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-100">
          <IndicatorMiniCards signals={activeSignals} />
        </div>
      )}

      {/* Expand/Collapse button for full indicator breakdown */}
      {activeSignals.length > 0 && (
        <div className="px-4 py-2 border-b border-gray-100">
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium w-full justify-center"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Collapse signal detail
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                Expand {activeSignals.length} signals by indicator
              </>
            )}
          </button>
        </div>
      )}

      {/* Expanded: Full Indicator Breakdown */}
      {expanded && (
        <div className="p-4">
          <IndicatorBreakdown signals={activeSignals} />
        </div>
      )}

      {/* Narrative (collapsed state, shown below) */}
      {narrative && !expanded && (
        <div className="px-4 py-3 bg-gray-50">
          <p className="text-sm text-gray-700 line-clamp-2">
            💡 {narrative}
          </p>
        </div>
      )}

      {/* Events link */}
      {event_count > 0 && (
        <div className="px-4 py-2 text-xs text-gray-400 cursor-pointer" onClick={() => onClick?.(trend)}>
          🔗 {event_count} causal events
        </div>
      )}
    </div>
  );
}

// ============================================================
// Priority Score Badge
// Shows composite priority score as a visual badge
// ============================================================
function PriorityBadge({ score }) {
  if (score == null) return null;
  const color = score >= 60 ? 'bg-red-600' :
                score >= 40 ? 'bg-orange-500' :
                score >= 25 ? 'bg-yellow-500' : 'bg-gray-400';
  return (
    <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full ${color} text-white text-xs font-bold`}>
      {Math.round(score)}
    </span>
  );
}

// ============================================================
// Category Badge
// Shows category emoji + label inline
// ============================================================
function CategoryBadge({ category }) {
  const { emoji, label } = getCategoryDisplay(category);
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs">
      {emoji} {label}
    </span>
  );
}

// ============================================================
// Compact Trend Row (for category-grouped section)
// Single-line row with score, name, key signal, expiry
// ============================================================
function CompactTrendRow({ trend, onClick }) {
  const {
    name, name_vi, urgency, signals_count = 0,
    earliest_signal_expires, priority_score, signals = [],
  } = trend;

  const daysLeft = earliest_signal_expires
    ? Math.max(0, Math.ceil((new Date(earliest_signal_expires) - new Date()) / (1000 * 60 * 60 * 24)))
    : null;

  // Get first active signal summary
  const firstSignal = (signals || []).find(s => s.status === 'active');
  const signalHint = firstSignal
    ? `${firstSignal.direction === 'up' ? '↑' : firstSignal.direction === 'down' ? '↓' : '→'} ${firstSignal.target_indicator || ''}`
    : '';

  return (
    <div
      onClick={() => onClick?.(trend)}
      className="flex items-center gap-3 py-2 px-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors group"
    >
      {/* Priority score */}
      <PriorityBadge score={priority_score} />

      {/* Name */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-gray-900 truncate group-hover:text-primary-700">
          {name_vi || name}
        </div>
        {signalHint && (
          <div className="text-xs text-gray-500 truncate">{signalHint}</div>
        )}
      </div>

      {/* Signals count */}
      <span className="text-xs text-gray-500 whitespace-nowrap">
        {signals_count} signals
      </span>

      {/* Expiry */}
      {daysLeft !== null && (
        <span className={`text-xs px-1.5 py-0.5 rounded font-medium whitespace-nowrap ${
          daysLeft <= 2 ? 'bg-red-100 text-red-700' :
          daysLeft <= 7 ? 'bg-yellow-100 text-yellow-700' :
          'bg-gray-100 text-gray-600'
        }`}>
          {daysLeft}d
        </span>
      )}
    </div>
  );
}

// ============================================================
// Category Group Component
// Shows trends for one category in a collapsible group
// ============================================================
function CategoryGroup({ category, trends, onClick, defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const { emoji, label } = getCategoryDisplay(category);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <span className="text-base">{emoji}</span>
        <span className="text-sm font-medium text-gray-800">{label}</span>
        <span className="px-1.5 py-0.5 bg-white text-gray-600 rounded text-xs font-medium border border-gray-200">
          {trends.length}
        </span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-gray-400 ml-auto" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 ml-auto" />
        )}
      </button>
      {expanded && (
        <div className="divide-y divide-gray-100 bg-white max-h-[440px] overflow-y-auto">
          {trends.map(trend => (
            <CompactTrendRow key={trend.id} trend={trend} onClick={onClick} />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Recent Results Section
// Shows recently verified signals
// 
// TODO: Signal verification is not yet implemented
// This section will show accuracy stats once we have:
// 1. Auto-verification job that compares predictions with actual values
// 2. Or LLM-based verification for qualitative predictions
// ============================================================
function RecentResults({ trends }) {
  return (
    <div className="text-center py-6">
      <div className="text-gray-400 mb-2">
        <Clock className="w-8 h-8 mx-auto mb-2" />
      </div>
      <p className="text-sm text-gray-500 font-medium">Verification Coming Soon</p>
      <p className="text-xs text-gray-400 mt-1">
        Signal accuracy tracking will be available in a future update
      </p>
    </div>
  );
}

// ============================================================
// Main TrendsPanel Component
// 
// Layout:
// 1. OverviewStats
// 2. Today's Focus (top N by priority_score, full cards)
// 3. Other Urgent (grouped by category, compact rows)
// 4. Watching
// 5. Other Trends
// 6. Load More
// 7. Recent Results
// ============================================================
export default function TrendsPanel({
  trends = [],
  summary = {},
  onSelectTrend,
  loading = false,
}) {
  const [expandedSections, setExpandedSections] = useState({
    otherUrgent: true,
    watching: true,
    low: true,
    results: false,
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Partition trends into sections using useMemo for performance
  const { focusTrends, otherUrgent, watchingTrends, lowTrends, categoryGroups, allActiveSignals } = useMemo(() => {
    const urgent = trends.filter(t => t.urgency === 'urgent');
    const watching = trends.filter(t => t.urgency === 'watching');
    const low = trends.filter(t => t.urgency === 'low' || !t.urgency);

    // Trends are already sorted by priority_score DESC from API.
    // Top FOCUS_COUNT urgent become "Today's Focus", rest go to "Other Urgent"
    const focus = urgent.slice(0, FOCUS_COUNT);
    const remaining = urgent.slice(FOCUS_COUNT);

    // Group remaining urgent by category
    const groups = {};
    for (const t of remaining) {
      const cat = t.category || 'other';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(t);
    }

    // Sort category groups by total signals descending (most active first)
    const sortedGroups = Object.entries(groups)
      .sort((a, b) => {
        const aScore = Math.max(...a[1].map(t => t.priority_score || 0));
        const bScore = Math.max(...b[1].map(t => t.priority_score || 0));
        return bScore - aScore;
      });

    // Collect ALL active signals from ALL trends for overall consensus
    const allSignals = [];
    for (const t of trends) {
      if (t.signals) {
        for (const sig of t.signals) {
          if (sig.status === 'active') allSignals.push(sig);
        }
      }
    }

    return {
      focusTrends: focus,
      otherUrgent: remaining,
      watchingTrends: watching,
      lowTrends: low,
      categoryGroups: sortedGroups,
      allActiveSignals: allSignals,
    };
  }, [trends]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (trends.length === 0) {
    return (
      <div className="text-center py-12">
        <Flame className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-700 mb-2">No Active Trends</h3>
        <p className="text-sm text-gray-500">
          Trends will appear here when patterns are detected in market news
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <OverviewStats summary={summary} />

      {/* ═══════════════════════════════════════════════════════
          ★ OVERALL MARKET CONSENSUS
          Weighted bullish/bearish bar across all active signals
          ═══════════════════════════════════════════════════════ */}
      <OverallMarketConsensus allSignals={allActiveSignals} />

      {/* ═══════════════════════════════════════════════════════
          ★ SIGNAL CONSENSUS BY INDICATOR
          Grid of per-indicator consensus cards
          ═══════════════════════════════════════════════════════ */}
      <IndicatorConsensusGrid allSignals={allActiveSignals} />

      {/* ═══════════════════════════════════════════════════════
          🎯 TODAY'S FOCUS — Top trends by priority score
          Full TrendCard with narrative + signals visible
          ═══════════════════════════════════════════════════════ */}
      {focusTrends.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              Today's Focus
            </h2>
            <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-sm font-medium">
              Top {focusTrends.length}
            </span>
            <span className="text-xs text-gray-400 ml-2">Ranked by composite priority score</span>
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            {focusTrends.map((trend, idx) => (
              <div key={trend.id} className="relative">
                {/* Rank badge overlay */}
                <div className="absolute -top-2 -left-2 z-10 w-7 h-7 rounded-full bg-red-600 text-white flex items-center justify-center text-xs font-bold shadow-md">
                  #{idx + 1}
                </div>
                <TrendCard
                  trend={trend}
                  onClick={onSelectTrend}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          ⚡ OTHER URGENT — Remaining urgent, grouped by category
          Compact rows in collapsible category groups
          ═══════════════════════════════════════════════════════ */}
      {otherUrgent.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('otherUrgent')}
            className="flex items-center gap-2 w-full text-left mb-3"
          >
            <Layers className="w-5 h-5 text-orange-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              Other Urgent
            </h2>
            <span className="px-2 py-0.5 bg-orange-100 text-orange-600 rounded-full text-sm font-medium">
              {otherUrgent.length}
            </span>
            <span className="text-xs text-gray-400 ml-1">
              in {categoryGroups.length} categories
            </span>
            {expandedSections.otherUrgent ? (
              <ChevronUp className="w-4 h-4 text-gray-400 ml-auto" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400 ml-auto" />
            )}
          </button>
          
          {expandedSections.otherUrgent && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 items-start">
              {categoryGroups.map(([cat, catTrends], idx) => (
                <CategoryGroup
                  key={cat}
                  category={cat}
                  trends={catTrends}
                  onClick={onSelectTrend}
                  defaultExpanded={false}  // All categories collapsed by default
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          👁 WATCHING — Signals expiring 7-14 days
          ═══════════════════════════════════════════════════════ */}
      {watchingTrends.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('watching')}
            className="flex items-center gap-2 w-full text-left mb-4"
          >
            <Eye className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              Watching
            </h2>
            <span className="px-2 py-0.5 bg-yellow-100 text-yellow-600 rounded-full text-sm font-medium">
              {watchingTrends.length}
            </span>
            {expandedSections.watching ? (
              <ChevronUp className="w-4 h-4 text-gray-400 ml-auto" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400 ml-auto" />
            )}
          </button>
          
          {expandedSections.watching && (
            <div className="grid md:grid-cols-2 gap-4">
              {watchingTrends.map(trend => (
                <TrendCard
                  key={trend.id}
                  trend={trend}
                  onClick={onSelectTrend}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════
          📋 OTHER TRENDS — Low urgency
          ═══════════════════════════════════════════════════════ */}
      {lowTrends.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('low')}
            className="flex items-center gap-2 w-full text-left mb-4"
          >
            <Clock className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">
              Other Trends
            </h2>
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
              {lowTrends.length}
            </span>
            {expandedSections.low ? (
              <ChevronUp className="w-4 h-4 text-gray-400 ml-auto" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400 ml-auto" />
            )}
          </button>
          
          {expandedSections.low && (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {lowTrends.map(trend => (
                <TrendCard
                  key={trend.id}
                  trend={trend}
                  onClick={onSelectTrend}
                  compact
                />
              ))}
            </div>
          )}
        </div>
      )}



      {/* Recent Results */}
      <div>
        <button
          onClick={() => toggleSection('results')}
          className="flex items-center gap-2 w-full text-left mb-4"
        >
          <Check className="w-5 h-5 text-green-500" />
          <h2 className="text-lg font-semibold text-gray-900">
            Recent Results
          </h2>
          {expandedSections.results ? (
            <ChevronUp className="w-4 h-4 text-gray-400 ml-auto" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400 ml-auto" />
          )}
        </button>
        
        {expandedSections.results && (
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <RecentResults trends={trends} />
          </div>
        )}
      </div>
    </div>
  );
}
