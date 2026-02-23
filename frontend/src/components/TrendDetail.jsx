/**
 * TrendDetail Component
 * 
 * Modal view showing full details of a single Trend.
 * Displays the complete story with all signals, events, and history.
 * 
 * ## LAYOUT:
 * - Header: Status badges, urgency, strength, timestamps
 * - Narrative: AI-synthesized summary of the trend
 * - Two columns:
 *   - Left: Evidence (related events)
 *   - Right: Signals (predictions with targets/directions)
 * - Signal History: Recently verified signals
 * - Affected Indicators: Which indicators to watch
 * - Actions: Archive, Dismiss, Edit
 * 
 * ## API USAGE:
 * - GET /api/trends/{id}: Full trend data with signals and events
 * - POST /api/trends/{id}/archive: Archive the trend
 * - POST /api/trends/{id}/dismiss: Dismiss the trend
 * 
 * ## PROPS:
 * - trend: Trend object from parent (basic info)
 * - onClose: Callback to close modal
 * - onArchive: Callback when archived
 */

import React, { useState, useEffect } from 'react';
import {
  X, Flame, Clock, TrendingUp, TrendingDown, AlertTriangle,
  Check, Archive, Eye, ExternalLink, ChevronDown, ChevronUp,
  Zap, Calendar
} from 'lucide-react';
import { formatRelativeTime, formatDate, formatNumber, safeParseJSON } from '../utils/format';
import { getTrend, archiveTrend, dismissTrend } from '../services/api';

// ============================================================
// Status Badge Component
// ============================================================
function StatusBadge({ status }) {
  const config = {
    active: { color: 'bg-green-100 text-green-700', label: '🟢 ACTIVE' },
    emerging: { color: 'bg-blue-100 text-blue-700', label: '🌱 EMERGING' },
    fading: { color: 'bg-gray-100 text-gray-600', label: '📉 FADING' },
    archived: { color: 'bg-gray-100 text-gray-500', label: '📦 ARCHIVED' },
  }[status?.toLowerCase()] || { color: 'bg-gray-100 text-gray-600', label: status };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}

// ============================================================
// Urgency Badge Component
// ============================================================
function UrgencyBadge({ urgency, expiresAt }) {
  if (!urgency) return null;

  const daysLeft = expiresAt 
    ? Math.ceil((new Date(expiresAt) - new Date()) / (1000 * 60 * 60 * 24))
    : null;

  const config = {
    urgent: { color: 'bg-red-100 text-red-700', icon: <Zap className="w-3 h-3" />, label: `⚡ ${daysLeft}d` },
    watching: { color: 'bg-yellow-100 text-yellow-700', icon: <Eye className="w-3 h-3" />, label: `👁 ${daysLeft}d` },
    low: { color: 'bg-gray-100 text-gray-600', icon: <Clock className="w-3 h-3" />, label: `${daysLeft}d` },
  }[urgency] || { color: 'bg-gray-100 text-gray-600', label: urgency };

  return (
    <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.icon}
      {config.label}
    </span>
  );
}

// ============================================================
// Signal Card (inside trend detail)
// ============================================================
function SignalCard({ signal }) {
  const {
    prediction,
    direction,
    target_indicator,
    target_range_low,
    target_range_high,
    signal_type,
    confidence,
    status,
    expires_at,
    reasoning,
    actual_value,
    verified_at,
  } = signal;

  const isActive = status === 'active';
  const isCorrect = status === 'verified_correct';
  const isWrong = status === 'verified_wrong';

  const daysLeft = expires_at 
    ? Math.ceil((new Date(expires_at) - new Date()) / (1000 * 60 * 60 * 24))
    : null;

  const confidenceConfig = {
    high: { color: 'text-green-600', icon: '🟢' },
    medium: { color: 'text-yellow-600', icon: '🟡' },
    low: { color: 'text-red-600', icon: '🔴' },
  }[confidence?.toLowerCase()] || { color: 'text-gray-600', icon: '⚪' };

  const directionIcon = direction === 'up' 
    ? <TrendingUp className="w-4 h-4 text-green-600" />
    : direction === 'down' 
    ? <TrendingDown className="w-4 h-4 text-red-600" />
    : <span className="text-gray-500">→</span>;

  return (
    <div className={`p-4 rounded-lg border ${
      isCorrect ? 'bg-green-50 border-green-200' :
      isWrong ? 'bg-red-50 border-red-200' :
      'bg-white border-gray-200'
    }`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {directionIcon}
          <span className="font-medium text-gray-900">{target_indicator || 'General'}</span>
        </div>
        {isActive && daysLeft !== null && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            daysLeft <= 3 ? 'bg-red-100 text-red-700' :
            daysLeft <= 7 ? 'bg-yellow-100 text-yellow-700' :
            'bg-gray-100 text-gray-600'
          }`}>
            ⏰ {daysLeft}d
          </span>
        )}
        {!isActive && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            isCorrect ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            {isCorrect ? '✅ CORRECT' : '❌ WRONG'}
          </span>
        )}
      </div>

      {/* Prediction text */}
      <p className="text-sm text-gray-700 mb-2">{prediction}</p>

      {/* Target info - only show if has target */}
      {(target_range_low !== null || target_range_high !== null) && (
        <div className="text-sm text-gray-600 mb-2">
          <span className="font-medium">Target:</span>{' '}
          {target_range_low !== null && target_range_high !== null 
            ? `${formatNumber(target_range_low)} - ${formatNumber(target_range_high)}`
            : target_range_low !== null 
            ? `≥ ${formatNumber(target_range_low)}`
            : `≤ ${formatNumber(target_range_high)}`
          }
        </div>
      )}

      {/* Direction only (no target) */}
      {signal_type === 'directional' && !target_range_low && !target_range_high && (
        <div className="text-sm text-gray-600 mb-2">
          <span className="font-medium">Direction:</span>{' '}
          <span className="capitalize">{direction}</span>
        </div>
      )}

      {/* Verified result */}
      {actual_value !== null && (
        <div className="text-sm text-gray-600 mb-2">
          <span className="font-medium">Actual:</span> {formatNumber(actual_value)}
        </div>
      )}

      {/* Confidence */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className={confidenceConfig.color}>
          {confidenceConfig.icon} {confidence}
        </span>
      </div>
    </div>
  );
}

// ============================================================
// Event Card (inside trend detail)
// ============================================================
function EventCard({ event }) {
  const { title, summary, source, current_score, published_at, source_url } = event;

  return (
    <div className="p-3 bg-white rounded-lg border border-gray-200 hover:border-primary-300 transition-colors">
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-xs font-bold text-primary-600">{current_score || '-'}</span>
        <span className="text-xs text-gray-400">{formatRelativeTime(published_at)}</span>
      </div>
      <h4 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">{title}</h4>
      {summary && (
        <p className="text-xs text-gray-500 line-clamp-2">{summary}</p>
      )}
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-400">{source}</span>
        {source_url && (
          <a
            href={source_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-primary-600 hover:underline flex items-center gap-1"
          >
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Main TrendDetail Component
// ============================================================
export default function TrendDetail({ trend: initialTrend, onClose, onArchive, onViewEvent, onViewSignal }) {
  const [trend, setTrend] = useState(initialTrend);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAllEvents, setShowAllEvents] = useState(false);

  // Fetch full trend details
  useEffect(() => {
    const fetchTrendDetails = async () => {
      if (!initialTrend?.id) return;
      
      try {
        setLoading(true);
        const data = await getTrend(initialTrend.id);
        setTrend(data);
      } catch (err) {
        console.error('Failed to fetch trend details:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTrendDetails();
  }, [initialTrend?.id]);

  // Handle archive
  const handleArchive = async () => {
    try {
      await archiveTrend(trend.id);
      onArchive?.();
      onClose?.();
    } catch (err) {
      console.error('Failed to archive trend:', err);
    }
  };

  // Handle dismiss
  const handleDismiss = async () => {
    try {
      await dismissTrend(trend.id);
      onArchive?.();
      onClose?.();
    } catch (err) {
      console.error('Failed to dismiss trend:', err);
    }
  };

  if (!trend) return null;

  const {
    id,
    name,
    name_vi,
    narrative,
    description,
    status,
    strength,
    peak_strength,
    urgency,
    earliest_signal_expires,
    signals_count = 0,
    signals_accuracy,
    signals_correct_count = 0,
    signals_verified_count = 0,
    first_seen,
    last_seen,
    related_indicators,
    signals = [],
    events = [],
  } = trend;

  const indicators = safeParseJSON(related_indicators, []);
  const activeSignals = signals.filter(s => s.status === 'active');
  const verifiedSignals = signals.filter(s => s.status === 'verified_correct' || s.status === 'verified_wrong');
  const displayEvents = showAllEvents ? events : events.slice(0, 3);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 z-10">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Flame className={`w-6 h-6 ${strength >= 5 ? 'text-orange-500' : 'text-gray-400'}`} />
                <h2 className="text-xl font-bold text-gray-900">{name_vi || name}</h2>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={status} />
                <UrgencyBadge urgency={urgency} expiresAt={earliest_signal_expires} />
                <span className="text-sm text-gray-500">
                  Strength: {strength?.toFixed(1)}
                  {peak_strength && <span className="text-gray-400"> (Peak: {peak_strength.toFixed(1)})</span>}
                </span>
                <span className="text-sm text-gray-500">
                  Started: {formatDate(first_seen, 'MMM d, yyyy')}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-500">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
              <p>Failed to load details: {error}</p>
            </div>
          ) : (
            <>
              {/* Narrative */}
              <div className="bg-gradient-to-r from-orange-50 to-yellow-50 rounded-xl p-5 border border-orange-100">
                <h3 className="text-sm font-semibold text-orange-700 mb-3 flex items-center gap-2">
                  💡 NARRATIVE
                </h3>
                <p className="text-gray-700 leading-relaxed">
                  {narrative || description || 'Chưa có narrative được tổng hợp cho trend này.'}
                </p>
              </div>

              {/* Two columns: Events & Signals */}
              <div className="grid md:grid-cols-2 gap-6">
                {/* Events Column */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    📰 EVIDENCE ({events.length} events)
                  </h3>
                  <div className="space-y-3">
                    {displayEvents.length > 0 ? (
                      displayEvents.map((event) => (
                        <div key={event.id} onClick={() => onViewEvent?.(event)} className="cursor-pointer">
                          <EventCard event={event} />
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500 py-4 text-center">Chưa có events liên quan</p>
                    )}
                    {events.length > 3 && (
                      <button
                        onClick={() => setShowAllEvents(!showAllEvents)}
                        className="w-full py-2 text-sm text-primary-600 hover:bg-primary-50 rounded-lg flex items-center justify-center gap-1"
                      >
                        {showAllEvents ? (
                          <>Show less <ChevronUp className="w-4 h-4" /></>
                        ) : (
                          <>View all {events.length} events <ChevronDown className="w-4 h-4" /></>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Signals Column */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    📡 SIGNALS ({activeSignals.length} active)
                    {signals_verified_count > 0 && (
                      <span className="text-xs text-gray-400">
                        • {signals_correct_count}/{signals_verified_count} correct
                      </span>
                    )}
                  </h3>
                  <div className="space-y-3">
                    {activeSignals.length > 0 ? (
                      activeSignals.map((signal) => (
                        <div key={signal.id} onClick={() => onViewSignal?.(signal)} className="cursor-pointer">
                          <SignalCard signal={signal} />
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500 py-4 text-center">Không có signals đang active</p>
                    )}
                  </div>

                  {/* Verified signals history */}
                  {verifiedSignals.length > 0 && (
                    <div className="mt-6">
                      <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                        📊 Signal History
                      </h4>
                      <div className="space-y-2">
                        {verifiedSignals.slice(0, 3).map((signal) => (
                          <div 
                            key={signal.id}
                            className={`p-2 rounded-lg text-sm ${
                              signal.status === 'verified_correct' 
                                ? 'bg-green-50 text-green-700'
                                : 'bg-red-50 text-red-700'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              {signal.status === 'verified_correct' 
                                ? <Check className="w-4 h-4" />
                                : <X className="w-4 h-4" />
                              }
                              <span className="line-clamp-1">{signal.prediction}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Affected Indicators */}
              {indicators.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">
                    📈 AFFECTED INDICATORS
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {indicators.map((ind, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm text-gray-700"
                      >
                        {typeof ind === 'string' ? ind : ind.id || ind.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-4 flex items-center justify-end gap-3">
          <button
            onClick={handleDismiss}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Dismiss
          </button>
          <button
            onClick={handleArchive}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2"
          >
            <Archive className="w-4 h-4" />
            Archive
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-primary-600 text-white hover:bg-primary-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
