import React from 'react';
import { X, Flame, TrendingUp, TrendingDown, Calendar, ExternalLink, Bell, Archive } from 'lucide-react';
import { formatDate, formatRelativeTime, formatNumber, safeParseJSON } from '../utils/format';

export default function ThemeDetail({ theme, onClose, onViewEvent, onViewSignal }) {
  if (!theme) return null;

  const {
    id,
    name,
    name_vi,
    description,
    status,
    strength,
    peak_strength,
    related_indicators,
    related_events,
    related_signals,
    first_seen,
    last_updated,
    event_count,
    category,
  } = theme;

  const indicators = safeParseJSON(related_indicators, []);
  const events = safeParseJSON(related_events, []);
  const signals = safeParseJSON(related_signals, []);

  const getStatusConfig = () => {
    switch (status?.toLowerCase()) {
      case 'active':
        return { color: 'bg-green-100 text-green-800 border-green-300', icon: '🟢', label: 'ACTIVE' };
      case 'emerging':
        return { color: 'bg-blue-100 text-blue-800 border-blue-300', icon: '🌱', label: 'EMERGING' };
      case 'fading':
        return { color: 'bg-gray-100 text-gray-600 border-gray-300', icon: '📉', label: 'FADING' };
      case 'archived':
        return { color: 'bg-gray-100 text-gray-500 border-gray-300', icon: '📦', label: 'ARCHIVED' };
      default:
        return { color: 'bg-gray-100 text-gray-600 border-gray-300', icon: '⚪', label: status?.toUpperCase() };
    }
  };

  const statusConfig = getStatusConfig();

  // Calculate strength percentage for progress bar (max 10)
  const strengthPercent = Math.min((strength || 0) / 10 * 100, 100);
  const peakPercent = Math.min((peak_strength || 0) / 10 * 100, 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-orange-500 to-red-500 px-6 py-4 flex items-center justify-between rounded-t-xl">
          <div className="flex items-center gap-3 text-white">
            <Flame className="w-7 h-7" />
            <h2 className="text-xl font-semibold">Theme Detail</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Title and Status */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-2xl font-bold text-gray-900">{name_vi || name}</h3>
              {name_vi && name && name !== name_vi && (
                <p className="text-gray-500 mt-1">{name}</p>
              )}
            </div>
            <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border font-medium ${statusConfig.color}`}>
              {statusConfig.icon} {statusConfig.label}
            </span>
          </div>

          {/* Description */}
          {description && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-gray-700">{description}</p>
            </div>
          )}

          {/* Strength Meter */}
          <div className="p-4 bg-orange-50 rounded-xl">
            <h4 className="text-sm font-medium text-orange-800 mb-3">📊 Theme Strength</h4>
            <div className="space-y-3">
              {/* Current Strength */}
              <div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-600">Current Strength</span>
                  <span className="font-bold text-orange-600">{strength?.toFixed(1) || 0}</span>
                </div>
                <div className="h-4 bg-orange-200 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all ${
                      strength >= 5 ? 'bg-orange-500' : strength >= 2 ? 'bg-yellow-400' : 'bg-gray-400'
                    }`}
                    style={{ width: `${strengthPercent}%` }}
                  />
                </div>
              </div>
              
              {/* Peak Strength */}
              {peak_strength && peak_strength !== strength && (
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-600">Peak Strength</span>
                    <span className="font-medium text-gray-500">{peak_strength?.toFixed(1)}</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gray-400 rounded-full"
                      style={{ width: `${peakPercent}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Legend */}
              <div className="flex items-center gap-4 text-xs text-gray-500 pt-2">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-gray-400"></span> Fading (&lt;2)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-yellow-400"></span> Emerging (2-5)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-orange-500"></span> Active (≥5)
                </span>
              </div>
            </div>
          </div>

          {/* Related Indicators */}
          {indicators.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">📊 Related Indicators</h4>
              <div className="flex flex-wrap gap-2">
                {indicators.map((ind, idx) => (
                  <div 
                    key={idx} 
                    className="px-3 py-2 bg-white border border-gray-200 rounded-lg flex items-center gap-2"
                  >
                    <span className="font-medium text-gray-800">{ind.name || ind.id || ind}</span>
                    {ind.value && (
                      <span className={`text-sm ${
                        ind.trend === 'up' ? 'text-green-600' : 
                        ind.trend === 'down' ? 'text-red-600' : 'text-gray-500'
                      }`}>
                        {formatNumber(ind.value)}
                        {ind.trend === 'up' && <TrendingUp className="w-3 h-3 inline ml-1" />}
                        {ind.trend === 'down' && <TrendingDown className="w-3 h-3 inline ml-1" />}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related Events */}
          {events.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">📰 Related Events ({event_count || events.length})</h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {events.map((evt, idx) => (
                  <div 
                    key={idx} 
                    className="p-3 bg-white border border-gray-200 rounded-lg hover:border-primary-300 cursor-pointer transition-colors"
                    onClick={() => onViewEvent?.(evt)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 line-clamp-1">{evt.title}</p>
                        <p className="text-xs text-gray-500 mt-1">{formatDate(evt.date || evt.published_at, 'MMM d, yyyy')}</p>
                      </div>
                      {evt.score && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {evt.score}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related Signals */}
          {signals.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">📡 Related Signals ({signals.length})</h4>
              <div className="space-y-2">
                {signals.map((sig, idx) => (
                  <div 
                    key={idx} 
                    className="p-3 bg-purple-50 border border-purple-200 rounded-lg hover:border-purple-400 cursor-pointer transition-colors"
                    onClick={() => onViewSignal?.(sig)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-purple-900">{sig.prediction_text || sig.target}</p>
                        <p className="text-xs text-purple-600 mt-1">
                          {sig.target_indicator || sig.target} • {sig.confidence}
                        </p>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        sig.status === 'active' ? 'bg-yellow-100 text-yellow-700' :
                        sig.status === 'verified_correct' ? 'bg-green-100 text-green-700' :
                        sig.status === 'verified_wrong' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {sig.status === 'active' ? 'Active' : 
                         sig.status === 'verified_correct' ? 'Correct' :
                         sig.status === 'verified_wrong' ? 'Wrong' : sig.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timeline Info */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <Calendar className="w-4 h-4" />
                First Seen
              </div>
              <p className="font-medium text-gray-900">{formatDate(first_seen, 'MMM d, yyyy')}</p>
            </div>
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
                <Calendar className="w-4 h-4" />
                Last Updated
              </div>
              <p className="font-medium text-gray-900">{formatDate(last_updated, 'MMM d, yyyy')}</p>
              <p className="text-xs text-gray-400 mt-1">{formatRelativeTime(last_updated)}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-4 border-t border-gray-200">
            <button className="flex items-center gap-2 px-4 py-2 bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 transition-colors">
              <Bell className="w-4 h-4" />
              Set Alert
            </button>
            {status !== 'archived' && (
              <button className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
                <Archive className="w-4 h-4" />
                Archive Theme
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
