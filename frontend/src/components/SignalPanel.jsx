import React, { useState } from 'react';
import { 
  TrendingUp, TrendingDown, Clock, Check, X, 
  ChevronDown, ChevronUp, ExternalLink, Filter,
  Calendar
} from 'lucide-react';
import { formatDate, formatRelativeTime, formatNumber, formatPercent, safeParseJSON } from '../utils/format';
import { AccuracyTrendChart } from './charts';

// ============================================================
// Signal Card Component
// ============================================================
function SignalCard({ signal, onClick }) {
  const {
    id,
    prediction_text,
    target_indicator,
    direction,
    target_range,
    confidence,
    status,
    source_event_title,
    reasoning,
    expires_at,
    verified_at,
    actual_value,
    current_value,
  } = signal;

  const getStatusConfig = () => {
    switch (status?.toLowerCase()) {
      case 'pending':
        return { icon: <Clock className="w-4 h-4" />, color: 'bg-yellow-100 text-yellow-800', label: 'PENDING' };
      case 'correct':
        return { icon: <Check className="w-4 h-4" />, color: 'bg-green-100 text-green-800', label: 'CORRECT' };
      case 'wrong':
        return { icon: <X className="w-4 h-4" />, color: 'bg-red-100 text-red-800', label: 'WRONG' };
      case 'expired':
        return { icon: <Clock className="w-4 h-4" />, color: 'bg-gray-100 text-gray-600', label: 'EXPIRED' };
      default:
        return { icon: <Clock className="w-4 h-4" />, color: 'bg-gray-100 text-gray-600', label: status?.toUpperCase() };
    }
  };

  const getConfidenceConfig = () => {
    switch (confidence?.toLowerCase()) {
      case 'high':
        return { color: 'text-green-600', icon: '🟢', label: 'High' };
      case 'medium':
        return { color: 'text-yellow-600', icon: '🟡', label: 'Medium' };
      case 'low':
        return { color: 'text-red-600', icon: '🔴', label: 'Low' };
      default:
        return { color: 'text-gray-600', icon: '⚪', label: confidence };
    }
  };

  const getDirectionIcon = () => {
    if (direction === 'up') return <TrendingUp className="w-4 h-4 text-green-600" />;
    if (direction === 'down') return <TrendingDown className="w-4 h-4 text-red-600" />;
    return <span className="text-gray-500">→</span>;
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
    <div
      onClick={() => onClick?.(signal)}
      className="bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md cursor-pointer transition-all overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
        <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${statusConfig.color}`}>
          {statusConfig.icon}
          {statusConfig.label}
        </span>
        {status === 'pending' && daysLeft !== null && (
          <span className="text-xs text-gray-500">
            Expires: {daysLeft} {daysLeft === 1 ? 'day' : 'days'}
          </span>
        )}
        {status !== 'pending' && verified_at && (
          <span className="text-xs text-gray-500">
            Verified: {formatDate(verified_at, 'MMM d')}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Prediction Text */}
        <div className="flex items-start gap-2 mb-3">
          <span className="text-lg">
            {direction === 'up' ? '📈' : direction === 'down' ? '📉' : '📊'}
          </span>
          <h4 className="text-base font-medium text-gray-900">
            {prediction_text}
          </h4>
        </div>

        {/* Meta Info */}
        <div className="flex flex-wrap items-center gap-3 text-sm mb-4">
          <span className="flex items-center gap-1 text-gray-600">
            <span className="font-medium">Target:</span> {target_indicator}
          </span>
          <span className="text-gray-300">│</span>
          <span className="flex items-center gap-1 text-gray-600">
            <span className="font-medium">Direction:</span>
            {getDirectionIcon()}
            <span className="capitalize">{direction}</span>
          </span>
          <span className="text-gray-300">│</span>
          <span className="flex items-center gap-1">
            <span className="font-medium">Confidence:</span>
            <span className={confidenceConfig.color}>
              {confidenceConfig.icon} {confidenceConfig.label}
            </span>
          </span>
        </div>

        {/* Progress Bar for Pending Signals */}
        {status === 'pending' && current_value && target_range && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between text-xs text-gray-600 mb-2">
              <span>Current: {formatNumber(current_value)}</span>
              <span>Target: {target_range}</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{ width: '45%' }}
              />
            </div>
          </div>
        )}

        {/* Result for Verified Signals */}
        {(status === 'correct' || status === 'wrong') && (
          <div className={`mb-3 p-3 rounded-lg ${status === 'correct' ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Target: {target_range}</span>
              <span className="text-gray-600">Actual: {formatNumber(actual_value)}</span>
              <span className={`font-medium ${status === 'correct' ? 'text-green-700' : 'text-red-700'}`}>
                {status === 'correct' ? '✓ Within range' : '✗ Outside range'}
              </span>
            </div>
          </div>
        )}

        {/* Source Event */}
        {source_event_title && (
          <div className="flex items-start gap-2 text-sm text-gray-500">
            <span>📰</span>
            <span className="line-clamp-1">Source: {source_event_title}</span>
          </div>
        )}

        {/* Reasoning */}
        {reasoning && (
          <div className="flex items-start gap-2 text-sm text-gray-500 mt-2">
            <span>💭</span>
            <span className="line-clamp-2">{reasoning}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Accuracy Stats Component
// ============================================================
function AccuracyStats({ stats }) {
  const { 
    total_signals = 0,
    correct_signals = 0,
    wrong_signals = 0,
    accuracy_rate = 0,
    by_confidence = {},
    by_indicator = {},
    trend_data = [],
  } = stats || {};

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h4 className="text-sm font-semibold text-gray-700 mb-4">📊 Accuracy Stats</h4>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* By Confidence */}
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase mb-3">By Confidence</h5>
          <div className="space-y-2">
            {Object.entries(by_confidence).map(([level, data]) => (
              <div key={level} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  {level === 'high' ? '🟢' : level === 'medium' ? '🟡' : '🔴'}
                  <span className="capitalize">{level}:</span>
                </span>
                <span className="font-medium">
                  {data.accuracy}% ({data.correct}/{data.total})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* By Indicator */}
        <div>
          <h5 className="text-xs font-medium text-gray-500 uppercase mb-3">By Indicator</h5>
          <div className="space-y-2">
            {Object.entries(by_indicator).slice(0, 5).map(([indicator, data]) => (
              <div key={indicator} className="flex items-center justify-between text-sm">
                <span className="text-gray-600 truncate max-w-[150px]">{indicator}:</span>
                <span className="font-medium">
                  {data.accuracy}% ({data.correct}/{data.total})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Overall Accuracy */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Overall Accuracy:</span>
          <span className="text-xl font-bold text-primary-600">
            {accuracy_rate}% ({correct_signals}/{total_signals})
          </span>
        </div>
      </div>

      {/* Accuracy Trend Chart */}
      <div className="mt-6 pt-4 border-t border-gray-100">
        <AccuracyTrendChart data={trend_data} />
      </div>
    </div>
  );
}

// ============================================================
// Main SignalPanel Component
// ============================================================
export default function SignalPanel({ 
  signals = [], 
  accuracyStats = null,
  onSelectSignal,
  loading = false 
}) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [confidenceFilter, setConfidenceFilter] = useState('all');
  const [indicatorFilter, setIndicatorFilter] = useState('all');
  const [periodFilter, setPeriodFilter] = useState('30');
  const [showFilters, setShowFilters] = useState(false);
  const [expandedSection, setExpandedSection] = useState({
    active: true,
    results: true,
    stats: true,
  });

  // Get unique indicators from signals
  const uniqueIndicators = [...new Set(signals.map(s => s.target_indicator).filter(Boolean))];

  // Filter signals by period (days)
  const filterByPeriod = (signal) => {
    if (periodFilter === 'all') return true;
    const days = parseInt(periodFilter);
    const createdAt = new Date(signal.created_at);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    return createdAt >= cutoff;
  };

  // Filter signals
  const filteredSignals = signals.filter(signal => {
    if (statusFilter !== 'all' && signal.status?.toLowerCase() !== statusFilter) return false;
    if (confidenceFilter !== 'all' && signal.confidence?.toLowerCase() !== confidenceFilter) return false;
    if (indicatorFilter !== 'all' && signal.target_indicator !== indicatorFilter) return false;
    if (!filterByPeriod(signal)) return false;
    return true;
  });

  // Separate active and verified signals
  const activeSignals = filteredSignals.filter(s => s.status?.toLowerCase() === 'pending');
  const verifiedSignals = filteredSignals.filter(s => ['correct', 'wrong'].includes(s.status?.toLowerCase()));

  // Calculate overall accuracy
  const totalVerified = signals.filter(s => ['correct', 'wrong'].includes(s.status?.toLowerCase())).length;
  const totalCorrect = signals.filter(s => s.status?.toLowerCase() === 'correct').length;
  const overallAccuracy = totalVerified > 0 ? Math.round((totalCorrect / totalVerified) * 100) : 0;

  const toggleSection = (section) => {
    setExpandedSection(prev => ({ ...prev, [section]: !prev[section] }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Accuracy */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          📡 Signals
        </h2>
        <div className="text-sm font-medium text-gray-600">
          Accuracy: <span className="text-primary-600 font-bold">{overallAccuracy}%</span> 
          <span className="text-gray-400 ml-1">({totalCorrect}/{totalVerified})</span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-3">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
        >
          <Filter className="w-4 h-4" />
          Filters
          {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        
        {showFilters && (
          <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-gray-100">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All</option>
                <option value="pending">Pending</option>
                <option value="correct">Correct</option>
                <option value="wrong">Wrong</option>
                <option value="expired">Expired</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Confidence</label>
              <select
                value={confidenceFilter}
                onChange={(e) => setConfidenceFilter(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Indicator</label>
              <select
                value={indicatorFilter}
                onChange={(e) => setIndicatorFilter(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="all">All</option>
                {uniqueIndicators.map(ind => (
                  <option key={ind} value={ind}>{ind}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Period</label>
              <select
                value={periodFilter}
                onChange={(e) => setPeriodFilter(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="7">Last 7 days</option>
                <option value="30">Last 30 days</option>
                <option value="90">Last 90 days</option>
                <option value="all">All time</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Active Signals Section */}
      <div className="bg-gray-50 rounded-xl p-4">
        <button
          onClick={() => toggleSection('active')}
          className="flex items-center justify-between w-full text-left"
        >
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            🎯 Active Signals
            <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded-full text-xs">
              {activeSignals.length}
            </span>
          </h3>
          {expandedSection.active ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        
        {expandedSection.active && (
          <div className="mt-4 space-y-3">
            {activeSignals.length > 0 ? (
              activeSignals.map(signal => (
                <SignalCard key={signal.id} signal={signal} onClick={onSelectSignal} />
              ))
            ) : (
              <div className="text-center py-6 text-gray-500 text-sm">
                No active signals
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Results Section */}
      <div className="bg-gray-50 rounded-xl p-4">
        <button
          onClick={() => toggleSection('results')}
          className="flex items-center justify-between w-full text-left"
        >
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            📋 Recent Results
            <span className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded-full text-xs">
              {verifiedSignals.length}
            </span>
          </h3>
          {expandedSection.results ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        
        {expandedSection.results && (
          <div className="mt-4 space-y-3">
            {verifiedSignals.length > 0 ? (
              verifiedSignals.slice(0, 5).map(signal => (
                <SignalCard key={signal.id} signal={signal} onClick={onSelectSignal} />
              ))
            ) : (
              <div className="text-center py-6 text-gray-500 text-sm">
                No verified signals yet
              </div>
            )}
          </div>
        )}
      </div>

      {/* Accuracy Stats Section */}
      {accuracyStats && (
        <div>
          <button
            onClick={() => toggleSection('stats')}
            className="flex items-center justify-between w-full text-left mb-3"
          >
            <h3 className="font-semibold text-gray-800">📊 Accuracy Stats</h3>
            {expandedSection.stats ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>
          
          {expandedSection.stats && <AccuracyStats stats={accuracyStats} />}
        </div>
      )}
    </div>
  );
}
