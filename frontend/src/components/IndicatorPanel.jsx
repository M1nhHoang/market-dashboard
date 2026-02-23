import React, { useState } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatNumber } from '../utils/format';
import GoldPriceTable from './GoldPriceTable';

// ─── Shared helpers ───────────────────────────────────────────────────────────

function TrendIcon({ trend, className = 'w-3 h-3' }) {
  if (trend === 'up') return <TrendingUp className={className} />;
  if (trend === 'down') return <TrendingDown className={className} />;
  return <Minus className={className} />;
}

function trendColor(trend) {
  if (trend === 'up') return 'text-red-500';
  if (trend === 'down') return 'text-green-600';
  return 'text-gray-400';
}

function formatChangePct(pct) {
  if (pct === null || pct === undefined) return null;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

/** One row in a compact indicator table */
function CompactRow({ label, indicator, linked = false, unit = null }) {
  if (!indicator) {
    return (
      <tr className="border-t border-gray-100">
        <td className="py-1.5 px-2 text-xs text-gray-500">{label}</td>
        <td className="py-1.5 px-2 text-right text-xs text-gray-400" colSpan={2}>—</td>
      </tr>
    );
  }

  const { value, change, change_pct, trend } = indicator;
  const displayUnit = unit || indicator.unit || '';
  const color = trendColor(trend);

  return (
    <tr className={`border-t border-gray-100 ${linked ? 'bg-blue-50' : 'hover:bg-gray-50'}`}>
      <td className="py-1.5 px-2 text-xs text-gray-600">{label}</td>
      <td className="py-1.5 px-2 text-right tabular-nums text-sm font-semibold text-gray-900">
        {formatNumber(value)}
      </td>
      <td className={`py-1.5 px-2 text-right tabular-nums text-xs ${color}`}>
        <span className="inline-flex items-center gap-0.5">
          <TrendIcon trend={trend} className="w-2.5 h-2.5" />
          {change !== null && change !== undefined
            ? formatChangePct(change_pct)
            : '—'}
        </span>
      </td>
    </tr>
  );
}

/** Section box inside a group (e.g. "Lãi suất điều hành") */
function Section({ title, children, footer }) {
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden mb-2">
      {title && (
        <div className="bg-gray-50 px-2 py-1 text-[10px] font-semibold text-gray-500 uppercase tracking-wider border-b border-gray-200">
          {title}
        </div>
      )}
      <table className="w-full">{children}</table>
      {footer && (
        <div className="bg-gray-50 px-2 py-0.5 text-[10px] text-gray-400 text-right border-t border-gray-100">
          {footer}
        </div>
      )}
    </div>
  );
}

// ─── Group renderers ──────────────────────────────────────────────────────────

/** 🏦 Monetary Policy — 3 sub-sections */
function MonetaryGroup({ groupData, linkedIndicators }) {
  const ind = Object.fromEntries(
    (groupData.indicators || []).map(i => [i.id, i])
  );

  const INTERBANK_ORDER = [
    { id: 'interbank_on', label: 'Qua đêm' },
    { id: 'interbank_1w', label: '1 Tuần' },
    { id: 'interbank_2w', label: '2 Tuần' },
    { id: 'interbank_1m', label: '1 Tháng' },
    { id: 'interbank_3m', label: '3 Tháng' },
    { id: 'interbank_6m', label: '6 Tháng' },
    { id: 'interbank_9m', label: '9 Tháng' },
  ];

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{groupData.display_name}</h3>

      {/* Policy rates */}
      <Section title="Lãi suất điều hành">
        <tbody>
          <CompactRow label="Tái cấp vốn" indicator={ind['refinancing_rate']} linked={linkedIndicators.includes('refinancing_rate')} unit="%" />
          <CompactRow label="Tái chiết khấu" indicator={ind['rediscount_rate']} linked={linkedIndicators.includes('rediscount_rate')} unit="%" />
        </tbody>
      </Section>

      {/* OMO */}
      <Section title="OMO">
        <tbody>
          <CompactRow label="OMO ròng trong ngày" indicator={ind['omo_net_daily']} linked={linkedIndicators.includes('omo_net_daily')} unit=" Tỷ" />
        </tbody>
      </Section>

      {/* Interbank rates */}
      <Section title="Lãi suất liên ngân hàng" footer="% năm">
        <tbody>
          {INTERBANK_ORDER.map(({ id, label }) => (
            <CompactRow key={id} label={label} indicator={ind[id]} linked={linkedIndicators.includes(id)} />
          ))}
        </tbody>
      </Section>
    </div>
  );
}

/** 💱 Exchange Rate — structured display with SBV + VCB sections */
function ForexGroup({ groupData, linkedIndicators }) {
  const indicators = groupData.indicators || [];

  // Partition by source
  const sbvRates = indicators.filter(i => i.source === 'SBV' || i.id === 'usd_vnd_central');
  const vcbUsd   = indicators.filter(i => i.id?.startsWith('usd_vnd_vcb'));
  const vcbEur   = indicators.filter(i => i.id?.startsWith('eur_vnd_vcb'));

  // Label maps for compact display
  const VCB_USD_LABELS = {
    usd_vnd_vcb_sell:     'Bán',
    usd_vnd_vcb_buy:      'Mua TM',
    usd_vnd_vcb_transfer: 'Mua CK',
  };

  const hasAnyData = indicators.length > 0;

  if (!hasAnyData) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">{groupData.display_name}</h3>
        <div className="text-xs text-gray-400 py-2">No data available</div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{groupData.display_name}</h3>

      {/* SBV Central Rate */}
      {sbvRates.length > 0 && (
        <Section title="NHNN — Tỷ giá trung tâm">
          <tbody>
            {sbvRates.map(ind => (
              <CompactRow
                key={ind.id}
                label="USD/VND"
                indicator={ind}
                linked={linkedIndicators.includes(ind.id)}
              />
            ))}
          </tbody>
        </Section>
      )}

      {/* VCB Commercial — USD */}
      {vcbUsd.length > 0 && (
        <Section title="Vietcombank — USD/VND">
          <tbody>
            {['usd_vnd_vcb_sell', 'usd_vnd_vcb_buy', 'usd_vnd_vcb_transfer'].map(id => {
              const ind = vcbUsd.find(i => i.id === id);
              return ind ? (
                <CompactRow
                  key={id}
                  label={VCB_USD_LABELS[id]}
                  indicator={ind}
                  linked={linkedIndicators.includes(id)}
                />
              ) : null;
            })}
          </tbody>
        </Section>
      )}

      {/* VCB Commercial — EUR */}
      {vcbEur.length > 0 && (
        <Section title="Vietcombank — EUR/VND">
          <tbody>
            {vcbEur.map(ind => (
              <CompactRow
                key={ind.id}
                label="Bán"
                indicator={ind}
                linked={linkedIndicators.includes(ind.id)}
              />
            ))}
          </tbody>
        </Section>
      )}
    </div>
  );
}

/** 📈 Inflation — compact table */
function InflationGroup({ groupData, linkedIndicators }) {
  const ind = Object.fromEntries(
    (groupData.indicators || []).map(i => [i.id, i])
  );

  const CPI_ORDER = [
    { id: 'cpi_mom', label: 'MoM' },
    { id: 'cpi_yoy', label: 'YoY' },
    { id: 'cpi_ytd', label: 'BQ đầu năm' },
    { id: 'core_inflation', label: 'Cơ bản' },
  ];

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{groupData.display_name}</h3>
      <Section title="CPI & Lạm phát" footer="%">
        <tbody>
          {CPI_ORDER.map(({ id, label }) => (
            <CompactRow key={id} label={label} indicator={ind[id]} linked={linkedIndicators.includes(id)} unit="%" />
          ))}
        </tbody>
      </Section>
    </div>
  );
}

/** 🪙 Gold — compact primary table + expandable */
function GoldGroup({ groupData, linkedIndicators }) {
  const [expanded, setExpanded] = useState(false);

  const indicators = groupData.indicators || [];
  const primaryIds = groupData.primary_indicators || [];

  const primaryIndicators = indicators.filter(ind => primaryIds.includes(ind.id));
  const allHcmIndicators = indicators.filter(
    ind => ind.attributes?.branch === 'hcm' || !ind.attributes?.branch
  );
  const regionalIndicators = indicators.filter(
    ind => ind.attributes?.branch && ind.attributes.branch !== 'hcm'
  );

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">{groupData.display_name}</h3>

      {indicators.length === 0 ? (
        <div className="text-sm text-gray-400 py-2">No data available</div>
      ) : (
        <>
          <GoldPriceTable
            indicators={primaryIndicators.length > 0 ? primaryIndicators : allHcmIndicators.slice(0, 2)}
            compact={true}
            linkedIndicators={linkedIndicators}
          />

          {(allHcmIndicators.length > primaryIndicators.length || regionalIndicators.length > 0) && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 w-full flex items-center justify-center gap-1 text-xs text-gray-500 hover:text-gray-700 py-1 border border-dashed border-gray-300 rounded-lg hover:border-gray-400 transition-colors"
            >
              {expanded ? (
                <><ChevronUp className="w-3 h-3" /> Thu gọn</>
              ) : (
                <><ChevronDown className="w-3 h-3" /> Xem tất cả ({indicators.length} loại)</>
              )}
            </button>
          )}

          {expanded && (
            <div className="mt-3 space-y-3">
              {allHcmIndicators.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">📍 Hồ Chí Minh — Tất cả loại</div>
                  <GoldPriceTable indicators={allHcmIndicators} compact={false} linkedIndicators={linkedIndicators} />
                </div>
              )}
              {regionalIndicators.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-gray-500 mb-1">🗺️ Giá SJC miếng theo khu vực</div>
                  <GoldPriceTable indicators={regionalIndicators} compact={false} showRegion={true} linkedIndicators={linkedIndicators} />
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

// Display order: Forex → Gold → Inflation → Monetary → others
const GROUP_ORDER = [
  'vietnam_forex',
  'vietnam_commodity',
  'vietnam_inflation',
  'vietnam_monetary',
];

export default function IndicatorPanel({ groups, linkedIndicators = [] }) {
  if (!groups || Object.keys(groups).length === 0) {
    return <div className="text-center py-8 text-gray-500">No indicators available</div>;
  }

  // Sort entries: known order first, then remaining alphabetically
  const sortedEntries = Object.entries(groups).sort(([a], [b]) => {
    const ia = GROUP_ORDER.indexOf(a);
    const ib = GROUP_ORDER.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  return (
    <div className="space-y-5">
      {sortedEntries.map(([groupId, groupData]) => {
        if (groupId === 'vietnam_monetary') {
          return <MonetaryGroup key={groupId} groupData={groupData} linkedIndicators={linkedIndicators} />;
        }
        if (groupId === 'vietnam_forex' || groupId.includes('forex')) {
          return <ForexGroup key={groupId} groupData={groupData} linkedIndicators={linkedIndicators} />;
        }
        if (groupId === 'vietnam_inflation' || groupId.includes('inflation')) {
          return <InflationGroup key={groupId} groupData={groupData} linkedIndicators={linkedIndicators} />;
        }
        if (groupId === 'vietnam_commodity' || groupData.expandable) {
          return <GoldGroup key={groupId} groupData={groupData} linkedIndicators={linkedIndicators} />;
        }
        // Fallback: generic compact table
        return (
          <div key={groupId}>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">{groupData.display_name || groupId}</h3>
            <Section>
              <tbody>
                {(groupData.indicators || []).length > 0 ? (
                  (groupData.indicators || []).map(ind => (
                    <CompactRow key={ind.id} label={ind.name_vi || ind.name || ind.id} indicator={ind} linked={linkedIndicators.includes(ind.id)} />
                  ))
                ) : (
                  <tr><td className="py-2 px-2 text-xs text-gray-400">No data available</td></tr>
                )}
              </tbody>
            </Section>
          </div>
        );
      })}
    </div>
  );
}
