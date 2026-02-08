import React, { useState } from 'react';
import { 
  Eye, Bell, AlertTriangle, Calendar, Type, BarChart2,
  ChevronDown, ChevronUp, Plus, Edit2, Trash2, Clock,
  Check, XCircle, RotateCcw
} from 'lucide-react';
import { formatDate, formatRelativeTime, formatNumber, safeParseJSON } from '../utils/format';

// ============================================================
// Progress Bar Component
// ============================================================
function ProgressBar({ current, target, threshold, label }) {
  // Calculate position as percentage
  const min = Math.min(current, target) * 0.9;
  const max = Math.max(current, target) * 1.1;
  const range = max - min;
  
  const currentPos = ((current - min) / range) * 100;
  const targetPos = ((target - min) / range) * 100;
  
  return (
    <div className="mt-2">
      <div className="relative h-2 bg-gray-200 rounded-full">
        <div 
          className="absolute top-0 left-0 h-full bg-primary-500 rounded-full"
          style={{ width: `${Math.min(currentPos, 100)}%` }}
        />
        <div 
          className="absolute top-0 h-full w-0.5 bg-red-500"
          style={{ left: `${Math.min(targetPos, 100)}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
        <span>{formatNumber(min)}</span>
        <span className="text-primary-600 font-medium">Current: {formatNumber(current)}</span>
        <span className="text-red-600">⚠️ {formatNumber(target)}</span>
      </div>
    </div>
  );
}

// ============================================================
// Countdown Component
// ============================================================
function Countdown({ targetDate }) {
  const now = new Date();
  const target = new Date(targetDate);
  const diffTime = target - now;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  const percentage = diffDays > 0 ? Math.max(0, ((365 - diffDays) / 365) * 100) : 100;
  
  return (
    <div className="mt-2">
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all ${diffDays < 30 ? 'bg-red-500' : diffDays < 90 ? 'bg-yellow-500' : 'bg-green-500'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-center mt-1 text-xs font-medium text-gray-600">
        {diffDays > 0 ? `${diffDays} days remaining` : 'Expired'}
      </div>
    </div>
  );
}

// ============================================================
// Triggered Watchlist Card
// ============================================================
function TriggeredCard({ item, onDismiss, onSnooze, onViewTheme }) {
  const {
    id,
    name,
    watch_type,
    condition,
    current_value,
    triggered_at,
    related_theme,
    trigger_details,
  } = item;

  const getTypeIcon = () => {
    switch (watch_type?.toLowerCase()) {
      case 'indicator': return <BarChart2 className="w-4 h-4" />;
      case 'date': return <Calendar className="w-4 h-4" />;
      case 'keyword': return <Type className="w-4 h-4" />;
      default: return <Eye className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-white rounded-xl border-2 border-yellow-400 shadow-sm overflow-hidden">
      {/* Alert Header */}
      <div className="bg-yellow-50 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-yellow-600" />
          <span className="font-semibold text-yellow-800">TRIGGERED</span>
          <span className="text-sm text-yellow-600">{formatDate(triggered_at, 'MMM d, HH:mm')}</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="p-2 bg-gray-100 rounded-lg text-gray-600">
            {getTypeIcon()}
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-gray-900">{name}</h4>
            <div className="text-sm text-gray-600 mt-1">
              <span className="font-medium">Type:</span> {watch_type} │ 
              <span className="font-medium ml-2">Condition:</span> {condition}
            </div>
            {current_value && (
              <div className="text-sm text-gray-600 mt-1">
                <span className="font-medium">Current Value:</span> {formatNumber(current_value)}
              </div>
            )}
          </div>
        </div>

        {/* Related Theme */}
        {related_theme && (
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
            <span>🔗</span>
            <span>Related Theme: {related_theme}</span>
          </div>
        )}

        {/* Trigger Details */}
        {trigger_details && (
          <div className="flex items-start gap-2 text-sm text-gray-600 mb-3">
            <span>📰</span>
            <span>Triggered by: {trigger_details}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-100">
          <button
            onClick={() => onDismiss?.(id)}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          >
            Dismiss
          </button>
          <button
            onClick={() => onSnooze?.(id, 7)}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          >
            Snooze 7 days
          </button>
          {related_theme && (
            <button
              onClick={() => onViewTheme?.(related_theme)}
              className="px-3 py-1.5 text-sm bg-orange-100 hover:bg-orange-200 text-orange-700 rounded-lg transition-colors"
            >
              View Theme
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Active Watchlist Card
// ============================================================
function WatchingCard({ item, onEdit, onDelete }) {
  const {
    id,
    name,
    watch_type,
    condition,
    target_value,
    current_value,
    target_date,
    keywords,
    source,
    related_indicators,
    linked_template,
    expected_impact,
    last_checked,
    created_at,
  } = item;

  const indicators = safeParseJSON(related_indicators, []);
  const impacts = safeParseJSON(expected_impact, []);

  const getTypeIcon = () => {
    switch (watch_type?.toLowerCase()) {
      case 'indicator': return <BarChart2 className="w-5 h-5 text-blue-600" />;
      case 'date': return <Calendar className="w-5 h-5 text-purple-600" />;
      case 'keyword': return <Type className="w-5 h-5 text-green-600" />;
      default: return <Eye className="w-5 h-5 text-gray-600" />;
    }
  };

  const getTypeBadge = () => {
    switch (watch_type?.toLowerCase()) {
      case 'indicator': return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">Indicator</span>;
      case 'date': return <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">Date</span>;
      case 'keyword': return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">Keyword</span>;
      default: return null;
    }
  };

  // Calculate distance from trigger for indicator type
  const getDistanceFromTrigger = () => {
    if (watch_type !== 'indicator' || !current_value || !target_value) return null;
    const diff = ((target_value - current_value) / current_value) * 100;
    return Math.abs(diff).toFixed(1);
  };

  const distancePercent = getDistanceFromTrigger();

  return (
    <div className="bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-sm transition-all overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getTypeIcon()}
          <h4 className="font-semibold text-gray-900">{name}</h4>
        </div>
        <div className="flex items-center gap-2">
          {getTypeBadge()}
          {target_date && (
            <span className="text-xs text-gray-500">Due: {formatDate(target_date, 'MMM d')}</span>
          )}
          <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">Active</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Type and Condition */}
        <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
          <span><span className="font-medium">Type:</span> {watch_type}</span>
          {source && <span>│ <span className="font-medium">Source:</span> {source}</span>}
        </div>

        {/* Condition */}
        {condition && (
          <div className="text-sm text-gray-600 mb-3">
            <span className="font-medium">Condition:</span> {condition}
          </div>
        )}

        {/* Keywords */}
        {keywords && watch_type === 'keyword' && (
          <div className="mb-3">
            <div className="text-sm text-gray-600 mb-1 font-medium">Keywords:</div>
            <div className="flex flex-wrap gap-2">
              {(Array.isArray(keywords) ? keywords : keywords.split(',')).map((kw, idx) => (
                <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                  "{kw.trim()}"
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Expected Impact */}
        {impacts.length > 0 && (
          <div className="mb-3">
            <div className="text-sm text-gray-600 mb-1 font-medium">Expected Impact:</div>
            <ul className="space-y-1">
              {impacts.map((impact, idx) => (
                <li key={idx} className="text-sm text-gray-600 flex items-start gap-1">
                  <span>•</span> {impact}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Linked Template */}
        {linked_template && (
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
            🔗 <span className="font-medium">Linked Template:</span> {linked_template}
          </div>
        )}

        {/* Related Indicators */}
        {indicators.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
            📊 <span className="font-medium">Monitor:</span> {indicators.join(', ')}
          </div>
        )}

        {/* Date Watch - Countdown */}
        {watch_type === 'date' && target_date && (
          <Countdown targetDate={target_date} />
        )}

        {/* Indicator Watch - Progress */}
        {watch_type === 'indicator' && current_value && target_value && (
          <div className="mb-3">
            <ProgressBar 
              current={current_value} 
              target={target_value}
              label={`${distancePercent}% away from trigger`}
            />
          </div>
        )}

        {/* Last Checked */}
        {last_checked && (
          <div className="text-xs text-gray-400 mt-2">
            📈 Last checked: {formatDate(last_checked, 'MMM d, HH:mm')}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="px-4 py-2 bg-gray-50 flex items-center justify-end gap-2">
        <button
          onClick={() => onEdit?.(item)}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded transition-colors"
        >
          <Edit2 className="w-4 h-4" />
        </button>
        <button
          onClick={() => onDelete?.(id)}
          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================
// Dismissed Row
// ============================================================
function DismissedRow({ item, onRestore }) {
  const { id, name, dismissed_at } = item;

  return (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded-lg">
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <span>▸</span>
        <span>{name}</span>
        <span className="text-gray-400">(dismissed {formatDate(dismissed_at, 'MMM d')})</span>
      </div>
      <button
        onClick={() => onRestore?.(id)}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-primary-600 px-2 py-1 rounded hover:bg-gray-100"
      >
        <RotateCcw className="w-3 h-3" />
        Restore
      </button>
    </div>
  );
}

// ============================================================
// Main WatchlistPanel Component
// ============================================================
export default function WatchlistPanel({
  items = [],
  onAddNew,
  onEdit,
  onDelete,
  onDismiss,
  onSnooze,
  onRestore,
  onViewTheme,
  loading = false,
}) {
  const [expandedSections, setExpandedSections] = useState({
    triggered: true,
    watching: true,
    dismissed: false,
  });

  // Categorize items by status
  const triggeredItems = items.filter(i => i.status?.toLowerCase() === 'triggered');
  const watchingItems = items.filter(i => i.status?.toLowerCase() === 'active' || i.status?.toLowerCase() === 'watching');
  const dismissedItems = items.filter(i => i.status?.toLowerCase() === 'dismissed');

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          👁️ Watchlist
        </h2>
        <button
          onClick={onAddNew}
          className="flex items-center gap-2 px-3 py-1.5 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add New Watch
        </button>
      </div>

      {/* Triggered Section */}
      {triggeredItems.length > 0 && (
        <div className="bg-yellow-50/50 rounded-xl p-4">
          <button
            onClick={() => toggleSection('triggered')}
            className="flex items-center justify-between w-full text-left"
          >
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <Bell className="w-5 h-5 text-yellow-600" />
              Triggered
              <span className="text-xs text-gray-500">(needs attention)</span>
              <span className="px-2 py-0.5 bg-yellow-200 text-yellow-800 rounded-full text-xs ml-2 font-bold">
                {triggeredItems.length}
              </span>
            </h3>
            {expandedSections.triggered ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>
          
          {expandedSections.triggered && (
            <div className="mt-4 space-y-4">
              {triggeredItems.map(item => (
                <TriggeredCard 
                  key={item.id} 
                  item={item} 
                  onDismiss={onDismiss}
                  onSnooze={onSnooze}
                  onViewTheme={onViewTheme}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Watching Section */}
      <div className="bg-gray-50 rounded-xl p-4">
        <button
          onClick={() => toggleSection('watching')}
          className="flex items-center justify-between w-full text-left"
        >
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <Eye className="w-5 h-5 text-primary-600" />
            Watching
            <span className="text-xs text-gray-500">(active monitors)</span>
            <span className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded-full text-xs ml-2">
              {watchingItems.length}
            </span>
          </h3>
          {expandedSections.watching ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        
        {expandedSections.watching && (
          <div className="mt-4 space-y-4">
            {watchingItems.length > 0 ? (
              watchingItems.map(item => (
                <WatchingCard 
                  key={item.id} 
                  item={item}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              ))
            ) : (
              <div className="text-center py-6 text-gray-500 text-sm">
                No active watchlist items. Click "Add New Watch" to create one.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Dismissed Section */}
      {dismissedItems.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4">
          <button
            onClick={() => toggleSection('dismissed')}
            className="flex items-center justify-between w-full text-left"
          >
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <Check className="w-5 h-5 text-gray-400" />
              Recently Dismissed
              <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded-full text-xs ml-2">
                {dismissedItems.length}
              </span>
            </h3>
            {expandedSections.dismissed ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>
          
          {expandedSections.dismissed && (
            <div className="mt-3">
              {dismissedItems.map(item => (
                <DismissedRow 
                  key={item.id} 
                  item={item}
                  onRestore={onRestore}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
