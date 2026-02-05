import React, { useState, useEffect } from 'react';
import { RefreshCw, Activity, TrendingUp, AlertCircle, Calendar, Settings } from 'lucide-react';
import { getHealth, getLatestRun, getIndicators, getKeyEvents, getOtherNews, getInvestigations, getCalendar } from './services/api';
import { useFetch, useModal } from './hooks';
import { formatDateTime, formatRelativeTime } from './utils/format';
import IndicatorPanel from './components/IndicatorPanel';
import EventList from './components/EventList';
import EventDetail from './components/EventDetail';
import InvestigationPanel from './components/InvestigationPanel';
import InvestigationDetail from './components/InvestigationDetail';
import CalendarPanel from './components/CalendarPanel';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const [activeTab, setActiveTab] = useState('vietnam');
  const [refreshing, setRefreshing] = useState(false);
  
  // Modals
  const eventModal = useModal();
  const investigationModal = useModal();

  // Data fetching
  const { data: healthData } = useFetch(getHealth, [], true);
  const { data: latestRun, loading: runLoading, execute: refetchRun } = useFetch(getLatestRun, [], true);
  const { data: indicatorsData, loading: indicatorsLoading, execute: refetchIndicators } = useFetch(getIndicators, [], true);
  const { data: keyEventsData, loading: eventsLoading, execute: refetchEvents } = useFetch(getKeyEvents, [], true);
  const { data: otherNewsData, execute: refetchOtherNews } = useFetch(getOtherNews, [], true);
  const { data: investigationsData, loading: invLoading, execute: refetchInvestigations } = useFetch(getInvestigations, [], true);
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
        refetchInvestigations(),
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
              onClick={() => setActiveTab('investigations')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'investigations'
                  ? 'text-purple-600 border-purple-600'
                  : 'text-gray-500 border-transparent hover:text-gray-700'
              }`}
            >
              🔍 Investigations
              {investigationsData?.investigations?.length > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                  {investigationsData.investigations.length}
                </span>
              )}
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'investigations' ? (
          // Investigations View
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-purple-600" />
              Open Investigations
            </h2>
            {invLoading ? (
              <LoadingSpinner />
            ) : (
              <InvestigationPanel
                investigations={investigationsData?.investigations || []}
                onSelect={(inv) => investigationModal.open(inv)}
              />
            )}
          </div>
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
                
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Active Investigations
                  </h3>
                  <InvestigationPanel
                    investigations={(investigationsData?.investigations || []).slice(0, 3)}
                    onSelect={(inv) => investigationModal.open(inv)}
                    compact
                  />
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
              
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Investigations
                </h3>
                <InvestigationPanel
                  investigations={(investigationsData?.investigations || []).slice(0, 5)}
                  onSelect={(inv) => investigationModal.open(inv)}
                  compact
                />
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
                <span>Events today: {latestRun.run.events_extracted || 0}</span>
                <span>•</span>
                <span>Investigations: {investigationsData?.investigations?.length || 0}</span>
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

      {/* Investigation Detail Modal */}
      {investigationModal.isOpen && (
        <InvestigationDetail
          investigation={investigationModal.data}
          onClose={investigationModal.close}
        />
      )}
    </div>
  );
}

export default App;
