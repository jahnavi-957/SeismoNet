import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  BarChart2,
  BookOpen,
  Home,
  Menu,
  Upload,
  User,
  X,
} from 'lucide-react';
import AboutProject from './pages/AboutProject';
import CSVUpload from './pages/CSVUpload';
import ModelEvaluation from './pages/ModelEvaluation';
import Overview from './pages/Overview';
import PhasePicker from './pages/PhasePicker';
import ErrorBoundary from './components/ErrorBoundary';
import { getApiErrorMessage, seismoService } from './services/api';

export type PageId = 'overview' | 'picker' | 'csv-upload' | 'evaluation' | 'about';

const pageFromPath = (): PageId => {
  const path = window.location.pathname.replace(/\/$/, '');
  if (path === '/picker') return 'picker';
  if (path === '/csv-upload') return 'csv-upload';
  if (path === '/evaluation') return 'evaluation';
  if (path === '/about') return 'about';
  return 'overview';
};

const App: React.FC = () => {
  const [activePage, setActivePage] = useState<PageId>(pageFromPath);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [serviceStatus, setServiceStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [serviceMessage, setServiceMessage] = useState('Checking backend');

  const navItems = useMemo(
    () => [
      { id: 'overview' as const, label: 'Overview', icon: <Home size={20} /> },
      { id: 'picker' as const, label: 'Phase Picker', icon: <Activity size={20} /> },
      { id: 'csv-upload' as const, label: 'CSV Upload', icon: <Upload size={20} /> },
      { id: 'evaluation' as const, label: 'Model Evaluation', icon: <BarChart2 size={20} /> },
      { id: 'about' as const, label: 'About Project', icon: <BookOpen size={20} /> },
    ],
    [],
  );

  const navigate = useCallback((page: PageId) => {
    const path = page === 'overview' ? '/' : `/${page}`;
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setActivePage(page);
  }, []);

  useEffect(() => {
    const handlePopState = () => setActivePage(pageFromPath());
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    seismoService
      .checkHealth()
      .then((health) => {
        if (cancelled) return;
        const source = typeof health.data_source === 'string' ? health.data_source : 'local backend';
        setServiceStatus('online');
        setServiceMessage(source === 'synthetic_demo_fallback' ? 'Demo data fallback' : 'Model service online');
      })
      .catch((error) => {
        if (cancelled) return;
        setServiceStatus('offline');
        setServiceMessage(getApiErrorMessage(error, 'Backend unavailable'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const pageTitle = navItems.find((item) => item.id === activePage)?.label || 'Overview';

  const pageContent = (() => {
    switch (activePage) {
      case 'picker': return <PhasePicker />;
      case 'csv-upload': return <CSVUpload />;
      case 'evaluation': return <ModelEvaluation />;
      case 'about': return <AboutProject />;
      default: return <Overview onNavigate={navigate} />;
    }
  })();

  return (
    <div className="flex min-h-screen bg-[#0a0a0c] font-sans text-slate-300">
      <aside className={`${isSidebarOpen ? 'w-64' : 'w-20'} sticky top-0 flex h-screen shrink-0 flex-col border-r border-slate-800 bg-[#0f0f12] transition-all duration-300`}>
        <button
          type="button"
          onClick={() => navigate('overview')}
          className="flex items-center gap-3 p-6 text-left"
          aria-label="Go to SeismoNet overview"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-500 font-black text-black">S</span>
          {isSidebarOpen && <span className="text-xl font-bold tracking-tight text-white">SEISMONET</span>}
        </button>

        <nav className="flex-1 space-y-2 px-4 py-6" aria-label="Primary navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => navigate(item.id)}
              title={isSidebarOpen ? undefined : item.label}
              aria-current={activePage === item.id ? 'page' : undefined}
              className={`flex w-full items-center gap-3 rounded-xl p-3 transition-all ${
                activePage === item.id
                  ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-900/20'
                  : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300'
              }`}
            >
              {item.icon}
              {isSidebarOpen && <span className="text-sm font-medium">{item.label}</span>}
            </button>
          ))}
        </nav>

        <div className="border-t border-slate-800 p-4">
          <button
            type="button"
            onClick={() => setIsSidebarOpen((open) => !open)}
            className="flex w-full justify-center rounded-lg bg-slate-800 p-2 text-slate-400 transition-colors hover:text-white"
            aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {isSidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-800 bg-[#0a0a0c]/90 px-6 py-4 backdrop-blur-md sm:px-8">
          <div className="flex items-center gap-4">
            <h1 className="font-medium text-white">{pageTitle}</h1>
            <div className="hidden items-center gap-2 rounded-full border border-slate-800 bg-slate-900 px-2 py-1 sm:flex">
              <span className={`h-2 w-2 rounded-full ${serviceStatus === 'online' ? 'bg-green-500' : serviceStatus === 'offline' ? 'bg-red-500' : 'bg-amber-400 animate-pulse'}`} />
              <span className="max-w-48 truncate text-[10px] font-mono text-slate-400" title={serviceMessage}>{serviceMessage}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs font-bold text-white">SeismoNet v1.0</p>
              <p className="text-[10px] text-slate-500">Academic Prototype</p>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-slate-400" aria-label="Academic prototype status">
              <User size={20} />
            </div>
          </div>
        </header>

        <ErrorBoundary key={activePage}>
          {pageContent}
        </ErrorBoundary>
      </main>
    </div>
  );
};

export default App;
