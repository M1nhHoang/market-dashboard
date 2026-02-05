import { format, formatDistanceToNow, parseISO, isValid } from 'date-fns';
import { vi } from 'date-fns/locale';

/**
 * Format a date string to display format
 */
export function formatDate(dateString, formatStr = 'dd/MM/yyyy') {
  if (!dateString) return '-';
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    if (!isValid(date)) return dateString;
    return format(date, formatStr);
  } catch {
    return dateString;
  }
}

/**
 * Format date with time
 */
export function formatDateTime(dateString) {
  return formatDate(dateString, 'dd/MM/yyyy HH:mm');
}

/**
 * Get relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString) {
  if (!dateString) return '-';
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    if (!isValid(date)) return dateString;
    return formatDistanceToNow(date, { addSuffix: true, locale: vi });
  } catch {
    return dateString;
  }
}

/**
 * Format number with thousands separator
 */
export function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '-';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return num.toLocaleString('vi-VN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format number as percentage
 */
export function formatPercent(value, decimals = 2) {
  if (value === null || value === undefined) return '-';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return `${num >= 0 ? '+' : ''}${num.toFixed(decimals)}%`;
}

/**
 * Format change value with + or - prefix
 */
export function formatChange(value, unit = '') {
  if (value === null || value === undefined) return '-';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  const sign = num >= 0 ? '+' : '';
  return `${sign}${formatNumber(num)}${unit}`;
}

/**
 * Get trend icon based on direction
 */
export function getTrendIcon(trend) {
  switch (trend?.toLowerCase()) {
    case 'up': return '↑';
    case 'down': return '↓';
    case 'stable': return '→';
    default: return '';
  }
}

/**
 * Get trend color class
 */
export function getTrendClass(trend, inverse = false) {
  const isUp = trend?.toLowerCase() === 'up';
  const isDown = trend?.toLowerCase() === 'down';
  
  if (inverse) {
    if (isUp) return 'trend-down';
    if (isDown) return 'trend-up';
  } else {
    if (isUp) return 'trend-up';
    if (isDown) return 'trend-down';
  }
  return 'trend-stable';
}

/**
 * Parse JSON safely
 */
export function safeParseJSON(str, fallback = null) {
  if (!str) return fallback;
  if (typeof str === 'object') return str;
  try {
    return JSON.parse(str);
  } catch {
    return fallback;
  }
}

/**
 * Get priority badge class
 */
export function getPriorityClass(priority) {
  switch (priority?.toLowerCase()) {
    case 'high': return 'badge-high';
    case 'medium': return 'badge-medium';
    case 'low': return 'badge-low';
    default: return 'badge-low';
  }
}

/**
 * Get status color
 */
export function getStatusColor(status) {
  switch (status?.toLowerCase()) {
    case 'open': return 'text-blue-600 bg-blue-50';
    case 'updated': return 'text-yellow-600 bg-yellow-50';
    case 'resolved': return 'text-green-600 bg-green-50';
    case 'stale': return 'text-gray-600 bg-gray-50';
    case 'escalated': return 'text-red-600 bg-red-50';
    default: return 'text-gray-600 bg-gray-50';
  }
}

/**
 * Truncate text
 */
export function truncate(str, length = 100) {
  if (!str) return '';
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

/**
 * Get confidence color
 */
export function getConfidenceColor(confidence) {
  switch (confidence?.toLowerCase()) {
    case 'verified': return 'text-green-600';
    case 'likely': return 'text-yellow-600';
    case 'uncertain': return 'text-gray-500';
    default: return 'text-gray-500';
  }
}

/**
 * Category display names
 */
export const CATEGORY_LABELS = {
  monetary: '🏦 Monetary',
  fiscal: '💰 Fiscal',
  banking: '🏛️ Banking',
  economic: '📊 Economic',
  geopolitical: '🌐 Geopolitical',
  corporate: '🏢 Corporate',
  regulatory: '📋 Regulatory',
  internal: '🏠 Internal',
};

/**
 * Get category label
 */
export function getCategoryLabel(category) {
  return CATEGORY_LABELS[category?.toLowerCase()] || category || 'Unknown';
}
