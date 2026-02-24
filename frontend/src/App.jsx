import React, { useState, useEffect } from 'react';
import { RefreshCw, Activity, TrendingUp, AlertCircle, Calendar, Settings, Radio, Flame, Eye } from 'lucide-react';
import { 
  getHealth, getLatestRun, getIndicators, getKeyEvents, getOtherNews, 
  getWatchlist, getCalendar, 
  createWatchlistItem, dismissWatchlistItem, snoozeWatchlistItem, 
  restoreWatchlistItem, deleteWatchlistItem,
  // Trends API (replaces separate themes/signals)
  getTrends, getTrend, getUrgentTrendsSidebar 
} from './services/api';
import { useFetch, useModal } from './hooks';
import { formatDateTime, formatRelativeTime } from './utils/format';
import IndicatorPanel from './components/IndicatorPanel';
import EventList from './components/EventList';
import EventDetail from './components/EventDetail';
import SignalDetail from './components/SignalDetail'; // Used when clicking signal in TrendDetail
import TrendsPanel from './components/TrendsPanel'; // Unified Trends dashboard
import TrendDetail from './components/TrendDetail'; // Full Trend modal view
import WatchlistPanel from './components/WatchlistPanel';
import WatchlistAddModal from './components/WatchlistAddModal';
import CalendarPanel from './components/CalendarPanel';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const [activeTab, setActiveTab] = useState('vietnam');
  const [refreshing, setRefreshing] = useState(false);
  const [watchlistAddModalOpen, setWatchlistAddModalOpen] = useState(false);
  
  // Modals
  const eventModal = useModal();
  const signalModal = useModal(); // For viewing signal from TrendDetail
  const trendModal = useModal(); // For TrendDetail

  // Data fetching
  const { data: healthData } = useFetch(getHealth, [], true);
  const { data: latestRun, loading: runLoading, execute: refetchRun } = useFetch(getLatestRun, [], true);
  const { data: indicatorsData, loading: indicatorsLoading, execute: refetchIndicators } = useFetch(getIndicators, [], true);
  const { data: keyEventsData, loading: eventsLoading, execute: refetchEvents } = useFetch(getKeyEvents, [], true);
  const { data: otherNewsData, execute: refetchOtherNews } = useFetch(getOtherNews, [], true);
  const { data: watchlistData, loading: watchlistLoading, execute: refetchWatchlist } = useFetch(getWatchlist, [], true);
  const { data: calendarData, execute: refetchCalendar } = useFetch(getCalendar, [], true);
  // Trends API with pagination (replaces separate themes/signals)
  const [trendsData, setTrendsData] = useState(null);
  const [trendsLoading, setTrendsLoading] = useState(true);
  const [trendsLoadingMore, setTrendsLoadingMore] = useState(false);

  const fetchTrends = async (offset = 0, append = false) => {
    if (append) {
      setTrendsLoadingMore(true);
    } else {
      setTrendsLoading(true);
    }
    try {
      const result = await getTrends({ offset });
      if (append && trendsData) {
        // Append new trends to existing, keep summary from fresh response
        setTrendsData({
          ...result,
          trends: [...trendsData.trends, ...result.trends],
        });
      } else {
        setTrendsData(result);
      }
    } catch (err) {
      console.error('Fetch trends failed:', err);
    } finally {
      setTrendsLoading(false);
      setTrendsLoadingMore(false);
    }
  };

  const handleLoadMoreTrends = () => {
    if (!trendsData?.has_more || trendsLoadingMore) return;
    const nextOffset = (trendsData.offset || 0) + (trendsData.limit || 30);
    fetchTrends(nextOffset, true);
  };

  const refetchTrends = () => fetchTrends(0, false);

  // Initial fetch for trends
  useEffect(() => { fetchTrends(); }, []);

  const { data: sidebarTrends, execute: refetchSidebarTrends } = useFetch(getUrgentTrendsSidebar, [], true);

  // Manual refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        refetchRun(),
        refetchIndicators(),
        refetchEvents(),
        refetchOtherNews(),
        refetchWatchlist(),
        refetchCalendar(),
        refetchTrends(),
        refetchSidebarTrends(),
      ]);
    } catch (err) {
      console.error('Refresh failed:', err);
    } finally {
      setRefreshing(false);
    }
  };

  // Filter indicators by region
  const getFilteredIndicators = () => {
    if (!indicatorsData?.groups) return {};
    
    const groups = indicatorsData.groups;
    const filtered = {};
    
    for (const [groupId, groupData] of Object.entries(groups)) {
      if (activeTab === 'vietnam' && groupId.startsWith('vietnam')) {
        filtered[groupId] = groupData;
      } else if (activeTab === 'global' && groupId.startsWith('global')) {
        filtered[groupId] = groupData;
      }
    }
    
    return filtered;
  };

  const filteredIndicators = getFilteredIndicators();

  // Watchlist handlers
  const handleAddWatchlistItem = async (data) => {
    try {
      await createWatchlistItem(data);
      refetchWatchlist();
    } catch (err) {
      console.error('Failed to add watchlist item:', err);
    }
  };

  const handleDismissWatchlistItem = async (id) => {
    try {
      await dismissWatchlistItem(id);
      refetchWatchlist();
    } catch (err) {
      console.error('Failed to dismiss watchlist item:', err);
    }
  };

  const handleSnoozeWatchlistItem = async (id, days) => {
    try {
      await snoozeWatchlistItem(id, days);
      refetchWatchlist();
    } catch (err) {
      console.error('Failed to snooze watchlist item:', err);
    }
  };

  const handleRestoreWatchlistItem = async (id) => {
    try {
      await restoreWatchlistItem(id);
      refetchWatchlist();
    } catch (err) {
      console.error('Failed to restore watchlist item:', err);
    }
  };

  const handleDeleteWatchlistItem = async (id) => {
    try {
      await deleteWatchlistItem(id);
      refetchWatchlist();
    } catch (err) {
      console.error('Failed to delete watchlist item:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-primary-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Market Intelligence</h1>
                <p className="text-xs text-gray-500">Vietnam & Global Macro Analysis</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Status indicators */}
              <div className="hidden md:flex items-center gap-2 text-sm">
                <Activity className={`w-4 h-4 ${healthData?.status === 'healthy' ? 'text-green-500' : 'text-red-500'}`} />
                <span className="text-gray-600">
                  {latestRun?.run && (
                    <>Last run: {formatRelativeTime(latestRun.run.run_time)}</>
                  )}
                </span>
              </div>

              {/* Refresh button */}
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-3 py-1.5 bg-primary-50 text-primary-700 rounded-lg hover:bg-primary-100 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex gap-1">
            <button
              onClick={() => setActiveTab('vietnam')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'vietnam'
                  ? 'text-red-600 border-red-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              🇻🇳 Vietnam
            </button>
            <button
              onClick={() => setActiveTab('global')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'global'
                  ? 'text-blue-600 border-blue-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              🌍 Global
            </button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'all'
                  ? 'text-primary-600 border-primary-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              📋 All News
            </button>
            {/* NEW: Unified Trends tab replaces separate Signals + Themes tabs */}
            <button
              onClick={() => setActiveTab('trends')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'trends'
                  ? 'text-orange-600 border-orange-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              🔥 Trends
              {trendsData?.summary?.urgent_count > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-red-100 text-red-700 rounded-full">
                  {trendsData.summary.urgent_count}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('watchlist')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'watchlist'
                  ? 'text-teal-600 border-teal-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              👁️ Watchlist
              {watchlistData?.items?.filter(i => i.status === 'triggered').length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-red-100 text-red-700 rounded-full">
                  {watchlistData.items.filter(i => i.status === 'triggered').length}
                </span>
              )}
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'trends' ? (
          // NEW: Unified Trends View (replaces separate Signals + Themes)
          <TrendsPanel
            trends={trendsData?.trends || []}
            summary={trendsData?.summary}
            onSelectTrend={(trend) => trendModal.open(trend)}
            loading={trendsLoading}
            hasMore={trendsData?.has_more || false}
            loadingMore={trendsLoadingMore}
            onLoadMore={handleLoadMoreTrends}
          />
        ) : activeTab === 'watchlist' ? (
          // Watchlist View
          <WatchlistPanel
            items={watchlistData?.items || []}
            loading={watchlistLoading}
            onAddNew={() => setWatchlistAddModalOpen(true)}
            onDismiss={handleDismissWatchlistItem}
            onSnooze={handleSnoozeWatchlistItem}
            onRestore={handleRestoreWatchlistItem}
            onDelete={handleDeleteWatchlistItem}
            onViewTheme={(theme) => { setActiveTab('trends'); trendModal.open(theme); }}
          />
        ) : activeTab === 'all' ? (
          // All News View
          <div className="space-y-6">
            <div className="grid lg:grid-cols-3 gap-6">
              {/* Key Events */}
              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">🔥 Key Events</h2>
                <EventList
                  events={keyEventsData?.events || []}
                  loading={eventsLoading}
                  onSelect={(event) => eventModal.open(event)}
                />

                <h2 className="text-lg font-semibold text-gray-900 mt-8">📰 Other News</h2>
                <EventList
                  events={otherNewsData?.events || []}
                  loading={false}
                  onSelect={(event) => eventModal.open(event)}
                  compact
                />
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                <CalendarPanel events={calendarData?.events || []} />
                
                {/* NEW: Active Trends Summary (replaces separate Themes + Signals) */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <Flame className="w-4 h-4 text-orange-500" />
                    Active Trends
                  </h3>
                  
                  {/* Urgent Trends */}
                  {sidebarTrends?.urgent?.length > 0 && (
                    <div className="mb-3">
                      <div className="text-xs text-red-600 font-medium mb-1">⚡ Urgent</div>
                      {sidebarTrends.urgent.map(trend => (
                        <div
                          key={trend.id}
                          onClick={() => { setActiveTab('trends'); trendModal.open(trend); }}
                          className="p-3 mb-2 bg-white rounded-lg border border-red-200 hover:border-red-400 cursor-pointer"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-sm">🔥</span>
                            <span className="text-sm font-medium text-gray-900 truncate">{trend.name_vi || trend.name}</span>
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {trend.signals_count} signals • Expires soon
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* Watching Trends */}
                  {sidebarTrends?.watching?.length > 0 && (
                    <div>
                      <div className="text-xs text-yellow-600 font-medium mb-1">👁 Watching</div>
                      {sidebarTrends.watching.map(trend => (
                        <div
                          key={trend.id}
                          onClick={() => { setActiveTab('trends'); trendModal.open(trend); }}
                          className="p-3 mb-2 bg-white rounded-lg border border-gray-200 hover:border-orange-300 cursor-pointer"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-sm">👁</span>
                            <span className="text-sm font-medium text-gray-900 truncate">{trend.name_vi || trend.name}</span>
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {trend.signals_count} signals
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* No trends */}
                  {(!sidebarTrends?.urgent?.length && !sidebarTrends?.watching?.length) && (
                    <div className="text-sm text-gray-400 py-2">No active trends</div>
                  )}
                  
                  {/* View all button */}
                  <button
                    onClick={() => setActiveTab('trends')}
                    className="text-sm text-primary-600 hover:text-primary-800 mt-2"
                  >
                    View all trends →
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Vietnam / Global View
          <div className="grid lg:grid-cols-4 gap-6">
            {/* Left - Indicators */}
            <div className="lg:col-span-1 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">📊 Key Indicators</h2>
              {indicatorsLoading ? (
                <LoadingSpinner />
              ) : (
                <IndicatorPanel groups={filteredIndicators} />
              )}
            </div>

            {/* Center - Events */}
            <div className="lg:col-span-2 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">🔥 Key Events</h2>
              <EventList
                events={keyEventsData?.events || []}
                loading={eventsLoading}
                onSelect={(event) => eventModal.open(event)}
              />

              {otherNewsData?.events?.length > 0 && (
                <>
                  <h2 className="text-lg font-semibold text-gray-900 mt-6">📰 Other News</h2>
                  <EventList
                    events={otherNewsData.events.slice(0, 5)}
                    loading={false}
                    onSelect={(event) => eventModal.open(event)}
                    compact
                  />
                </>
              )}
            </div>

            {/* Right - Sidebar */}
            <div className="lg:col-span-1 space-y-6">
              <CalendarPanel events={calendarData?.events || []} />
              
              {/* NEW: Active Trends (replaces separate Themes + Signals) */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  Active Trends
                </h3>
                
                {/* Urgent */}
                {sidebarTrends?.urgent?.length > 0 && (
                  <div className="mb-2">
                    <div className="text-xs text-red-600 font-medium mb-1">⚡ Urgent</div>
                    {sidebarTrends.urgent.slice(0, 2).map(trend => (
                      <div
                        key={trend.id}
                        onClick={() => { setActiveTab('trends'); trendModal.open(trend); }}
                        className="p-3 mb-2 bg-white rounded-lg border border-red-200 hover:border-red-400 cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm">🔥</span>
                          <span className="text-sm font-medium text-gray-900 truncate">{trend.name_vi || trend.name}</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{trend.signals_count} signals</div>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Watching */}
                {sidebarTrends?.watching?.length > 0 && (
                  <div>
                    <div className="text-xs text-yellow-600 font-medium mb-1">👁 Watching</div>
                    {sidebarTrends.watching.slice(0, 2).map(trend => (
                      <div
                        key={trend.id}
                        onClick={() => { setActiveTab('trends'); trendModal.open(trend); }}
                        className="p-3 mb-2 bg-white rounded-lg border border-gray-200 hover:border-orange-300 cursor-pointer"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-sm">👁</span>
                          <span className="text-sm font-medium text-gray-900 truncate">{trend.name_vi || trend.name}</span>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{trend.signals_count} signals</div>
                      </div>
                    ))}
                  </div>
                )}
                
                {(!sidebarTrends?.urgent?.length && !sidebarTrends?.watching?.length) && (
                  <div className="text-sm text-gray-400 py-2">No active trends</div>
                )}
                
                <button
                  onClick={() => setActiveTab('trends')}
                  className="text-sm text-primary-600 hover:text-primary-800 mt-2"
                >
                  View all →
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-4">
            <span>Sources: SBV, News APIs</span>
            {latestRun?.run && (
              <>
                <span>•</span>
                <span>Events: {latestRun.run.events_extracted || 0}</span>
                <span>•</span>
                <span>Trends: {trendsData?.summary?.total || 0}</span>
                <span>•</span>
                <span>⚡ Urgent: {trendsData?.summary?.urgent_count || 0}</span>
              </>
            )}
          </div>
          <div>
            {latestRun?.run && (
              <span>Last processed: {formatDateTime(latestRun.run.run_time)}</span>
            )}
          </div>
        </div>
      </footer>

      {/* Event Detail Modal */}
      {eventModal.isOpen && (
        <EventDetail
          event={eventModal.data}
          onClose={eventModal.close}
        />
      )}

      {/* Signal Detail Modal - shown when clicking a signal from TrendDetail */}
      {signalModal.isOpen && (
        <SignalDetail
          signal={signalModal.data}
          onClose={signalModal.close}
        />
      )}

      {/* Trend Detail Modal - unified view with signals */}
      {trendModal.isOpen && (
        <TrendDetail
          trend={trendModal.data}
          onClose={trendModal.close}
          onArchive={() => {
            trendModal.close();
            refetchTrends();
          }}
          onViewEvent={(event) => {
            trendModal.close();
            eventModal.open(event);
          }}
          onViewSignal={(signal) => {
            trendModal.close();
            signalModal.open(signal);
          }}
        />
      )}

      {/* Watchlist Add Modal */}
      <WatchlistAddModal
        isOpen={watchlistAddModalOpen}
        onClose={() => setWatchlistAddModalOpen(false)}
        onSubmit={handleAddWatchlistItem}
      />
    </div>
  );
}

export default App;
