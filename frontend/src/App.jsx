import React, { useState, useEffect } from 'react';
import { RefreshCw, Activity, TrendingUp, AlertCircle, Calendar, Settings, Radio, Flame, Eye } from 'lucide-react';
import { getHealth, getLatestRun, getIndicators, getKeyEvents, getOtherNews, getSignals, getSignalAccuracy, getThemes, getWatchlist, getCalendar, createWatchlistItem, dismissWatchlistItem, snoozeWatchlistItem, restoreWatchlistItem, deleteWatchlistItem } from './services/api';
import { useFetch, useModal } from './hooks';
import { formatDateTime, formatRelativeTime } from './utils/format';
import IndicatorPanel from './components/IndicatorPanel';
import EventList from './components/EventList';
import EventDetail from './components/EventDetail';
import SignalPanel from './components/SignalPanel';
import SignalDetail from './components/SignalDetail';
import ThemePanel from './components/ThemePanel';
import ThemeDetail from './components/ThemeDetail';
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
  const signalModal = useModal();
  const themeModal = useModal();

  // Data fetching
  const { data: healthData } = useFetch(getHealth, [], true);
  const { data: latestRun, loading: runLoading, execute: refetchRun } = useFetch(getLatestRun, [], true);
  const { data: indicatorsData, loading: indicatorsLoading, execute: refetchIndicators } = useFetch(getIndicators, [], true);
  const { data: keyEventsData, loading: eventsLoading, execute: refetchEvents } = useFetch(getKeyEvents, [], true);
  const { data: otherNewsData, execute: refetchOtherNews } = useFetch(getOtherNews, [], true);
  const { data: signalsData, loading: signalsLoading, execute: refetchSignals } = useFetch(getSignals, [], true);
  const { data: accuracyData, execute: refetchAccuracy } = useFetch(getSignalAccuracy, [], true);
  const { data: themesData, loading: themesLoading, execute: refetchThemes } = useFetch(getThemes, [], true);
  const { data: watchlistData, loading: watchlistLoading, execute: refetchWatchlist } = useFetch(getWatchlist, [], true);
  const { data: calendarData, execute: refetchCalendar } = useFetch(getCalendar, [], true);

  // Manual refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        refetchRun(),
        refetchIndicators(),
        refetchEvents(),
        refetchOtherNews(),
        refetchSignals(),
        refetchAccuracy(),
        refetchThemes(),
        refetchWatchlist(),
        refetchCalendar(),
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
            <button
              onClick={() => setActiveTab('signals')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'signals'
                  ? 'text-purple-600 border-purple-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              📡 Signals
              {signalsData?.signals?.filter(s => s.status === 'pending').length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                  {signalsData.signals.filter(s => s.status === 'pending').length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('themes')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'themes'
                  ? 'text-orange-600 border-orange-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              🔥 Themes
              {themesData?.themes?.filter(t => t.status === 'active').length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-orange-100 text-orange-700 rounded-full">
                  {themesData.themes.filter(t => t.status === 'active').length}
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
        {activeTab === 'signals' ? (
          // Signals View
          <SignalPanel
            signals={signalsData?.signals || []}
            accuracyStats={accuracyData}
            onSelectSignal={(signal) => signalModal.open(signal)}
            loading={signalsLoading}
          />
        ) : activeTab === 'themes' ? (
          // Themes View
          <ThemePanel
            themes={themesData?.themes || []}
            onSelectTheme={(theme) => themeModal.open(theme)}
            loading={themesLoading}
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
            onViewTheme={(theme) => { setActiveTab('themes'); themeModal.open(theme); }}
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
                
                {/* Active Themes Summary */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <Flame className="w-4 h-4 text-orange-500" />
                    Active Themes
                  </h3>
                  {themesData?.themes?.filter(t => t.status === 'active').slice(0, 3).map(theme => (
                    <div
                      key={theme.id}
                      onClick={() => { setActiveTab('themes'); themeModal.open(theme); }}
                      className="p-3 mb-2 bg-white rounded-lg border border-gray-200 hover:border-orange-300 cursor-pointer"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm">🔥</span>
                        <span className="text-sm font-medium text-gray-900 truncate">{theme.name_vi || theme.name}</span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">Strength: {theme.strength?.toFixed(1)}</div>
                    </div>
                  ))}
                </div>

                {/* Active Signals Summary */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <Radio className="w-4 h-4 text-purple-500" />
                    Active Signals
                  </h3>
                  {signalsData?.signals?.filter(s => s.status === 'pending').slice(0, 3).map(signal => (
                    <div
                      key={signal.id}
                      onClick={() => { setActiveTab('signals'); signalModal.open(signal); }}
                      className="p-3 mb-2 bg-white rounded-lg border border-gray-200 hover:border-purple-300 cursor-pointer"
                    >
                      <div className="text-sm font-medium text-gray-900 line-clamp-2">{signal.prediction_text}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {signal.target_indicator} • {signal.confidence}
                      </div>
                    </div>
                  ))}
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
              
              {/* Active Themes */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  Themes
                </h3>
                {themesData?.themes?.filter(t => t.status === 'active' || t.strength >= 5).slice(0, 3).map(theme => (
                  <div
                    key={theme.id}
                    onClick={() => { setActiveTab('themes'); themeModal.open(theme); }}
                    className="p-3 mb-2 bg-white rounded-lg border border-gray-200 hover:border-orange-300 cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm">🔥</span>
                      <span className="text-sm font-medium text-gray-900 truncate">{theme.name_vi || theme.name}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Strength: {theme.strength?.toFixed(1)}</div>
                  </div>
                ))}
                {(!themesData?.themes || themesData.themes.filter(t => t.status === 'active' || t.strength >= 5).length === 0) && (
                  <div className="text-sm text-gray-400 py-2">No active themes</div>
                )}
              </div>
              
              {/* Active Signals */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Radio className="w-4 h-4 text-purple-500" />
                  Signals
                </h3>
                {signalsData?.signals?.filter(s => s.status === 'pending').slice(0, 3).map(signal => (
                  <div
                    key={signal.id}
                    onClick={() => { setActiveTab('signals'); signalModal.open(signal); }}
                    className="p-3 mb-2 bg-white rounded-lg border border-gray-200 hover:border-purple-300 cursor-pointer"
                  >
                    <div className="text-sm font-medium text-gray-900 line-clamp-2">{signal.prediction_text}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {signal.target_indicator} • {signal.confidence}
                    </div>
                  </div>
                ))}
                {(!signalsData?.signals || signalsData.signals.filter(s => s.status === 'pending').length === 0) && (
                  <div className="text-sm text-gray-400 py-2">No active signals</div>
                )}
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
                <span>Signals: {signalsData?.signals?.filter(s => s.status === 'pending').length || 0}</span>
                <span>•</span>
                <span>Themes: {themesData?.themes?.filter(t => t.status === 'active').length || 0}</span>
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

      {/* Signal Detail Modal */}
      {signalModal.isOpen && (
        <SignalDetail
          signal={signalModal.data}
          onClose={signalModal.close}
        />
      )}

      {/* Theme Detail Modal */}
      {themeModal.isOpen && (
        <ThemeDetail
          theme={themeModal.data}
          onClose={themeModal.close}
          onViewEvent={(event) => {
            themeModal.close();
            eventModal.open(event);
          }}
          onViewSignal={(signal) => {
            themeModal.close();
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
