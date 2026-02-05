const API_BASE = '/api';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================
// Health & System
// ============================================================
export const getHealth = () => fetchAPI('/health');

export const getLatestRun = () => fetchAPI('/runs/latest');

export const getRuns = (limit = 10) => fetchAPI(`/runs?limit=${limit}`);

export const triggerRefresh = () => fetchAPI('/refresh', { method: 'POST' });

// ============================================================
// Indicators
// ============================================================
export const getIndicators = (grouped = true) => 
  fetchAPI(`/indicators?grouped=${grouped}`);

export const getIndicatorsByCategory = (category) => 
  fetchAPI(`/indicators/category/${category}`);

export const getIndicatorsByRegion = (region) => 
  fetchAPI(`/indicators/region/${region}`);

export const getIndicator = (id) => 
  fetchAPI(`/indicators/${id}`);

export const getIndicatorHistory = (id, days = 30) => 
  fetchAPI(`/indicators/${id}/history?days=${days}`);

// ============================================================
// Events
// ============================================================
export const getEvents = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/events${query ? `?${query}` : ''}`);
};

export const getKeyEvents = () => fetchAPI('/events/key');

export const getOtherNews = (limit = 30, offset = 0) => 
  fetchAPI(`/events/other?limit=${limit}&offset=${offset}`);

export const getTodayEvents = () => fetchAPI('/events/today');

export const getEvent = (id) => fetchAPI(`/events/${id}`);

// ============================================================
// Investigations
// ============================================================
export const getInvestigations = (status = null) => 
  fetchAPI(`/investigations${status ? `?status=${status}` : ''}`);

export const getAllInvestigations = (limit = 50) => 
  fetchAPI(`/investigations/all?limit=${limit}`);

export const getInvestigation = (id) => 
  fetchAPI(`/investigations/${id}`);

export const getInvestigationEvidence = (id) => 
  fetchAPI(`/investigations/${id}/evidence`);

// ============================================================
// Topics
// ============================================================
export const getHotTopics = () => fetchAPI('/topics/hot');

export const getTopicEvents = (topic) => 
  fetchAPI(`/topics/${encodeURIComponent(topic)}/events`);

// ============================================================
// Calendar
// ============================================================
export const getCalendar = () => fetchAPI('/calendar');

export const getWeekCalendar = () => fetchAPI('/calendar/week');

// ============================================================
// Causal Analysis
// ============================================================
export const getCausalAnalysis = (eventId) => 
  fetchAPI(`/analysis/${eventId}`);

export default {
  getHealth,
  getLatestRun,
  getRuns,
  triggerRefresh,
  getIndicators,
  getIndicatorsByCategory,
  getIndicatorsByRegion,
  getIndicator,
  getIndicatorHistory,
  getEvents,
  getKeyEvents,
  getOtherNews,
  getTodayEvents,
  getEvent,
  getInvestigations,
  getAllInvestigations,
  getInvestigation,
  getInvestigationEvidence,
  getHotTopics,
  getTopicEvents,
  getCalendar,
  getWeekCalendar,
  getCausalAnalysis,
};
