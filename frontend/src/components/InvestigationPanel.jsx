import React from 'react';
import { AlertCircle, Clock, CheckCircle, AlertTriangle, Archive, ArrowUpRight } from 'lucide-react';
import { formatRelativeTime, getStatusColor, getPriorityClass, truncate } from '../utils/format';

function InvestigationCard({ investigation, onSelect, compact = false }) {
  const {
    id,
    question,
    status,
    priority,
    evidence_count,
    created_at,
    updated_at,
    source_event_title,
  } = investigation;

  const getStatusIcon = () => {
    switch (status?.toLowerCase()) {
      case 'resolved': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'updated': return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'stale': return <Archive className="w-4 h-4 text-gray-400" />;
      case 'escalated': return <ArrowUpRight className="w-4 h-4 text-red-500" />;
      default: return <AlertCircle className="w-4 h-4 text-blue-500" />;
    }
  };

  if (compact) {
    return (
      <div
        onClick={() => onSelect(investigation)}
        className="p-3 bg-white rounded-lg border border-gray-200 hover:border-purple-300 hover:shadow-sm cursor-pointer transition-all"
      >
        <div className="flex items-start gap-2">
          {getStatusIcon()}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 line-clamp-2">
              {question}
            </p>
            <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
              <span className={`px-1.5 py-0.5 rounded ${getStatusColor(status)}`}>
                {status}
              </span>
              <span>•</span>
              <span>{formatRelativeTime(updated_at || created_at)}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={() => onSelect(investigation)}
      className="p-4 bg-white rounded-xl border border-gray-200 hover:border-purple-300 hover:shadow-md cursor-pointer transition-all card-hover"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        {getStatusIcon()}
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
          {status?.toUpperCase()}
        </span>
        <span className={`badge ${getPriorityClass(priority)}`}>
          {priority === 'high' ? '⚡' : priority === 'medium' ? '📌' : '📋'} {priority}
        </span>
      </div>

      {/* Question */}
      <p className="text-base font-medium text-gray-900 mb-2">
        {question}
      </p>

      {/* Source Event */}
      {source_event_title && (
        <div className="text-sm text-gray-500 mb-2">
          <span className="text-gray-400">From:</span> {truncate(source_event_title, 60)}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-xs text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Created {formatRelativeTime(created_at)}
          </span>
          {evidence_count > 0 && (
            <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded-full">
              {evidence_count} evidence
            </span>
          )}
        </div>
        {updated_at && updated_at !== created_at && (
          <span>Updated {formatRelativeTime(updated_at)}</span>
        )}
      </div>
    </div>
  );
}

export default function InvestigationPanel({ investigations, onSelect, compact = false }) {
  if (!investigations || investigations.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p>No open investigations</p>
      </div>
    );
  }

  // Group by priority
  const highPriority = investigations.filter(i => i.priority === 'high');
  const otherPriority = investigations.filter(i => i.priority !== 'high');

  if (compact) {
    return (
      <div className="space-y-2">
        {investigations.map((inv) => (
          <InvestigationCard
            key={inv.id}
            investigation={inv}
            onSelect={onSelect}
            compact
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {highPriority.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-red-600 mb-2 flex items-center gap-2">
            ⚡ High Priority ({highPriority.length})
          </h3>
          <div className="space-y-3">
            {highPriority.map((inv) => (
              <InvestigationCard
                key={inv.id}
                investigation={inv}
                onSelect={onSelect}
              />
            ))}
          </div>
        </div>
      )}

      {otherPriority.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-600 mb-2">
            📋 Other ({otherPriority.length})
          </h3>
          <div className="space-y-3">
            {otherPriority.map((inv) => (
              <InvestigationCard
                key={inv.id}
                investigation={inv}
                onSelect={onSelect}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
