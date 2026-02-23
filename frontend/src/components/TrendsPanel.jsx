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
 * 
 * ## LAYOUT:
 * - Overview stats bar (total trends, urgent count, accuracy)
 * - URGENT section: Trends with signals expiring < 7 days
 * - WATCHING section: Trends with signals expiring 7-14 days
 * - RECENT RESULTS: Recently verified signals
 * 
 * ## API USAGE:
 * - GET /api/trends: Main data source
 * - Returns trends with computed urgency, signal counts
 * 
 * ## PROPS:
 * - trends: Array of trend objects from API
 * - summary: Summary stats from API
 * - onSelectTrend: Callback when trend card is clicked
 * - loading: Loading state
 */

import React, { useState } from 'react';
import { 
  Flame, TrendingUp, TrendingDown, Clock, ChevronDown, ChevronUp,
  AlertTriangle, Eye, Archive, Check, X, Zap
} from 'lucide-react';
import { formatRelativeTime, formatDate, formatNumber, safeParseJSON } from '../utils/format';

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
// Recent Results Section
// Shows recently verified signals
// 
// TODO: Signal verification is not yet implemented
// This section will show accuracy stats once we have:
// 1. Auto-verification job that compares predictions with actual values
// 2. Or LLM-based verification for qualitative predictions
// ============================================================
function RecentResults({ trends }) {
  // TODO: Implement signal verification system
  // - Auto-verify quantitative signals when expires_at is reached
  // - Compare actual indicator value vs target_range
  // - Update signal.status to verified_correct/verified_wrong
  
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
// ============================================================
export default function TrendsPanel({
  trends = [],
  summary = {},
  onSelectTrend,
  loading = false,
}) {
  const [expandedSections, setExpandedSections] = useState({
    urgent: true,
    watching: true,
    results: false,
  });

  // Separate trends by urgency
  const urgentTrends = trends.filter(t => t.urgency === 'urgent');
  const watchingTrends = trends.filter(t => t.urgency === 'watching');
  const lowTrends = trends.filter(t => t.urgency === 'low' || !t.urgency);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

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

      {/* URGENT Section */}
      {urgentTrends.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('urgent')}
            className="flex items-center gap-2 w-full text-left mb-4"
          >
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-semibold text-gray-900">
              Urgent Warnings
            </h2>
            <span className="px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-sm font-medium">
              {urgentTrends.length}
            </span>
            {expandedSections.urgent ? (
              <ChevronUp className="w-4 h-4 text-gray-400 ml-auto" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400 ml-auto" />
            )}
          </button>
          
          {expandedSections.urgent && (
            <div className="grid md:grid-cols-2 gap-4">
              {urgentTrends.map(trend => (
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

      {/* WATCHING Section */}
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

      {/* LOW/NO URGENCY Section */}
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
