import React from 'react';
import { Clock, ExternalLink, Flame, Link2 } from 'lucide-react';
import { formatDate, formatRelativeTime, getCategoryLabel, truncate, safeParseJSON } from '../utils/format';
import LoadingSpinner from './LoadingSpinner';

function EventCard({ event, onSelect, compact = false }) {
  const {
    id,
    title,
    summary,
    category,
    region,
    base_score,
    current_score,
    published_at,
    source,
    linked_indicators,
    display_section,
    hot_topic,
  } = event;

  const indicators = safeParseJSON(linked_indicators, []);
  const score = current_score || base_score || 0;

  const getScoreColor = () => {
    if (score >= 70) return 'bg-red-100 text-red-800';
    if (score >= 50) return 'bg-orange-100 text-orange-800';
    if (score >= 30) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  if (compact) {
    return (
      <div
        onClick={() => onSelect(event)}
        className="p-3 bg-white rounded-lg border border-gray-200 hover:border-primary-300 hover:shadow-sm cursor-pointer transition-all"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-gray-900 line-clamp-2">
              {title}
            </h4>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
              <span>{getCategoryLabel(category)}</span>
              <span>•</span>
              <span>{formatRelativeTime(published_at)}</span>
            </div>
          </div>
          <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${getScoreColor()}`}>
            {Math.round(score)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={() => onSelect(event)}
      className="p-4 bg-white rounded-xl border border-gray-200 hover:border-primary-300 hover:shadow-md cursor-pointer transition-all card-hover"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${getScoreColor()}`}>
            {Math.round(score)}
          </span>
          <span className="text-xs text-gray-500">
            {getCategoryLabel(category)}
          </span>
          {region && (
            <span className="text-xs text-gray-400">
              {region === 'vietnam' ? '🇻🇳' : '🌍'}
            </span>
          )}
          {hot_topic && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full text-xs">
              <Flame className="w-3 h-3" />
              Hot
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <Clock className="w-3 h-3" />
          {formatRelativeTime(published_at)}
        </div>
      </div>

      {/* Title */}
      <h3 className="text-base font-semibold text-gray-900 mb-2 line-clamp-2">
        {title}
      </h3>

      {/* Summary */}
      {summary && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {summary}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        {/* Linked Indicators */}
        {indicators.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <Link2 className="w-3.5 h-3.5 text-gray-400" />
            {indicators.slice(0, 3).map((ind, i) => (
              <span
                key={i}
                className="text-xs px-1.5 py-0.5 bg-primary-50 text-primary-700 rounded"
              >
                {ind}
              </span>
            ))}
            {indicators.length > 3 && (
              <span className="text-xs text-gray-400">
                +{indicators.length - 3} more
              </span>
            )}
          </div>
        )}

        {/* Source */}
        {source && (
          <span className="text-xs text-gray-400 flex items-center gap-1">
            <ExternalLink className="w-3 h-3" />
            {source}
          </span>
        )}
      </div>
    </div>
  );
}

export default function EventList({ events, loading, onSelect, compact = false }) {
  if (loading) {
    return <LoadingSpinner />;
  }

  if (!events || events.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No events found</p>
      </div>
    );
  }

  return (
    <div className={compact ? 'space-y-2' : 'space-y-3'}>
      {events.map((event) => (
        <EventCard
          key={event.id}
          event={event}
          onSelect={onSelect}
          compact={compact}
        />
      ))}
    </div>
  );
}
