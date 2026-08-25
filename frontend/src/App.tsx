import React, { useState, useEffect } from 'react';
import { Navbar } from './components/layout/Navbar';
import { HardwareMonitorBar } from './components/hardware/HardwareMonitorBar';
import { ServerActivityBar } from './components/hardware/ServerActivityBar';
import { ReviewWorkstation } from './components/review/ReviewWorkstation';
import { DocumentQueueView } from './components/queue/DocumentQueueView';
import { BenchmarkView } from './components/benchmark/BenchmarkView';
import { GlossaryManager } from './components/glossary/GlossaryManager';
import { SetupWizard } from './components/wizard/SetupWizard';
import { ProviderSettingsModal } from './components/settings/ProviderSettingsModal';
import { SimpleModeView } from './components/simple/SimpleModeView';
import { HardwareMetrics, ThrottlePolicy, ProvidersStatusResponse, ModelCapability, ProjectRecord, ServerActivity } from './types';
import { api } from './services/api';

export function App() {
  const [isSimpleMode, setIsSimpleMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('tarjuman_mode');
    return saved ? saved === 'simple' : true;
  });
  const [currentTab, setCurrentTab] = useState<'review' | 'queue' | 'benchmark' | 'glossary'>('review');
  const [metrics, setMetrics] = useState<HardwareMetrics | null>(null);
  const [throttle, setThrottle] = useState<ThrottlePolicy | null>(null);
  const [serverActivity, setServerActivity] = useState<ServerActivity | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProvidersStatusResponse | null>(null);
  const [models, setModels] = useState<ModelCapability[]>([]);
  const [activeProject, setActiveProject] = useState<ProjectRecord | null>(null);

  const [showWizard, setShowWizard] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const handleToggleMode = () => {
    setIsSimpleMode((prev) => {
      const next = !prev;
      localStorage.setItem('tarjuman_mode', next ? 'simple' : 'advanced');
      return next;
    });
  };

  // Poll hardware status every 3 seconds
  const fetchHardware = async () => {
    try {
      const data = await api.getHardwareStatus();
      setMetrics(data.metrics);
      setThrottle(data.throttle_policy);
      if (data.server_activity) {
        setServerActivity(data.server_activity);
      }
    } catch (e) {
      console.debug('Hardware polling:', e);
    }
  };

  // Poll providers status
  const fetchProviders = async () => {
    try {
      const status = await api.getProvidersStatus();
      setProviderStatus(status);
      // Auto-open wizard if system is not ready on initial load
      if (!status.system_ready && !localStorage.getItem('wizard_dismissed')) {
        setShowWizard(true);
      }
    } catch (e) {
      console.debug('Provider polling:', e);
    }
  };

  // Fetch model catalog
  const fetchModels = async () => {
    try {
      const m = await api.getModelRegistry();
      setModels(m);
    } catch (e) {
      console.debug('Model catalog fetch:', e);
    }
  };

  useEffect(() => {
    fetchHardware();
    fetchProviders();
    fetchModels();

    const hwInterval = setInterval(fetchHardware, 3000);
    const provInterval = setInterval(fetchProviders, 10000);

    return () => {
      clearInterval(hwInterval);
      clearInterval(provInterval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-600 selection:text-white">
      
      {/* Top Workstation Header */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        providerStatus={providerStatus}
        onOpenSettings={() => setShowSettings(true)}
        onOpenWizard={() => setShowWizard(true)}
        activeStrategy={activeProject?.routing_strategy || 'local_only'}
        isSimpleMode={isSimpleMode}
        onToggleSimpleMode={handleToggleMode}
      />

      {/* Real-time Hardware Telemetry Bar */}
      <HardwareMonitorBar
        metrics={metrics}
        throttle={throttle}
        activeModelName={
          activeProject
            ? (activeProject.routing_strategy === 'gemini_primary' && providerStatus?.providers.gemini.is_available)
              ? `Cloud: ${activeProject.gemini_model_id || 'gemini-3.6-flash'}`
              : (activeProject.routing_strategy === 'local_gemini_review' && providerStatus?.providers.gemini.is_available)
              ? `Local: ${activeProject.primary_model_id} + Gemini Review`
              : `Local: ${activeProject.primary_model_id || 'Auto/Local MT'}`
            : undefined
        }
      />

      {/* Live Server Process & Activity Status Bar */}
      <ServerActivityBar
        activity={serverActivity}
        onOpenSettings={() => setShowSettings(true)}
      />

      {/* Main Workstation View Area */}
      <main className="flex-1 pb-12">
        {isSimpleMode ? (
          <SimpleModeView
            activeProject={activeProject}
            onSelectProject={(proj) => setActiveProject(proj)}
            models={models}
            onSwitchToAdvanced={() => {
              setIsSimpleMode(false);
              localStorage.setItem('tarjuman_mode', 'advanced');
            }}
            onOpenWizard={() => setShowWizard(true)}
          />
        ) : (
          <>
            {currentTab === 'review' && (
              <ReviewWorkstation
                activeProject={activeProject}
                models={models}
                onProjectChange={(proj) => setActiveProject(proj)}
              />
            )}

            {currentTab === 'queue' && (
              <DocumentQueueView
                activeProject={activeProject}
                onSelectProject={(proj) => {
                  setActiveProject(proj);
                }}
                models={models}
                onOpenReview={() => setCurrentTab('review')}
                onOpenBenchmark={() => setCurrentTab('benchmark')}
                onOpenWizard={() => setShowWizard(true)}
              />
            )}

            {currentTab === 'benchmark' && (
              <BenchmarkView models={models} />
            )}

            {currentTab === 'glossary' && (
              <GlossaryManager />
            )}
          </>
        )}
      </main>

      {/* First-Run Setup & Verification Wizard */}
      {showWizard && (
        <SetupWizard
          metrics={metrics}
          providerStatus={providerStatus}
          models={models}
          onRefreshStatus={fetchProviders}
          onClose={() => {
            localStorage.setItem('wizard_dismissed', 'true');
            setShowWizard(false);
          }}
        />
      )}

      {/* Settings & Credentials Modal */}
      {showSettings && (
        <ProviderSettingsModal
          providerStatus={providerStatus}
          metrics={metrics}
          onRefresh={fetchProviders}
          onClose={() => setShowSettings(false)}
        />
      )}

    </div>
  );
}

export default App;
