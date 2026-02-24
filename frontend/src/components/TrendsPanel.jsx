/**
 * TrendsPanel Component
 * 
 * Main dashboard view for the unified Trends system.
 * Replaces the separate Themes and Signals tabs.
 * 
 * ## CONCEPT:
 * A "Trend" combines:
 * - Narrative: The story/context (e.g., "Căng thẳng thanh khoản")
 * - Signals: Predictions with expiry dates
 * - Events: Evidence supporting the narrative
 * - Urgency: Computed from earliest signal expiry
 * - Priority Score: Composite score (0-100) for importance ranking
 * - Category: Auto-classified (gold, monetary, trade, forex, etc.)
 * 
 * ## LAYOUT:
 * 1. Overview stats bar (total trends, urgent count, accuracy)
 * 2. TODAY'S FOCUS: Top 3-5 trends by priority_score (full cards)
 * 3. OTHER URGENT: Remaining urgent grouped by category (compact)
 * 4. WATCHING: Trends with signals expiring 7-14 days
 * 5. OTHER TRENDS: Low urgency
 * 6. RECENT RESULTS: Recently verified signals
 * 
 * ## API USAGE:
 * - GET /api/trends: Main data source
 * - Returns trends with computed urgency, signal counts, priority_score, category
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
  AlertTriangle, Eye, Archive, Check, X, Zap, Target, Layers
} from 'lucide-react';
import { formatRelativeTime, formatDate, formatNumber, safeParseJSON } from '../utils/format';

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
// Trend Card Component
// Individual card showing trend summary with inline signals
// 
// Signals are sorted by:
// 1. expires_at ASC (soonest first)
// 2. confidence (high > medium > low)
// 3. created_at DESC (newest first)
// ============================================================
function TrendCard({ trend, onClick, compact = false }) {
  const [showAllSignals, setShowAllSignals] = useState(false);
  
  const {
    id,
    name,
    name_vi,
    narrative,
    status,
    strength,
    urgency,
    signals = [],  // Array of signal objects from API
    signals_count = 0,
    signals_accuracy,
    signals_correct_count = 0,
    signals_verified_count = 0,
    earliest_signal_expires,
    related_indicators,
    event_count = 0,
  } = trend;

  // Parse indicators if JSON string
  const indicators = safeParseJSON(related_indicators, []);
  
  // Get active signals only and sort them
  const activeSignals = (signals || [])
    .filter(s => s.status === 'active')
    .sort((a, b) => {
      // 1. Sort by expires_at ASC (soonest first)
      if (a.expires_at && b.expires_at) {
        const diff = new Date(a.expires_at) - new Date(b.expires_at);
        if (diff !== 0) return diff;
      } else if (a.expires_at) return -1;
      else if (b.expires_at) return 1;
      
      // 2. Sort by confidence (high > medium > low)
      const confOrder = { high: 1, medium: 2, low: 3 };
      const confDiff = (confOrder[a.confidence] || 3) - (confOrder[b.confidence] || 3);
      if (confDiff !== 0) return confDiff;
      
      // 3. Sort by created_at DESC (newest first)
      return new Date(b.created_at) - new Date(a.created_at);
    });
  
  // Display max 3 signals, "see more" for rest
  const MAX_VISIBLE_SIGNALS = 3;
  const visibleSignals = showAllSignals ? activeSignals : activeSignals.slice(0, MAX_VISIBLE_SIGNALS);
  const hasMoreSignals = activeSignals.length > MAX_VISIBLE_SIGNALS;

  // Calculate days until earliest signal expires
  const getDaysUntilExpiry = () => {
    if (!earliest_signal_expires) return null;
    const now = new Date();
    const expiry = new Date(earliest_signal_expires);
    const diffDays = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays);
  };

  const daysLeft = getDaysUntilExpiry();

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

  // Confidence badge based on signal accuracy
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
    // Compact view for collapsed sections
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
    <div
      onClick={() => onClick?.(trend)}
      className="bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md cursor-pointer transition-all overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
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
        
        {/* Meta line */}
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>Strength: {strength?.toFixed(1)}</span>
          <span>•</span>
          <span>{signals_count} signals</span>
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

      {/* Narrative */}
      {narrative && (
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
          <p className="text-sm text-gray-700 line-clamp-3">
            💡 {narrative}
          </p>
        </div>
      )}

      {/* Signals List - show actual signals with targets */}
      {activeSignals.length > 0 && (
        <div className="p-4">
          <div className="text-xs font-medium text-gray-500 uppercase mb-2">
            📡 Signals ({activeSignals.length})
          </div>
          <div className="space-y-2">
            {visibleSignals.map((signal, idx) => {
              const daysUntil = signal.expires_at 
                ? Math.max(0, Math.ceil((new Date(signal.expires_at) - new Date()) / (1000 * 60 * 60 * 24)))
                : null;
              
              return (
                <div
                  key={signal.id || idx}
                  className="flex items-center justify-between py-1.5 px-2 bg-gray-50 rounded text-sm"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    {/* Direction indicator */}
                    <span className={`text-base ${
                      signal.direction === 'up' ? 'text-green-500' : 
                      signal.direction === 'down' ? 'text-red-500' : 'text-gray-400'
                    }`}>
                      {signal.direction === 'up' ? '↑' : signal.direction === 'down' ? '↓' : '→'}
                    </span>
                    
                    {/* Indicator name */}
                    <span className="font-medium text-gray-700">
                      {signal.target_indicator || 'Signal'}
                    </span>
                    
                    {/* Target range if quantitative, otherwise just direction */}
                    <span className="text-gray-500 truncate">
                      {signal.target_range_low != null && signal.target_range_high != null
                        ? `${signal.target_range_low} - ${signal.target_range_high}`
                        : signal.direction?.toUpperCase() || ''
                      }
                    </span>
                  </div>
                  
                  {/* Expiry badge */}
                  {daysUntil !== null && (
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      daysUntil <= 2 ? 'bg-red-100 text-red-700' :
                      daysUntil <= 7 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      ⏰ {daysUntil}d
                    </span>
                  )}
                </div>
              );
            })}
            
            {/* See more button */}
            {hasMoreSignals && !showAllSignals && (
              <button
                onClick={(e) => { e.stopPropagation(); setShowAllSignals(true); }}
                className="text-xs text-primary-600 hover:text-primary-700 font-medium"
              >
                + {activeSignals.length - MAX_VISIBLE_SIGNALS} more signals
              </button>
            )}
            {showAllSignals && hasMoreSignals && (
              <button
                onClick={(e) => { e.stopPropagation(); setShowAllSignals(false); }}
                className="text-xs text-gray-500 hover:text-gray-600"
              >
                Show less
              </button>
            )}
          </div>
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
        <div className="divide-y divide-gray-100 bg-white">
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
  hasMore = false,
  loadingMore = false,
  onLoadMore,
}) {
  const [expandedSections, setExpandedSections] = useState({
    otherUrgent: true,
    watching: true,
    low: false,
    results: false,
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Partition trends into sections using useMemo for performance
  const { focusTrends, otherUrgent, watchingTrends, lowTrends, categoryGroups } = useMemo(() => {
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

    return {
      focusTrends: focus,
      otherUrgent: remaining,
      watchingTrends: watching,
      lowTrends: low,
      categoryGroups: sortedGroups,
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
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {categoryGroups.map(([cat, catTrends], idx) => (
                <CategoryGroup
                  key={cat}
                  category={cat}
                  trends={catTrends}
                  onClick={onSelectTrend}
                  defaultExpanded={idx === 0}  // Expand first (highest priority) category by default
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

      {/* Load More */}
      {hasMore && (
        <div className="flex justify-center py-4">
          <button
            onClick={onLoadMore}
            disabled={loadingMore}
            className="px-6 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-all"
          >
            {loadingMore ? (
              <span className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600" />
                Loading...
              </span>
            ) : (
              'Load More Trends'
            )}
          </button>
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
