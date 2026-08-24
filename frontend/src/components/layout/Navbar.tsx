import React from 'react';
import { BookOpen, ShieldCheck, ShieldAlert, Cpu, Sparkles, Sliders, Database, Layers, CheckCircle2, AlertCircle } from 'lucide-react';
import { ProvidersStatusResponse } from '../../types';

interface NavbarProps {
  currentTab: 'queue' | 'review' | 'benchmark' | 'glossary';
  setCurrentTab: (tab: 'queue' | 'review' | 'benchmark' | 'glossary') => void;
  providerStatus: ProvidersStatusResponse | null;
  onOpenSettings: () => void;
  onOpenWizard: () => void;
  activeStrategy: string;
  isSimpleMode: boolean;
  onToggleSimpleMode: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  providerStatus,
  onOpenSettings,
  onOpenWizard,
  activeStrategy,
  isSimpleMode,
  onToggleSimpleMode
}) => {
  const isCloudActive = Boolean(
    (activeStrategy.includes('gemini') || activeStrategy === 'gemini_primary' || activeStrategy === 'local_gemini_review') &&
    providerStatus?.providers.gemini.is_available
  );
  const isReady = providerStatus?.system_ready ?? false;

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-slate-100 sticky top-0 z-30 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Branding & Mode Switcher */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-tr from-indigo-600 to-emerald-500 p-2.5 rounded-xl shadow-md">
              <BookOpen className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">Tarjuman</h1>
                <span className="font-urdu text-lg text-emerald-400">ترجمان</span>
                <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">v1.0 Local</span>
              </div>
              <p className="text-xs text-slate-400">Arabic → Urdu Local Translation Workstation</p>
            </div>
          </div>

          {/* Top-Level Mode Toggle */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 ml-2">
            <button
              onClick={() => !isSimpleMode && onToggleSimpleMode()}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                isSimpleMode
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Simple Mode</span>
            </button>
            <button
              onClick={() => isSimpleMode && onToggleSimpleMode()}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                !isSimpleMode
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Advanced Workstation</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs (Visible only in Advanced Mode) */}
        {!isSimpleMode && (
          <nav className="flex items-center gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setCurrentTab('review')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'review'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Layers className="w-4 h-4" />
              Review Workstation
            </button>

            <button
              onClick={() => setCurrentTab('queue')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'queue'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              Document Queue
            </button>

            <button
              onClick={() => setCurrentTab('benchmark')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'benchmark'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Arabic Benchmark
            </button>

            <button
              onClick={() => setCurrentTab('glossary')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                currentTab === 'glossary'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Database className="w-4 h-4" />
              Glossary & TM
            </button>
          </nav>
        )}

        {/* Right Status Badges & Controls */}
        <div className="flex items-center gap-3">
          
          {/* Privacy Flag */}
          {isCloudActive ? (
            <div className="flex items-center gap-1.5 bg-amber-500/15 border border-amber-500/30 text-amber-300 px-3 py-1.5 rounded-lg text-xs font-semibold" title="Some content routed to Google Gemini API">
              <ShieldAlert className="w-4 h-4 text-amber-400 animate-pulse" />
              <span>⚠ CLOUD AI ENABLED</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 px-3 py-1.5 rounded-lg text-xs font-semibold" title="All processing occurs 100% locally on this Mac. No document text leaves this device.">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>✓ LOCAL ONLY</span>
            </div>
          )}

          {/* Engine Status */}
          <button
            onClick={onOpenWizard}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              isReady
                ? 'bg-slate-800 text-emerald-400 border-emerald-500/30 hover:bg-slate-700'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30 hover:bg-rose-500/20'
            }`}
          >
            {isReady ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5 animate-bounce" />}
            <span>{isReady ? 'ENGINE READY' : 'SETUP REQUIRED'}</span>
          </button>

          {/* Settings Modal Button */}
          <button
            onClick={onOpenSettings}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg border border-slate-700 transition-colors"
            title="AI Engine & Hardware Settings"
          >
            <Sliders className="w-4 h-4" />
          </button>
        </div>

      </div>
    </header>
  );
};
