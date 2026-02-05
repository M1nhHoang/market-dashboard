import React, { useEffect, useState } from 'react';
import { X, ExternalLink, Link2, AlertCircle, CheckCircle, HelpCircle, Clock, TrendingUp } from 'lucide-react';
import { getEvent } from '../services/api';
import { formatDateTime, formatRelativeTime, getCategoryLabel, safeParseJSON, getConfidenceColor } from '../utils/format';
import LoadingSpinner from './LoadingSpinner';

export default function EventDetail({ event, onClose }) {
  const [fullEvent, setFullEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchEvent = async () => {
      if (!event?.id) return;
      try {
        setLoading(true);
        const data = await getEvent(event.id);
        setFullEvent(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchEvent();
  }, [event?.id]);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  if (!event) return null;

  const data = fullEvent || event;
  const linkedIndicators = safeParseJSON(data.linked_indicators, []);
  const scoreFactors = safeParseJSON(data.score_factors, {});
  const causalAnalysis = data.causal_analysis;
  const chainSteps = safeParseJSON(causalAnalysis?.chain_steps, []);
  const needsInvestigation = safeParseJSON(causalAnalysis?.needs_investigation, []);

  const getConfidenceIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'verified': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'likely': return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default: return <HelpCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 bg-primary-100 text-primary-800 rounded-full text-sm font-bold">
                {Math.round(data.current_score || data.base_score || 0)}
              </span>
              <span className="text-sm text-gray-500">{getCategoryLabel(data.category)}</span>
              {data.region && (
                <span className="text-sm">{data.region === 'vietnam' ? '🇻🇳' : '🌍'}</span>
              )}
            </div>
            <h2 className="text-xl font-bold text-gray-900">{data.title}</h2>
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
              {/* Summary */}
              {data.summary && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Summary</h3>
                  <p className="text-gray-600">{data.summary}</p>
                </div>
              )}

              {/* Metadata */}
              <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-1 text-gray-500">
                  <Clock className="w-4 h-4" />
                  {formatDateTime(data.published_at)}
                </div>
                {data.source && (
                  <div className="flex items-center gap-1 text-gray-500">
                    <ExternalLink className="w-4 h-4" />
                    <a
                      href={data.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline"
                    >
                      {data.source}
                    </a>
                  </div>
                )}
              </div>

              {/* Linked Indicators */}
              {linkedIndicators.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <Link2 className="w-4 h-4" />
                    Linked Indicators
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {linkedIndicators.map((ind, i) => (
                      <span
                        key={i}
                        className="px-3 py-1.5 bg-primary-50 text-primary-700 rounded-lg text-sm font-medium"
                      >
                        {ind}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Score Factors */}
              {Object.keys(scoreFactors).length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Score Breakdown
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(scoreFactors).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center p-2 bg-gray-50 rounded-lg">
                        <span className="text-sm text-gray-600 capitalize">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span className="text-sm font-medium text-gray-900">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Causal Chain */}
              {chainSteps.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    🔗 Causal Chain Analysis
                    {causalAnalysis?.template_id && (
                      <span className="text-xs text-gray-400 font-normal">
                        (Template: {causalAnalysis.template_id})
                      </span>
                    )}
                  </h3>
                  <div className="space-y-0">
                    {chainSteps.map((step, idx) => (
                      <div
                        key={idx}
                        className={`chain-node ${step.status?.toLowerCase() || 'uncertain'}`}
                      >
                        <div className="flex items-start gap-2">
                          {getConfidenceIcon(step.status)}
                          <div>
                            <div className="font-medium text-gray-800">
                              {step.step && <span className="text-gray-400 mr-1">Step {step.step}:</span>}
                              {step.event || step.description}
                            </div>
                            {step.event_vi && (
                              <div className="text-sm text-gray-500">{step.event_vi}</div>
                            )}
                            <div className={`text-xs mt-0.5 ${getConfidenceColor(step.status)}`}>
                              {step.status || 'uncertain'}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {causalAnalysis?.reasoning && (
                    <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                      <p className="text-sm text-blue-800">{causalAnalysis.reasoning}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Needs Investigation */}
              {needsInvestigation.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-orange-500" />
                    Needs Investigation
                  </h3>
                  <ul className="space-y-2">
                    {needsInvestigation.map((item, i) => (
                      <li key={i} className="flex items-start gap-2 p-2 bg-orange-50 rounded-lg">
                        <span className="text-orange-500">🔍</span>
                        <span className="text-sm text-orange-800">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Related Investigations */}
              {data.related_investigations?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">
                    Related Investigations
                  </h3>
                  <div className="space-y-2">
                    {data.related_investigations.map((inv) => (
                      <div
                        key={inv.id}
                        className="p-3 bg-purple-50 rounded-lg border border-purple-100"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            inv.status === 'resolved' ? 'bg-green-100 text-green-700' :
                            inv.status === 'updated' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {inv.status}
                          </span>
                          <span className="text-xs text-gray-400">{inv.priority}</span>
                        </div>
                        <p className="text-sm text-purple-900">{inv.question}</p>
                      </div>
                    ))}
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
