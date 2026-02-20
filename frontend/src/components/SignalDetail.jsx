import React from 'react';
import { X, TrendingUp, TrendingDown, Clock, Check, AlertTriangle, ExternalLink } from 'lucide-react';
import { formatDate, formatRelativeTime, formatNumber, safeParseJSON } from '../utils/format';

export default function SignalDetail({ signal, onClose }) {
  if (!signal) return null;

  const {
    id,
    prediction_text,
    target_indicator,
    direction,
    target_range,
    target_min,
    target_max,
    confidence,
    status,
    source_event_id,
    source_event_title,
    reasoning,
    expires_at,
    created_at,
    verified_at,
    actual_value,
    current_value,
    accuracy_note,
    theme_id,
    theme_name,
  } = signal;

  const getStatusConfig = () => {
    switch (status?.toLowerCase()) {
      case 'active':
        return { icon: <Clock className="w-5 h-5" />, color: 'bg-yellow-100 text-yellow-800 border-yellow-300', label: 'ACTIVE' };
      case 'verified_correct':
        return { icon: <Check className="w-5 h-5" />, color: 'bg-green-100 text-green-800 border-green-300', label: 'CORRECT' };
      case 'verified_wrong':
        return { icon: <X className="w-5 h-5" />, color: 'bg-red-100 text-red-800 border-red-300', label: 'WRONG' };
      case 'expired':
        return { icon: <Clock className="w-5 h-5" />, color: 'bg-gray-100 text-gray-600 border-gray-300', label: 'EXPIRED' };
      default:
        return { icon: <AlertTriangle className="w-5 h-5" />, color: 'bg-gray-100 text-gray-600 border-gray-300', label: status?.toUpperCase() };
    }
  };

  const getConfidenceConfig = () => {
    switch (confidence?.toLowerCase()) {
      case 'high':
        return { color: 'text-green-600 bg-green-50', icon: '🟢', label: 'High' };
      case 'medium':
        return { color: 'text-yellow-600 bg-yellow-50', icon: '🟡', label: 'Medium' };
      case 'low':
        return { color: 'text-red-600 bg-red-50', icon: '🔴', label: 'Low' };
      default:
        return { color: 'text-gray-600 bg-gray-50', icon: '⚪', label: confidence };
    }
  };

  const statusConfig = getStatusConfig();
  const confidenceConfig = getConfidenceConfig();

  // Calculate days until expiry
  const getDaysUntilExpiry = () => {
    if (!expires_at) return null;
    const now = new Date();
    const expiry = new Date(expires_at);
    const diffTime = expiry - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const daysLeft = getDaysUntilExpiry();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📡</span>
            <h2 className="text-xl font-semibold text-gray-900">Signal Detail</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status Badge */}
          <div className="flex items-center justify-between">
            <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${statusConfig.color} font-semibold`}>
              {statusConfig.icon}
              {statusConfig.label}
            </span>
            {status === 'active' && daysLeft !== null && (
              <span className="text-sm text-gray-500">
                {daysLeft > 0 ? `Expires in ${daysLeft} days` : 'Expired'}
              </span>
            )}
            {status !== 'active' && verified_at && (
              <span className="text-sm text-gray-500">
                Verified: {formatDate(verified_at, 'MMM d, yyyy')}
              </span>
            )}
          </div>

          {/* Prediction */}
          <div className="p-4 bg-gray-50 rounded-xl">
            <div className="flex items-start gap-3">
              <span className="text-2xl mt-1">
                {direction === 'up' ? '📈' : direction === 'down' ? '📉' : '📊'}
              </span>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{prediction_text}</h3>
                <p className="text-sm text-gray-500 mt-1">Created {formatRelativeTime(created_at)}</p>
              </div>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Target Indicator</h4>
              <p className="font-medium text-gray-900">{target_indicator}</p>
            </div>
            
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Direction</h4>
              <p className="font-medium text-gray-900 flex items-center gap-2">
                {direction === 'up' ? (
                  <><TrendingUp className="w-4 h-4 text-green-600" /> Increase</>
                ) : direction === 'down' ? (
                  <><TrendingDown className="w-4 h-4 text-red-600" /> Decrease</>
                ) : (
                  <>→ Stable</>
                )}
              </p>
            </div>
            
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Target Range</h4>
              <p className="font-medium text-gray-900">{target_range || `${target_min} - ${target_max}`}</p>
            </div>
            
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Confidence</h4>
              <p className={`font-medium inline-flex items-center gap-2 px-2 py-1 rounded ${confidenceConfig.color}`}>
                {confidenceConfig.icon} {confidenceConfig.label}
              </p>
            </div>
          </div>

          {/* Current vs Target Progress (for active) */}
          {status === 'active' && current_value && (
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="text-sm font-medium text-blue-800 mb-3">Current Progress</h4>
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-blue-700">Current: {formatNumber(current_value)}</span>
                <span className="text-blue-700">Target: {target_range || `${target_min} - ${target_max}`}</span>
              </div>
              <div className="h-3 bg-blue-200 rounded-full overflow-hidden">
                <div className="h-full bg-blue-600 rounded-full" style={{ width: '45%' }} />
              </div>
            </div>
          )}

          {/* Result (for verified) */}
          {(status === 'verified_correct' || status === 'verified_wrong') && (
            <div className={`p-4 rounded-lg ${status === 'verified_correct' ? 'bg-green-50' : 'bg-red-50'}`}>
              <h4 className={`text-sm font-medium mb-3 ${status === 'verified_correct' ? 'text-green-800' : 'text-red-800'}`}>
                Verification Result
              </h4>
              <div className="grid md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Target:</span>
                  <span className="ml-2 font-medium">{target_range}</span>
                </div>
                <div>
                  <span className="text-gray-500">Actual:</span>
                  <span className="ml-2 font-medium">{formatNumber(actual_value)}</span>
                </div>
                <div>
                  <span className={`font-medium ${status === 'verified_correct' ? 'text-green-700' : 'text-red-700'}`}>
                    {status === 'verified_correct' ? '✓ Within range' : '✗ Outside range'}
                  </span>
                </div>
              </div>
              {accuracy_note && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <span className="text-gray-600">📝 Note: {accuracy_note}</span>
                </div>
              )}
            </div>
          )}

          {/* Source Event */}
          {source_event_title && (
            <div className="p-4 bg-white border border-gray-200 rounded-lg">
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">📰 Source Event</h4>
              <p className="text-gray-900">{source_event_title}</p>
            </div>
          )}

          {/* Linked Theme */}
          {theme_name && (
            <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <h4 className="text-xs font-medium text-orange-600 uppercase mb-2">🔥 Linked Theme</h4>
              <p className="text-orange-800 font-medium">{theme_name}</p>
            </div>
          )}

          {/* Reasoning */}
          {reasoning && (
            <div className="p-4 bg-gray-50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-700 mb-2">💭 Reasoning</h4>
              <p className="text-gray-600 whitespace-pre-wrap">{reasoning}</p>
            </div>
          )}

          {/* Timestamps */}
          <div className="pt-4 border-t border-gray-200 flex items-center justify-between text-xs text-gray-400">
            <span>Created: {formatDate(created_at, 'MMM d, yyyy HH:mm')}</span>
            {expires_at && <span>Expires: {formatDate(expires_at, 'MMM d, yyyy')}</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
