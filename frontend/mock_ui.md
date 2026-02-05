import React, { useState, useEffect } from 'react';

// Mock data representing what the LLM system would aggregate
const mockVietnamData = {
  macro: {
    omo: { value: 4.0, change: -0.25, unit: '%', trend: 'down', lastUpdate: '03/02/2026' },
    interbank: { value: 3.85, change: 0.15, unit: '%', trend: 'up', lastUpdate: '03/02/2026' },
    usdVnd: { value: 25420, change: 85, unit: 'VND', trend: 'up', lastUpdate: '03/02/2026' },
    cpi: { value: 3.2, change: 0.1, unit: '%', trend: 'up', lastUpdate: '01/2026' },
    creditGrowth: { value: 14.5, change: 1.2, unit: '%', trend: 'up', lastUpdate: '01/2026' },
  },
  banking: {
    depositRate: { avg: 4.8, change: 0.3, trend: 'up' },
    lendingRate: { avg: 8.5, change: 0.2, trend: 'up' },
    nplRatio: { value: 4.55, change: 0.15, trend: 'up' },
    kbnnDeposits: { change: -15000, unit: 'tỷ VND', trend: 'down' },
  },
  events: [
    {
      id: 1,
      title: 'Giải ngân đầu tư công tăng mạnh T1/2026',
      popularity: 85,
      impact: 'high',
      category: 'fiscal',
      timestamp: '2026-02-01',
      causalChain: [
        { event: 'Giải ngân ĐTCC tăng 45% YoY', verified: true },
        { event: 'KBNN rút ~15,000 tỷ từ hệ thống NH', verified: true },
        { event: 'Thanh khoản liên ngân hàng căng', verified: true },
        { event: 'Lãi suất huy động tăng 0.3%', verified: true },
        { event: 'Áp lực margin call một số cổ phiếu', verified: false, needInvestigation: true },
      ],
      linkedIndicators: ['interbank', 'depositRate', 'kbnnDeposits'],
      sources: ['SBV', 'MoF', 'Bloomberg'],
    },
    {
      id: 2,
      title: 'NHNN bơm ròng qua OMO 3 tuần liên tiếp',
      popularity: 72,
      impact: 'medium',
      category: 'monetary',
      timestamp: '2026-02-02',
      causalChain: [
        { event: 'OMO net inject 25,000 tỷ', verified: true },
        { event: 'Bù đắp một phần rút KBNN', verified: true },
        { event: 'Lãi suất ON ổn định quanh 3.8%', verified: true },
      ],
      linkedIndicators: ['omo', 'interbank'],
      sources: ['SBV', 'Reuters'],
    },
    {
      id: 3,
      title: 'Nợ xấu ngân hàng tăng - TT 02 hết hiệu lực',
      popularity: 68,
      impact: 'high',
      category: 'banking',
      timestamp: '2026-01-28',
      causalChain: [
        { event: 'TT02 hết hiệu lực 31/12/2025', verified: true },
        { event: 'NPL ratio tăng từ 1.9% → 4.55%', verified: true },
        { event: 'Áp lực trích lập dự phòng', verified: true },
        { event: 'Lợi nhuận NH Q1/2026 có thể giảm', verified: false, needInvestigation: true },
      ],
      linkedIndicators: ['nplRatio'],
      sources: ['SBV', 'BCTC Ngân hàng'],
    },
  ],
};

const mockGlobalData = {
  macro: {
    fedRate: { value: 4.25, change: 0, unit: '%', trend: 'stable', lastUpdate: '01/2026' },
    dxy: { value: 108.5, change: 1.2, unit: '', trend: 'up', lastUpdate: '03/02/2026' },
    us10y: { value: 4.55, change: 0.08, unit: '%', trend: 'up', lastUpdate: '03/02/2026' },
    brentOil: { value: 78.5, change: -2.3, unit: 'USD', trend: 'down', lastUpdate: '03/02/2026' },
    gold: { value: 2045, change: 15, unit: 'USD', trend: 'up', lastUpdate: '03/02/2026' },
    copper: { value: 8650, change: -120, unit: 'USD/MT', trend: 'down', lastUpdate: '03/02/2026' },
  },
  events: [
    {
      id: 101,
      title: 'Fed giữ nguyên lãi suất, signal hawkish Q1',
      popularity: 95,
      impact: 'high',
      category: 'monetary',
      timestamp: '2026-01-29',
      causalChain: [
        { event: 'Fed hold 4.25-4.50%', verified: true },
        { event: 'Dot plot: 2 cuts in 2026 (vs 4 expected)', verified: true },
        { event: 'DXY rally 1.2%', verified: true },
        { event: 'EM currencies weaken', verified: true },
        { event: 'VND áp lực mất giá', verified: true },
      ],
      linkedIndicators: ['fedRate', 'dxy', 'usdVnd'],
      impactOnVN: 'Áp lực tỷ giá VND, room giảm lãi suất VN hẹp',
      sources: ['Fed', 'Bloomberg', 'Reuters'],
    },
    {
      id: 102,
      title: 'China PMI Manufacturing < 50 tháng thứ 3',
      popularity: 78,
      impact: 'medium',
      category: 'economic',
      timestamp: '2026-02-01',
      causalChain: [
        { event: 'China PMI 49.2', verified: true },
        { event: 'Demand hàng hóa công nghiệp yếu', verified: true },
        { event: 'Copper, steel giảm', verified: true },
        { event: 'Xuất khẩu VN sang TQ có thể chậm lại', verified: false, needInvestigation: true },
      ],
      linkedIndicators: ['copper'],
      impactOnVN: 'Xuất khẩu VN sang TQ chiếm 17% - cần theo dõi',
      sources: ['NBS China', 'Caixin'],
    },
  ],
  calendar: [
    { date: '2026-02-05', event: 'US Nonfarm Payrolls', importance: 'high', forecast: '+180K' },
    { date: '2026-02-07', event: 'China CPI/PPI', importance: 'medium', forecast: 'CPI 0.3%' },
    { date: '2026-02-12', event: 'US CPI', importance: 'high', forecast: '2.9% YoY' },
    { date: '2026-02-19', event: 'FOMC Minutes', importance: 'high', forecast: '-' },
  ],
};

// System Architecture Visualization
const SystemArchitecture = () => (
  <div className="architecture-section">
    <h3>🔧 System Architecture</h3>
    <div className="arch-flow">
      <div className="arch-stage">
        <div className="stage-icon">📥</div>
        <div className="stage-name">Data Ingestion</div>
        <div className="stage-details">
          <span>SBV API</span>
          <span>News RSS</span>
          <span>BCTC Crawl</span>
          <span>Bloomberg</span>
        </div>
      </div>
      <div className="arch-arrow">→</div>
      <div className="arch-stage">
        <div className="stage-icon">🧠</div>
        <div className="stage-name">Round 1: Extract</div>
        <div className="stage-details">
          <span>Entity Recognition</span>
          <span>Fact Extraction</span>
          <span>Deduplication</span>
        </div>
      </div>
      <div className="arch-arrow">→</div>
      <div className="arch-stage">
        <div className="stage-icon">🔗</div>
        <div className="stage-name">Round 2: Link</div>
        <div className="stage-details">
          <span>Embedding Search</span>
          <span>Causal Mapping</span>
          <span>Cross-reference</span>
        </div>
      </div>
      <div className="arch-arrow">→</div>
      <div className="arch-stage">
        <div className="stage-icon">💡</div>
        <div className="stage-name">Round 3: Reason</div>
        <div className="stage-details">
          <span>Impact Analysis</span>
          <span>Prediction</span>
          <span>Confidence Score</span>
        </div>
      </div>
      <div className="arch-arrow">→</div>
      <div className="arch-stage">
        <div className="stage-icon">📊</div>
        <div className="stage-name">Dashboard</div>
        <div className="stage-details">
          <span>Real-time View</span>
          <span>Alerts</span>
          <span>Drill-down</span>
        </div>
      </div>
    </div>
    <div className="memory-layer">
      <div className="memory-icon">💾</div>
      <div className="memory-text">
        <strong>Long-term Memory Layer</strong>
        <span>Vector DB (embeddings) + Graph DB (causal chains) + Time-series DB (indicators)</span>
      </div>
    </div>
  </div>
);

// Indicator Card Component
const IndicatorCard = ({ name, data, linked }) => {
  const getTrendIcon = (trend) => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };
  
  const getTrendClass = (trend, isGood) => {
    if (trend === 'stable') return 'stable';
    if (isGood) return trend === 'up' ? 'positive' : 'negative';
    return trend === 'up' ? 'negative' : 'positive';
  };

  return (
    <div className={`indicator-card ${linked ? 'linked' : ''}`}>
      <div className="indicator-name">{name}</div>
      <div className="indicator-value">
        {data.value || data.avg}
        <span className="unit">{data.unit}</span>
      </div>
      <div className={`indicator-change ${getTrendClass(data.trend)}`}>
        {getTrendIcon(data.trend)} {data.change > 0 ? '+' : ''}{data.change}{data.unit}
      </div>
      {linked && <div className="linked-badge">🔗 Linked</div>}
    </div>
  );
};

// Event Card with Causal Chain
const EventCard = ({ event, onSelect, isSelected }) => {
  const getImpactClass = (impact) => {
    if (impact === 'high') return 'impact-high';
    if (impact === 'medium') return 'impact-medium';
    return 'impact-low';
  };

  return (
    <div 
      className={`event-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(event)}
    >
      <div className="event-header">
        <span className={`impact-badge ${getImpactClass(event.impact)}`}>
          {event.impact.toUpperCase()}
        </span>
        <span className="event-category">{event.category}</span>
        <span className="event-date">{event.timestamp}</span>
      </div>
      <h4 className="event-title">{event.title}</h4>
      <div className="event-meta">
        <div className="popularity-bar">
          <div className="popularity-fill" style={{ width: `${event.popularity}%` }}></div>
          <span className="popularity-text">🔥 {event.popularity}% attention</span>
        </div>
        <div className="source-tags">
          {event.sources.map((s, i) => (
            <span key={i} className="source-tag">{s}</span>
          ))}
        </div>
      </div>
    </div>
  );
};

// Causal Chain Visualization
const CausalChainView = ({ event }) => {
  if (!event) return null;

  return (
    <div className="causal-chain-panel">
      <h3>🔗 Causal Chain Analysis</h3>
      <div className="chain-title">{event.title}</div>
      <div className="chain-flow">
        {event.causalChain.map((item, idx) => (
          <React.Fragment key={idx}>
            <div className={`chain-node ${item.verified ? 'verified' : 'unverified'} ${item.needInvestigation ? 'investigate' : ''}`}>
              <div className="node-status">
                {item.verified ? '✓' : item.needInvestigation ? '🔍' : '?'}
              </div>
              <div className="node-text">{item.event}</div>
              {item.needInvestigation && (
                <div className="investigate-badge">Cần điều tra thêm</div>
              )}
            </div>
            {idx < event.causalChain.length - 1 && (
              <div className="chain-connector">↓</div>
            )}
          </React.Fragment>
        ))}
      </div>
      {event.impactOnVN && (
        <div className="vn-impact">
          <strong>🇻🇳 Impact on Vietnam:</strong> {event.impactOnVN}
        </div>
      )}
      <div className="linked-indicators-section">
        <strong>📊 Linked Indicators:</strong>
        <div className="linked-tags">
          {event.linkedIndicators.map((ind, i) => (
            <span key={i} className="linked-tag">{ind}</span>
          ))}
        </div>
      </div>
    </div>
  );
};

// Economic Calendar
const EconomicCalendar = ({ events }) => (
  <div className="calendar-section">
    <h3>📅 Economic Calendar</h3>
    <div className="calendar-list">
      {events.map((e, i) => (
        <div key={i} className={`calendar-item importance-${e.importance}`}>
          <div className="cal-date">{e.date}</div>
          <div className="cal-event">{e.event}</div>
          <div className="cal-forecast">Est: {e.forecast}</div>
        </div>
      ))}
    </div>
  </div>
);

// Main Dashboard Component
export default function MarketIntelligenceDashboard() {
  const [activeTab, setActiveTab] = useState('vietnam');
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showArchitecture, setShowArchitecture] = useState(false);
  const [processingStatus, setProcessingStatus] = useState({
    round1: 'complete',
    round2: 'complete',
    round3: 'processing',
    lastUpdate: '03/02/2026 14:30'
  });

  const currentData = activeTab === 'vietnam' ? mockVietnamData : mockGlobalData;

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1>🎯 Market Intelligence System</h1>
          <span className="subtitle">Multi-round LLM Processing • Causal Analysis • Real-time Insights</span>
        </div>
        <div className="header-right">
          <div className="processing-status">
            <div className="status-item">
              <span className="status-dot complete"></span>
              Round 1: Extract
            </div>
            <div className="status-item">
              <span className="status-dot complete"></span>
              Round 2: Link
            </div>
            <div className="status-item">
              <span className="status-dot processing"></span>
              Round 3: Reason
            </div>
          </div>
          <div className="last-update">Updated: {processingStatus.lastUpdate}</div>
          <button 
            className="arch-toggle"
            onClick={() => setShowArchitecture(!showArchitecture)}
          >
            {showArchitecture ? '📊 Dashboard' : '🔧 Architecture'}
          </button>
        </div>
      </header>

      {showArchitecture ? (
        <SystemArchitecture />
      ) : (
        <>
          {/* Tab Navigation */}
          <nav className="tab-nav">
            <button 
              className={`tab-btn ${activeTab === 'vietnam' ? 'active' : ''}`}
              onClick={() => { setActiveTab('vietnam'); setSelectedEvent(null); }}
            >
              🇻🇳 Vietnam
            </button>
            <button 
              className={`tab-btn ${activeTab === 'global' ? 'active' : ''}`}
              onClick={() => { setActiveTab('global'); setSelectedEvent(null); }}
            >
              🌍 Global
            </button>
          </nav>

          {/* Main Content */}
          <main className="dashboard-main">
            {/* Left Panel - Indicators */}
            <section className="indicators-panel">
              <h3>📊 Key Indicators</h3>
              <div className="indicators-grid">
                {Object.entries(currentData.macro).map(([key, data]) => (
                  <IndicatorCard 
                    key={key} 
                    name={key.toUpperCase()} 
                    data={data}
                    linked={selectedEvent?.linkedIndicators?.includes(key)}
                  />
                ))}
              </div>
              
              {activeTab === 'vietnam' && currentData.banking && (
                <>
                  <h3>🏦 Banking Metrics</h3>
                  <div className="indicators-grid">
                    {Object.entries(currentData.banking).map(([key, data]) => (
                      <IndicatorCard 
                        key={key} 
                        name={key.replace(/([A-Z])/g, ' $1').trim()} 
                        data={data}
                        linked={selectedEvent?.linkedIndicators?.includes(key)}
                      />
                    ))}
                  </div>
                </>
              )}
            </section>

            {/* Center Panel - Events */}
            <section className="events-panel">
              <h3>📰 Key Events (by Attention Score)</h3>
              <div className="events-list">
                {currentData.events.map(event => (
                  <EventCard 
                    key={event.id}
                    event={event}
                    onSelect={setSelectedEvent}
                    isSelected={selectedEvent?.id === event.id}
                  />
                ))}
              </div>
            </section>

            {/* Right Panel - Causal Analysis */}
            <section className="analysis-panel">
              {selectedEvent ? (
                <CausalChainView event={selectedEvent} />
              ) : (
                <div className="placeholder-panel">
                  <div className="placeholder-icon">👆</div>
                  <p>Select an event to view causal chain analysis</p>
                  <p className="placeholder-hint">
                    The system traces cause-effect relationships and highlights 
                    items that need further investigation
                  </p>
                </div>
              )}
              
              {activeTab === 'global' && mockGlobalData.calendar && (
                <EconomicCalendar events={mockGlobalData.calendar} />
              )}
            </section>
          </main>
        </>
      )}

      {/* Footer */}
      <footer className="dashboard-footer">
        <div className="footer-stats">
          <span>📄 Sources indexed: 847</span>
          <span>🔗 Causal links: 1,234</span>
          <span>💾 Memory: 2.3GB embeddings</span>
          <span>⚡ Model: Claude Sonnet + Custom Embedding</span>
        </div>
      </footer>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        .dashboard-container {
          font-family: 'Inter', -apple-system, sans-serif;
          background: #0a0a0f;
          min-height: 100vh;
          color: #e0e0e0;
        }

        /* Header */
        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 24px;
          background: linear-gradient(180deg, #12121a 0%, #0a0a0f 100%);
          border-bottom: 1px solid #1e1e2e;
        }

        .header-left h1 {
          font-size: 1.5rem;
          font-weight: 700;
          color: #fff;
          margin-bottom: 4px;
        }

        .subtitle {
          font-size: 0.75rem;
          color: #666;
          font-family: 'JetBrains Mono', monospace;
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: 24px;
        }

        .processing-status {
          display: flex;
          gap: 16px;
        }

        .status-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.75rem;
          font-family: 'JetBrains Mono', monospace;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }

        .status-dot.complete {
          background: #10b981;
          box-shadow: 0 0 8px #10b981;
        }

        .status-dot.processing {
          background: #f59e0b;
          box-shadow: 0 0 8px #f59e0b;
          animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .last-update {
          font-size: 0.7rem;
          color: #555;
          font-family: 'JetBrains Mono', monospace;
        }

        .arch-toggle {
          padding: 8px 16px;
          background: #1e1e2e;
          border: 1px solid #2e2e3e;
          border-radius: 6px;
          color: #e0e0e0;
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .arch-toggle:hover {
          background: #2e2e3e;
          border-color: #3e3e4e;
        }

        /* Tab Navigation */
        .tab-nav {
          display: flex;
          gap: 8px;
          padding: 16px 24px;
          background: #0d0d12;
        }

        .tab-btn {
          padding: 10px 24px;
          background: transparent;
          border: 1px solid #2e2e3e;
          border-radius: 8px;
          color: #888;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .tab-btn:hover {
          border-color: #4e4e5e;
          color: #ccc;
        }

        .tab-btn.active {
          background: linear-gradient(135deg, #1a1a2e 0%, #16162a 100%);
          border-color: #3b82f6;
          color: #fff;
        }

        /* Main Layout */
        .dashboard-main {
          display: grid;
          grid-template-columns: 280px 1fr 360px;
          gap: 16px;
          padding: 16px 24px;
          min-height: calc(100vh - 200px);
        }

        /* Panels */
        .indicators-panel,
        .events-panel,
        .analysis-panel {
          background: #0d0d12;
          border: 1px solid #1e1e2e;
          border-radius: 12px;
          padding: 16px;
          overflow-y: auto;
        }

        .indicators-panel h3,
        .events-panel h3,
        .analysis-panel h3,
        .calendar-section h3 {
          font-size: 0.85rem;
          color: #888;
          margin-bottom: 16px;
          font-weight: 500;
        }

        /* Indicators Grid */
        .indicators-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 8px;
          margin-bottom: 24px;
        }

        .indicator-card {
          background: #12121a;
          border: 1px solid #1e1e2e;
          border-radius: 8px;
          padding: 12px;
          transition: all 0.2s;
          position: relative;
        }

        .indicator-card.linked {
          border-color: #3b82f6;
          background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
        }

        .indicator-name {
          font-size: 0.65rem;
          color: #666;
          font-family: 'JetBrains Mono', monospace;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .indicator-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: #fff;
          margin: 4px 0;
        }

        .unit {
          font-size: 0.7rem;
          color: #666;
          margin-left: 4px;
        }

        .indicator-change {
          font-size: 0.75rem;
          font-family: 'JetBrains Mono', monospace;
        }

        .indicator-change.positive { color: #10b981; }
        .indicator-change.negative { color: #ef4444; }
        .indicator-change.stable { color: #666; }

        .linked-badge {
          position: absolute;
          top: 8px;
          right: 8px;
          font-size: 0.65rem;
          color: #3b82f6;
        }

        /* Events */
        .events-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .event-card {
          background: #12121a;
          border: 1px solid #1e1e2e;
          border-radius: 10px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .event-card:hover {
          border-color: #2e2e3e;
          transform: translateX(4px);
        }

        .event-card.selected {
          border-color: #3b82f6;
          background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
        }

        .event-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }

        .impact-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.6rem;
          font-weight: 600;
          font-family: 'JetBrains Mono', monospace;
        }

        .impact-high { background: #7f1d1d; color: #fca5a5; }
        .impact-medium { background: #78350f; color: #fcd34d; }
        .impact-low { background: #1e3a5f; color: #93c5fd; }

        .event-category {
          font-size: 0.7rem;
          color: #666;
          text-transform: uppercase;
        }

        .event-date {
          font-size: 0.7rem;
          color: #555;
          margin-left: auto;
          font-family: 'JetBrains Mono', monospace;
        }

        .event-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #e0e0e0;
          margin-bottom: 12px;
          line-height: 1.4;
        }

        .popularity-bar {
          height: 4px;
          background: #1e1e2e;
          border-radius: 2px;
          position: relative;
          margin-bottom: 8px;
        }

        .popularity-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #8b5cf6);
          border-radius: 2px;
        }

        .popularity-text {
          font-size: 0.7rem;
          color: #888;
        }

        .source-tags {
          display: flex;
          gap: 6px;
          margin-top: 8px;
        }

        .source-tag {
          padding: 2px 8px;
          background: #1e1e2e;
          border-radius: 4px;
          font-size: 0.65rem;
          color: #888;
          font-family: 'JetBrains Mono', monospace;
        }

        /* Causal Chain */
        .causal-chain-panel {
          height: 100%;
        }

        .chain-title {
          font-size: 1rem;
          font-weight: 600;
          color: #fff;
          margin-bottom: 20px;
          padding-bottom: 12px;
          border-bottom: 1px solid #1e1e2e;
        }

        .chain-flow {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .chain-node {
          background: #12121a;
          border: 1px solid #1e1e2e;
          border-radius: 8px;
          padding: 12px;
          display: flex;
          align-items: flex-start;
          gap: 10px;
          position: relative;
        }

        .chain-node.verified {
          border-left: 3px solid #10b981;
        }

        .chain-node.unverified {
          border-left: 3px solid #666;
        }

        .chain-node.investigate {
          border-left: 3px solid #f59e0b;
          background: linear-gradient(135deg, #12121a 0%, #1a1510 100%);
        }

        .node-status {
          font-size: 0.9rem;
          width: 20px;
          flex-shrink: 0;
        }

        .node-text {
          font-size: 0.85rem;
          color: #ccc;
          line-height: 1.4;
        }

        .investigate-badge {
          position: absolute;
          top: 8px;
          right: 8px;
          font-size: 0.6rem;
          color: #f59e0b;
          background: rgba(245, 158, 11, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
        }

        .chain-connector {
          text-align: center;
          color: #3b82f6;
          font-size: 0.8rem;
          padding: 2px 0;
        }

        .vn-impact {
          margin-top: 20px;
          padding: 12px;
          background: linear-gradient(135deg, #1a1a2e 0%, #1a2030 100%);
          border: 1px solid #2e2e4e;
          border-radius: 8px;
          font-size: 0.85rem;
          line-height: 1.5;
        }

        .linked-indicators-section {
          margin-top: 16px;
          font-size: 0.85rem;
        }

        .linked-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 8px;
        }

        .linked-tag {
          padding: 4px 10px;
          background: #1e1e3e;
          border: 1px solid #3b82f6;
          border-radius: 4px;
          font-size: 0.7rem;
          color: #93c5fd;
          font-family: 'JetBrains Mono', monospace;
        }

        /* Placeholder */
        .placeholder-panel {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 200px;
          text-align: center;
          color: #555;
        }

        .placeholder-icon {
          font-size: 2rem;
          margin-bottom: 12px;
        }

        .placeholder-hint {
          font-size: 0.75rem;
          color: #444;
          margin-top: 8px;
          max-width: 200px;
        }

        /* Calendar */
        .calendar-section {
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #1e1e2e;
        }

        .calendar-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .calendar-item {
          display: grid;
          grid-template-columns: 80px 1fr auto;
          gap: 12px;
          padding: 10px 12px;
          background: #12121a;
          border-radius: 6px;
          border-left: 3px solid #666;
          font-size: 0.8rem;
        }

        .calendar-item.importance-high {
          border-left-color: #ef4444;
        }

        .calendar-item.importance-medium {
          border-left-color: #f59e0b;
        }

        .cal-date {
          font-family: 'JetBrains Mono', monospace;
          color: #888;
        }

        .cal-event {
          color: #ccc;
        }

        .cal-forecast {
          color: #666;
          font-family: 'JetBrains Mono', monospace;
        }

        /* Architecture Section */
        .architecture-section {
          padding: 40px 24px;
        }

        .architecture-section h3 {
          font-size: 1.2rem;
          color: #fff;
          margin-bottom: 32px;
          text-align: center;
        }

        .arch-flow {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          margin-bottom: 40px;
          flex-wrap: wrap;
        }

        .arch-stage {
          background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
          border: 1px solid #2e2e3e;
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          min-width: 160px;
        }

        .stage-icon {
          font-size: 2rem;
          margin-bottom: 8px;
        }

        .stage-name {
          font-weight: 600;
          color: #fff;
          margin-bottom: 12px;
        }

        .stage-details {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .stage-details span {
          font-size: 0.7rem;
          color: #666;
          font-family: 'JetBrains Mono', monospace;
        }

        .arch-arrow {
          font-size: 1.5rem;
          color: #3b82f6;
        }

        .memory-layer {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 16px;
          padding: 20px 40px;
          background: linear-gradient(90deg, #0d0d12 0%, #1a1a2e 50%, #0d0d12 100%);
          border: 1px dashed #2e2e3e;
          border-radius: 8px;
          max-width: 800px;
          margin: 0 auto;
        }

        .memory-icon {
          font-size: 2rem;
        }

        .memory-text {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .memory-text strong {
          color: #fff;
        }

        .memory-text span {
          font-size: 0.75rem;
          color: #666;
          font-family: 'JetBrains Mono', monospace;
        }

        /* Footer */
        .dashboard-footer {
          padding: 12px 24px;
          background: #08080c;
          border-top: 1px solid #1e1e2e;
        }

        .footer-stats {
          display: flex;
          justify-content: center;
          gap: 32px;
          font-size: 0.7rem;
          color: #555;
          font-family: 'JetBrains Mono', monospace;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
          width: 6px;
        }

        ::-webkit-scrollbar-track {
          background: #0a0a0f;
        }

        ::-webkit-scrollbar-thumb {
          background: #2e2e3e;
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: #3e3e4e;
        }
      `}</style>
    </div>
  );
}