/**
 * Signal Consensus Calculation Utils
 * 
 * Computes weighted consensus scores for signals, considering:
 * - confidence (high: 3, medium: 2, low: 1)
 * - freshness (days_remaining / timeframe_days, clamped 0.1 → 1.0)
 * - direction (up → +weight, down → -weight, stable → 0)
 * 
 * Used in:
 * 1. Overall Market Consensus (all active signals)
 * 2. Per-Indicator Consensus (grouped by target_indicator)
 * 3. Per-Trend Consensus (signals within one trend)
 */

const CONFIDENCE_WEIGHTS = { high: 3, medium: 2, low: 1 };

/**
 * Calculate weight for a single signal
 */
function getSignalWeight(signal) {
  const confWeight = CONFIDENCE_WEIGHTS[signal.confidence] || 2;

  // Freshness: days_remaining / timeframe_days
  let freshnessWeight = 1.0;
  if (signal.expires_at && signal.timeframe_days) {
    const now = new Date();
    const expiry = new Date(signal.expires_at);
    const daysRemaining = Math.max(0, (expiry - now) / (1000 * 60 * 60 * 24));
    freshnessWeight = Math.max(0.1, Math.min(1.0, daysRemaining / signal.timeframe_days));
  } else if (signal.expires_at) {
    // Fallback: if no timeframe_days, use expires_at only
    const now = new Date();
    const expiry = new Date(signal.expires_at);
    const daysRemaining = Math.max(0, (expiry - now) / (1000 * 60 * 60 * 24));
    // Assume 30d as default timeframe
    freshnessWeight = Math.max(0.1, Math.min(1.0, daysRemaining / 30));
  }

  return confWeight * freshnessWeight;
}

/**
 * Compute consensus from an array of signals
 * 
 * @param {Array} signals - Active signals array
 * @returns {Object} { bullishPct, bearishPct, label, direction, totalSignals, upCount, downCount, stableCount }
 */
export function computeConsensus(signals) {
  const activeSignals = (signals || []).filter(s => s.status === 'active');
  
  if (activeSignals.length === 0) {
    return {
      bullishPct: 50,
      bearishPct: 50,
      label: 'NO DATA',
      direction: 'neutral',
      totalSignals: 0,
      upCount: 0,
      downCount: 0,
      stableCount: 0,
    };
  }

  let positiveSum = 0;
  let totalAbsSum = 0;
  let upCount = 0;
  let downCount = 0;
  let stableCount = 0;

  for (const signal of activeSignals) {
    const weight = getSignalWeight(signal);
    
    if (signal.direction === 'up') {
      positiveSum += weight;
      totalAbsSum += weight;
      upCount++;
    } else if (signal.direction === 'down') {
      totalAbsSum += weight;
      downCount++;
    } else {
      // stable → neutral, still counts in total for denominator
      totalAbsSum += weight * 0.5; // Half-weight for stable (doesn't push either direction)
      positiveSum += weight * 0.5; // Neutral contribution
      stableCount++;
    }
  }

  const bullishPct = totalAbsSum > 0 ? Math.round((positiveSum / totalAbsSum) * 100) : 50;
  const bearishPct = 100 - bullishPct;

  let label, direction;
  if (bullishPct > 55) {
    label = `▲ ${bullishPct}% UP`;
    direction = 'bullish';
  } else if (bullishPct < 45) {
    label = `▼ ${bearishPct}% DOWN`;
    direction = 'bearish';
  } else {
    label = `→ ${bullishPct}% FLAT`;
    direction = 'neutral';
  }

  return {
    bullishPct,
    bearishPct,
    label,
    direction,
    totalSignals: activeSignals.length,
    upCount,
    downCount,
    stableCount,
  };
}

/**
 * Group signals by target_indicator and compute consensus per group
 * 
 * @param {Array} signals - All active signals
 * @returns {Array} Sorted array of { indicator, signals, consensus }
 *   Sorted by: signal count DESC, then abs(consensus - 50) DESC
 */
export function groupSignalsByIndicator(signals) {
  const activeSignals = (signals || []).filter(s => s.status === 'active');
  
  // Group
  const groups = {};
  for (const signal of activeSignals) {
    const key = signal.target_indicator || 'unknown';
    if (!groups[key]) groups[key] = [];
    groups[key].push(signal);
  }

  // Compute consensus per group
  const result = Object.entries(groups).map(([indicator, sigs]) => ({
    indicator,
    signals: sigs,
    consensus: computeConsensus(sigs),
  }));

  // Sort: signal count DESC, then clarity DESC
  result.sort((a, b) => {
    const countDiff = b.signals.length - a.signals.length;
    if (countDiff !== 0) return countDiff;
    // Higher clarity (further from 50%) goes first
    const aClarity = Math.abs(a.consensus.bullishPct - 50);
    const bClarity = Math.abs(b.consensus.bullishPct - 50);
    return bClarity - aClarity;
  });

  return result;
}

/**
 * Get days remaining until a signal expires
 */
export function getDaysUntilExpiry(expiresAt) {
  if (!expiresAt) return null;
  const now = new Date();
  const expiry = new Date(expiresAt);
  return Math.max(0, Math.ceil((expiry - now) / (1000 * 60 * 60 * 24)));
}

/**
 * Format target range for display
 * - Both low + high: "8.8 → 9.9"
 * - Only low: "> 8.8"
 * - Only high: "< 9.9"
 * - Neither: direction label ("▲ UP" / "▼ DOWN" / "→ STABLE")
 */
export function formatTargetRange(signal) {
  const { target_range_low, target_range_high, direction } = signal;
  
  if (target_range_low != null && target_range_high != null) {
    return `${target_range_low} → ${target_range_high}`;
  }
  if (target_range_low != null) {
    return `> ${target_range_low}`;
  }
  if (target_range_high != null) {
    return `< ${target_range_high}`;
  }
  
  // Fallback to direction label
  switch (direction) {
    case 'up': return '▲ UP';
    case 'down': return '▼ DOWN';
    case 'stable': return '→ STABLE';
    default: return '-';
  }
}

/**
 * Get indicator emoji from CATEGORY_CONFIG-style mapping
 */
const INDICATOR_ICONS = {
  interbank_on: '🏦',
  interbank_1w: '🏦',
  interbank_2w: '🏦',
  gold_sjc: '🥇',
  gold_world: '🥇',
  brent_alf: '⛽',
  brent_oil: '⛽',
  usd_vnd: '💱',
  usd_vnd_central: '💱',
  dxy: '💵',
  vn_index: '📈',
  vnindex: '📈',
  market_liquidity_hose: '📊',
};

export function getIndicatorIcon(indicator) {
  if (!indicator) return '📡';
  const lower = indicator.toLowerCase();
  // Exact match first
  if (INDICATOR_ICONS[lower]) return INDICATOR_ICONS[lower];
  // Partial match
  for (const [key, icon] of Object.entries(INDICATOR_ICONS)) {
    if (lower.includes(key) || key.includes(lower)) return icon;
  }
  return '📡';
}
