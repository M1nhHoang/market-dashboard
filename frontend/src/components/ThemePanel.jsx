import React, { useState } from 'react';
import { 
  Flame, TrendingUp, TrendingDown, ChevronDown, ChevronUp, 
  ExternalLink, Bell, Archive, Zap
} from 'lucide-react';
import { formatDate, formatRelativeTime, formatNumber, safeParseJSON } from '../utils/format';
import { StrengthTimelineChart } from './charts';

// ============================================================
// Strength Bar Component
// ============================================================
function StrengthBar({ strength, peak, maxStrength = 10 }) {
  const percentage = (strength / maxStrength) * 100;
  
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-3 bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all ${
            strength >= 5 ? 'bg-orange-500' : strength >= 2 ? 'bg-yellow-400' : 'bg-gray-400'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-sm font-medium text-gray-700 min-w-[80px]">
        {strength.toFixed(1)} {peak && <span className="text-gray-400">(Peak: {peak.toFixed(1)})</span>}
      </span>
    </div>
  );
}

// ============================================================
// Theme Card - Full/Active
// ============================================================
function ActiveThemeCard({ theme, onClick }) {
  const {
    id,
    name,
    name_vi,
    status,
    strength,
    peak_strength,
    related_indicators,
    related_events,
    related_signals,
    strength_history,
    first_seen,
    last_updated,
    event_count,
  } = theme;

  const indicators = safeParseJSON(related_indicators, []);
  const events = safeParseJSON(related_events, []);
  const signals = safeParseJSON(related_signals, []);
  const historyData = safeParseJSON(strength_history, []);

  const getStatusBadge = () => {
    switch (status?.toLowerCase()) {
      case 'active':
        return <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">🟢 ACTIVE</span>;
      case 'emerging':
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">🌱 EMERGING</span>;
      case 'fading':
        return <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">📉 FADING</span>;
      case 'archived':
        return <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs font-medium"><Archive className="w-3 h-3 inline" /> ARCHIVED</span>;
      default:
        return null;
    }
  };

  return (
    <div
      onClick={() => onClick?.(theme)}
      className="bg-white rounded-xl border border-gray-200 hover:border-orange-300 hover:shadow-md cursor-pointer transition-all overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <Flame className={`w-5 h-5 ${strength >= 5 ? 'text-orange-500' : 'text-gray-400'}`} />
            <h3 className="font-semibold text-gray-900">{name_vi || name}</h3>
          </div>
          {getStatusBadge()}
        </div>
        
        <StrengthBar strength={strength || 0} peak={peak_strength} />
      </div>

      {/* Related Indicators */}
      {indicators.length > 0 && (
        <div className="px-4 py-3 border-b border-gray-50">
          <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">📊 Related Indicators</h4>
          <div className="flex flex-wrap gap-2">
            {indicators.slice(0, 4).map((ind, idx) => (
              <div key={idx} className="px-3 py-1.5 bg-gray-50 rounded-lg text-sm">
                <span className="font-medium text-gray-700">{ind.name || ind.id}</span>
                {ind.value && (
                  <span className={`ml-2 ${ind.trend === 'up' ? 'text-green-600' : ind.trend === 'down' ? 'text-red-600' : 'text-gray-500'}`}>
                    {formatNumber(ind.value)} {ind.trend === 'up' ? '↑' : ind.trend === 'down' ? '↓' : ''}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Events and Signals Summary */}
      <div className="px-4 py-3 grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">📰 Related Events ({event_count || events.length})</h4>
          <div className="space-y-1">
            {events.slice(0, 3).map((evt, idx) => (
              <div key={idx} className="text-sm text-gray-600 truncate">
                ├─ {formatDate(evt.date, 'MMM d')}: {evt.title}
              </div>
            ))}
            {events.length > 3 && (
              <div className="text-xs text-gray-400">
                └─ [+{events.length - 3} more]
              </div>
            )}
          </div>
        </div>
        
        {signals.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">📡 Signals ({signals.length})</h4>
            <div className="space-y-1">
              {signals.slice(0, 2).map((sig, idx) => (
                <div key={idx} className="text-sm text-gray-600 truncate">
                  ├─ {sig.target} → {sig.direction} ({sig.days_left}d)
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Strength Timeline Chart */}
      <div className="px-4 py-3 border-t border-gray-50">
        <StrengthTimelineChart data={historyData} maxStrength={10} />
      </div>

      {/* Footer Actions */}
      <div className="px-4 py-3 bg-gray-50 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          First seen: {formatDate(first_seen, 'MMM d')}
        </span>
        <div className="flex items-center gap-2">
          <button className="px-2 py-1 text-xs text-gray-600 hover:text-primary-600 hover:bg-white rounded transition-colors">
            View All Events
          </button>
          <button className="px-2 py-1 text-xs text-gray-600 hover:text-primary-600 hover:bg-white rounded transition-colors">
            <Bell className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Theme Card - Compact/Emerging
// ============================================================
function EmergingThemeCard({ theme, onClick }) {
  const { id, name, name_vi, strength, event_count, first_seen, status, related_indicators } = theme;
  const indicators = safeParseJSON(related_indicators, []);

  return (
    <div
      onClick={() => onClick?.(theme)}
      className="bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm cursor-pointer transition-all p-4"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🌱</span>
          <h4 className="font-medium text-gray-900">{name_vi || name}</h4>
        </div>
        <span className="text-sm font-medium text-blue-600">
          Strength: {strength?.toFixed(1)}
        </span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span>Events: {event_count}</span>
        <span>│</span>
        <span>First seen: {formatDate(first_seen, 'MMM d')}</span>
        <span>│</span>
        <span>Status: {status}</span>
      </div>
      {indicators.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          Related: {indicators.slice(0, 3).map(i => i.id || i).join(', ')}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Fading Theme Row
// ============================================================
function FadingThemeRow({ theme, onArchive, onRestore }) {
  const { id, name, name_vi, strength, last_updated } = theme;

  return (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-gray-50 rounded-lg">
      <div className="flex items-center gap-2">
        <span className="text-gray-400">▸</span>
        <span className="text-sm text-gray-600">{name_vi || name}</span>
        <span className="text-xs text-gray-400">
          (strength: {strength?.toFixed(1)}, fading since {formatDate(last_updated, 'MMM d')})
        </span>
      </div>
      <button 
        onClick={(e) => { e.stopPropagation(); onArchive?.(id); }}
        className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
      >
        Archive
      </button>
    </div>
  );
}

// ============================================================
// Main ThemePanel Component
// ============================================================
export default function ThemePanel({
  themes = [],
  onSelectTheme,
  onArchiveTheme,
  loading = false,
}) {
  const [expandedSections, setExpandedSections] = useState({
    active: true,
    emerging: true,
    fading: false,
  });

  // Categorize themes by status
  const activeThemes = themes.filter(t => t.status?.toLowerCase() === 'active' || (t.strength >= 5));
  const emergingThemes = themes.filter(t => t.status?.toLowerCase() === 'emerging' || (t.strength >= 2 && t.strength < 5));
  const fadingThemes = themes.filter(t => t.status?.toLowerCase() === 'fading' || t.strength < 2);

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin w-8 h-8 border-4 border-orange-200 border-t-orange-600 rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          🔥 Themes
        </h2>
        <div className="text-sm text-gray-500">
          {activeThemes.length} active • {emergingThemes.length} emerging
        </div>
      </div>

      {/* Active Themes Section */}
      <div className="bg-orange-50/50 rounded-xl p-4">
        <button
          onClick={() => toggleSection('active')}
          className="flex items-center justify-between w-full text-left"
        >
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <Flame className="w-5 h-5 text-orange-500" />
            Active Themes
            <span className="text-xs text-gray-500">(strength ≥ 5.0)</span>
            <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full text-xs ml-2">
              {activeThemes.length}
            </span>
          </h3>
          {expandedSections.active ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        
        {expandedSections.active && (
          <div className="mt-4 space-y-4">
            {activeThemes.length > 0 ? (
              activeThemes.map(theme => (
                <ActiveThemeCard key={theme.id} theme={theme} onClick={onSelectTheme} />
              ))
            ) : (
              <div className="text-center py-6 text-gray-500 text-sm">
                No active themes currently
              </div>
            )}
          </div>
        )}
      </div>

      {/* Emerging Themes Section */}
      <div className="bg-blue-50/50 rounded-xl p-4">
        <button
          onClick={() => toggleSection('emerging')}
          className="flex items-center justify-between w-full text-left"
        >
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-500" />
            Emerging Themes
            <span className="text-xs text-gray-500">(2.0 ≤ strength &lt; 5.0)</span>
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs ml-2">
              {emergingThemes.length}
            </span>
          </h3>
          {expandedSections.emerging ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
        </button>
        
        {expandedSections.emerging && (
          <div className="mt-4 grid md:grid-cols-2 gap-3">
            {emergingThemes.length > 0 ? (
              emergingThemes.map(theme => (
                <EmergingThemeCard key={theme.id} theme={theme} onClick={onSelectTheme} />
              ))
            ) : (
              <div className="col-span-2 text-center py-6 text-gray-500 text-sm">
                No emerging themes
              </div>
            )}
          </div>
        )}
      </div>

      {/* Fading Themes Section */}
      {fadingThemes.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-4">
          <button
            onClick={() => toggleSection('fading')}
            className="flex items-center justify-between w-full text-left"
          >
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <Archive className="w-5 h-5 text-gray-400" />
              Fading Themes
              <span className="px-2 py-0.5 bg-gray-200 text-gray-600 rounded-full text-xs ml-2">
                {fadingThemes.length}
              </span>
            </h3>
            {expandedSections.fading ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
          </button>
          
          {expandedSections.fading && (
            <div className="mt-3">
              {fadingThemes.map(theme => (
                <FadingThemeRow 
                  key={theme.id} 
                  theme={theme} 
                  onArchive={onArchiveTheme}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
