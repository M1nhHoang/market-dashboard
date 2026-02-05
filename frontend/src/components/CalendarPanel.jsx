import React from 'react';
import { Calendar, AlertCircle } from 'lucide-react';
import { formatDate } from '../utils/format';

export default function CalendarPanel({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          Upcoming Events
        </h3>
        <div className="text-center py-4 text-gray-500 text-sm">
          No upcoming events
        </div>
      </div>
    );
  }

  const getImportanceColor = (importance) => {
    switch (importance?.toLowerCase()) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      default: return 'bg-gray-400';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <Calendar className="w-4 h-4" />
        Upcoming Events
      </h3>
      <div className="space-y-2">
        {events.slice(0, 5).map((event, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {/* Importance Indicator */}
            <div className="flex flex-col items-center">
              <div className={`w-2 h-2 rounded-full ${getImportanceColor(event.importance)}`} />
              {idx < events.length - 1 && (
                <div className="w-px h-full bg-gray-200 mt-1" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="text-xs text-gray-500 mb-0.5">
                {formatDate(event.date)}
                {event.time && ` ${event.time}`}
              </div>
              <p className="text-sm font-medium text-gray-900 line-clamp-2">
                {event.event_name || event.event}
              </p>
              {event.country && (
                <span className="text-xs text-gray-400">{event.country}</span>
              )}
              {(event.forecast || event.previous) && (
                <div className="flex gap-2 mt-1 text-xs">
                  {event.forecast && (
                    <span className="text-gray-500">
                      Forecast: <span className="text-gray-700">{event.forecast}</span>
                    </span>
                  )}
                  {event.previous && (
                    <span className="text-gray-400">
                      Prev: {event.previous}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {events.length > 5 && (
        <div className="mt-3 text-center">
          <button className="text-xs text-primary-600 hover:text-primary-700">
            View all {events.length} events →
          </button>
        </div>
      )}
    </div>
  );
}
