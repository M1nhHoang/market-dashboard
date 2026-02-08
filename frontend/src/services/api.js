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
// Signals
// ============================================================
export const getSignals = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/signals${query ? `?${query}` : ''}`);
};

export const getSignal = (id) => fetchAPI(`/signals/${id}`);

export const getSignalAccuracy = () => fetchAPI('/signals/accuracy');

// ============================================================
// Themes
// ============================================================
export const getThemes = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/themes${query ? `?${query}` : ''}`);
};

export const getTheme = (id) => fetchAPI(`/themes/${id}`);

export const archiveTheme = (id) => 
  fetchAPI(`/themes/${id}/archive`, { method: 'POST' });

// ============================================================
// Watchlist
// ============================================================
export const getWatchlist = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/watchlist${query ? `?${query}` : ''}`);
};

export const getWatchlistItem = (id) => fetchAPI(`/watchlist/${id}`);

export const createWatchlistItem = (data) => 
  fetchAPI('/watchlist', { method: 'POST', body: JSON.stringify(data) });

export const updateWatchlistItem = (id, data) => 
  fetchAPI(`/watchlist/${id}`, { method: 'PUT', body: JSON.stringify(data) });

export const deleteWatchlistItem = (id) => 
  fetchAPI(`/watchlist/${id}`, { method: 'DELETE' });

export const dismissWatchlistItem = (id) => 
  fetchAPI(`/watchlist/${id}/dismiss`, { method: 'POST' });

export const snoozeWatchlistItem = (id, days) => 
  fetchAPI(`/watchlist/${id}/snooze`, { method: 'POST', body: JSON.stringify({ days }) });

export const restoreWatchlistItem = (id) => 
  fetchAPI(`/watchlist/${id}/restore`, { method: 'POST' });

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
  getSignals,
  getSignal,
  getSignalAccuracy,
  getThemes,
  getTheme,
  archiveTheme,
  getWatchlist,
  getWatchlistItem,
  createWatchlistItem,
  updateWatchlistItem,
  deleteWatchlistItem,
  dismissWatchlistItem,
  snoozeWatchlistItem,
  restoreWatchlistItem,
  getHotTopics,
  getTopicEvents,
  getCalendar,
  getWeekCalendar,
  getCausalAnalysis,
};
