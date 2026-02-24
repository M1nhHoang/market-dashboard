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
// Signals (LEGACY - Use /trends for dashboard)
// Kept for SignalDetail modal and direct signal access
// ============================================================
/** @deprecated Use getTrends() for dashboard views instead */
export const getSignals = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/signals${query ? `?${query}` : ''}`);
};

/** Used by: SignalDetail modal when viewing individual signal */
export const getSignal = (id) => fetchAPI(`/signals/${id}`);

/** @deprecated Signal accuracy is now included in getTrends summary */
export const getSignalAccuracy = () => fetchAPI('/signals/accuracy');

// ============================================================
// Themes (LEGACY - Use /trends for dashboard)
// Kept for backward compatibility, prefer /trends endpoints
// ============================================================
/** @deprecated Use getTrends() for dashboard views instead */
export const getThemes = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/themes${query ? `?${query}` : ''}`);
};

/** @deprecated Use getTrend() instead */
export const getTheme = (id) => fetchAPI(`/themes/${id}`);

/** @deprecated Use archiveTrend() instead */
export const archiveTheme = (id) => 
  fetchAPI(`/themes/${id}/archive`, { method: 'POST' });

// ============================================================
// Trends (Unified: Themes + Signals)
// ============================================================
// NEW: Primary endpoint for dashboard - replaces separate themes/signals

/**
 * Get all trends for dashboard
 * Used by: TrendsPanel component
 * @param {Object} params - Query params
 * @param {string} params.urgency - Filter by urgency: 'urgent', 'watching', 'low'
 * @param {boolean} params.with_summary - Include summary stats (default: true)
 * @param {boolean} params.include_fading - Include fading trends (default: false)
 * @param {number} params.limit - Max results (default: 30)
 * @param {number} params.offset - Offset for pagination (default: 0)
 */
export const getTrends = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return fetchAPI(`/trends${query ? `?${query}` : ''}`);
};

/**
 * Get single trend with full details
 * Used by: TrendDetail modal/component
 */
export const getTrend = (id) => fetchAPI(`/trends/${id}`);

/**
 * Get urgent trends for sidebar
 * Used by: Vietnam/Global tab sidebar "Active Trends" section
 */
export const getUrgentTrendsSidebar = () => fetchAPI('/trends/urgent/sidebar');

/**
 * Archive a trend (removes from active dashboard)
 * Used by: TrendDetail "Archive" button
 */
export const archiveTrend = (id) => 
  fetchAPI(`/trends/${id}/archive`, { method: 'POST' });

/**
 * Dismiss a trend (moves to fading section)
 * Used by: TrendDetail "Dismiss" button  
 */
export const dismissTrend = (id) => 
  fetchAPI(`/trends/${id}/dismiss`, { method: 'POST' });

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
  // Trends (unified: Themes + Signals)
  getTrends,
  getTrend,
  getUrgentTrendsSidebar,
  archiveTrend,
  dismissTrend,
  // Watchlist
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
