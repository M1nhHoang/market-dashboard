import React, { useEffect, useState } from 'react';
import { X, Clock, AlertCircle, CheckCircle, XCircle, Minus, FileText } from 'lucide-react';
import { getInvestigation } from '../services/api';
import { formatDateTime, formatRelativeTime, getStatusColor, getPriorityClass, safeParseJSON } from '../utils/format';
import LoadingSpinner from './LoadingSpinner';

export default function InvestigationDetail({ investigation, onClose }) {
  const [fullData, setFullData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!investigation?.id) return;
      try {
        setLoading(true);
        const data = await getInvestigation(investigation.id);
        setFullData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [investigation?.id]);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  if (!investigation) return null;

  const data = fullData || investigation;
  const relatedIndicators = safeParseJSON(data.related_indicators, []);
  const evidenceTimeline = data.evidence_timeline || [];

  const getEvidenceIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'supports': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'contradicts': return <XCircle className="w-4 h-4 text-red-500" />;
      default: return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const getEvidenceBg = (type) => {
    switch (type?.toLowerCase()) {
      case 'supports': return 'border-l-green-400 bg-green-50';
      case 'contradicts': return 'border-l-red-400 bg-red-50';
      default: return 'border-l-gray-300 bg-gray-50';
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(data.status)}`}>
                {data.status?.toUpperCase()}
              </span>
              <span className={`badge ${getPriorityClass(data.priority)}`}>
                {data.priority === 'high' ? '⚡' : '📌'} {data.priority}
              </span>
            </div>
            <h2 className="text-xl font-bold text-gray-900">Investigation</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {loading ? (
            <LoadingSpinner />
          ) : error ? (
            <div className="text-red-500 text-center py-8">{error}</div>
          ) : (
            <>
              {/* Question */}
              <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
                <h3 className="text-sm font-semibold text-purple-700 mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Question
                </h3>
                <p className="text-lg font-medium text-purple-900">{data.question}</p>
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-2 text-gray-600">
                  <Clock className="w-4 h-4" />
                  <span>Created: {formatDateTime(data.created_at)}</span>
                </div>
                {data.updated_at && (
                  <div className="flex items-center gap-2 text-gray-600">
                    <Clock className="w-4 h-4" />
                    <span>Updated: {formatRelativeTime(data.updated_at)}</span>
                  </div>
                )}
              </div>

              {/* Context */}
              {data.context && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Context</h3>
                  <p className="text-gray-600">{data.context}</p>
                </div>
              )}

              {/* Related Indicators */}
              {relatedIndicators.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Related Indicators</h3>
                  <div className="flex flex-wrap gap-2">
                    {relatedIndicators.map((ind, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 bg-primary-50 text-primary-700 rounded-lg text-sm"
                      >
                        {ind}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence Summary */}
              {data.evidence_summary && (
                <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                  <h3 className="text-sm font-semibold text-blue-700 mb-2 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Evidence Summary
                  </h3>
                  <p className="text-blue-800">{data.evidence_summary}</p>
                </div>
              )}

              {/* Resolution */}
              {data.status === 'resolved' && data.resolution && (
                <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                  <h3 className="text-sm font-semibold text-green-700 mb-2 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Resolution
                  </h3>
                  <p className="text-green-800">{data.resolution}</p>
                  {data.resolution_confidence && (
                    <p className="text-sm text-green-600 mt-2">
                      Confidence: {data.resolution_confidence}
                    </p>
                  )}
                </div>
              )}

              {/* Evidence Timeline */}
              {evidenceTimeline.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    📊 Evidence Timeline ({evidenceTimeline.length})
                  </h3>
                  <div className="space-y-3">
                    {evidenceTimeline.map((evidence, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border-l-4 ${getEvidenceBg(evidence.evidence_type)}`}
                      >
                        <div className="flex items-start gap-2">
                          {getEvidenceIcon(evidence.evidence_type)}
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium uppercase text-gray-500">
                                {evidence.evidence_type}
                              </span>
                              <span className="text-xs text-gray-400">
                                {formatRelativeTime(evidence.added_at)}
                              </span>
                            </div>
                            {evidence.event_title && (
                              <p className="font-medium text-gray-900 text-sm mb-1">
                                {evidence.event_title}
                              </p>
                            )}
                            <p className="text-sm text-gray-700">{evidence.summary}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Event */}
              {data.source_event && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Source Event</h3>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="font-medium text-gray-900">{data.source_event.title}</p>
                    <p className="text-sm text-gray-500 mt-1">{data.source_event.summary}</p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
