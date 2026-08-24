import React, { useState } from 'react';
import {
  Sliders,
  X,
  Key,
  ShieldCheck,
  ShieldAlert,
  Cpu,
  RefreshCw,
  ExternalLink,
  Trash2,
  CheckCircle2,
  HardDrive
} from 'lucide-react';
import { ProvidersStatusResponse, HardwareMetrics } from '../../types';
import { api } from '../../services/api';

interface ProviderSettingsModalProps {
  providerStatus: ProvidersStatusResponse | null;
  metrics: HardwareMetrics | null;
  onRefresh: () => void;
  onClose: () => void;
}

export const ProviderSettingsModal: React.FC<ProviderSettingsModalProps> = ({
  providerStatus,
  metrics,
  onRefresh,
  onClose
}) => {
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Models Hub & Server Links
  const [modelsHub, setModelsHub] = useState<any>(null);
  const [loadingHub, setLoadingHub] = useState(false);
  const [ollamaUrlInput, setOllamaUrlInput] = useState('http://127.0.0.1:11434');
  const [lmstudioUrlInput, setLmstudioUrlInput] = useState('http://127.0.0.1:1234/v1');
  const [updatingUrls, setUpdatingUrls] = useState(false);
  const [modelsDirInput, setModelsDirInput] = useState('');
  const [savingModelsDir, setSavingModelsDir] = useState(false);
  const [modelsDirMsg, setModelsDirMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const fetchHub = async () => {
    setLoadingHub(true);
    try {
      const data = await api.getModelsHubStatus();
      setModelsHub(data);
      if (data.ollama?.base_url) setOllamaUrlInput(data.ollama.base_url);
      if (data.lmstudio?.base_url) setLmstudioUrlInput(data.lmstudio.base_url);
      if (data.local_folder?.path) setModelsDirInput(data.local_folder.path);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHub(false);
    }
  };

  React.useEffect(() => {
    fetchHub();
  }, []);

  const handleOpenFolder = async () => {
    try {
      await api.openModelsFolder();
    } catch (e: any) {
      alert(`Could not open folder: ${e.message}`);
    }
  };

  const handleSaveModelsDir = async () => {
    if (!modelsDirInput.trim()) return;
    setSavingModelsDir(true);
    setModelsDirMsg(null);
    try {
      const res = await api.updateServerUrls({ custom_models_dir: modelsDirInput.trim() });
      setModelsDirMsg({ ok: !!res.success, text: res.message || (res.success ? 'Models folder updated.' : 'Failed to update models folder.') });
      if (res.success) {
        await fetchHub();
        onRefresh();
      }
    } catch (e: any) {
      setModelsDirMsg({ ok: false, text: `Failed: ${e.message}` });
    } finally {
      setSavingModelsDir(false);
    }
  };

  const handleSaveServerUrls = async () => {
    setUpdatingUrls(true);
    try {
      await api.updateServerUrls({
        ollama_url: ollamaUrlInput.trim(),
        lmstudio_url: lmstudioUrlInput.trim()
      });
      await fetchHub();
      onRefresh();
    } catch (e: any) {
      alert(`Failed updating server URLs: ${e.message}`);
    } finally {
      setUpdatingUrls(false);
    }
  };

  const handleSaveGeminiKey = async () => {
    if (!geminiKeyInput.trim()) return;
    setSaving(true);
    setSaveSuccessMsg(null);
    try {
      const res = await api.configureGeminiKey(geminiKeyInput.trim());
      setGeminiKeyInput('');
      setSaveSuccessMsg(res.message || 'Gemini API Key saved securely in Keychain.');
      onRefresh();
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteGeminiKey = async () => {
    if (!confirm('Are you sure you want to remove the Gemini API Key from Keychain?')) return;
    try {
      await api.deleteGeminiKey();
      onRefresh();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-xl">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">AI Engines & Model Discovery Hub</h2>
              <p className="text-xs text-slate-400">Local model weights, Ollama/LM Studio servers, and automated discovery</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6 text-xs text-slate-300">
          
          {/* 1. Local Models Folder & Finder Access */}
          <div className="bg-slate-950 p-5 rounded-2xl border border-indigo-900/40 space-y-3 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HardDrive className="w-5 h-5 text-indigo-400" />
                <div>
                  <h4 className="font-bold text-white text-sm">Local Model Weights Folder</h4>
                  <p className="text-[11px] text-slate-400">Drop offline GGUF, CTranslate2, NLLB, or MADLAD model files here</p>
                </div>
              </div>

              <button
                onClick={handleOpenFolder}
                className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/20"
              >
                <span>Open in Finder ↗</span>
              </button>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800 flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-400 truncate max-w-lg">{modelsHub?.local_folder?.path || 'data/models/'}</span>
              <span className="text-indigo-400 font-bold">{modelsHub?.local_folder?.total_size_gb || 0} GB on Disk</span>
            </div>

            {/* Change models download location (e.g. move off internal disk to an external SSD) */}
            <div className="space-y-1.5">
              <p className="text-[11px] text-slate-400">
                Running low on internal disk space? Point downloads (NLLB-200, Qari-OCR, etc.) at an external drive instead:
              </p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={modelsDirInput}
                  onChange={(e) => setModelsDirInput(e.target.value)}
                  placeholder="/Volumes/MySSD/tarjuman-models"
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono placeholder-slate-600"
                />
                <button
                  onClick={handleSaveModelsDir}
                  disabled={savingModelsDir || !modelsDirInput.trim()}
                  className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold px-3.5 py-1.5 rounded-lg whitespace-nowrap"
                >
                  {savingModelsDir ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                  <span>{savingModelsDir ? 'Saving...' : 'Use This Folder'}</span>
                </button>
              </div>
              {modelsDirMsg && (
                <div className={`text-[11px] p-2 rounded-lg border ${modelsDirMsg.ok ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' : 'bg-rose-950/40 border-rose-500/40 text-rose-300'}`}>
                  {modelsDirMsg.text}
                </div>
              )}
              <p className="text-[10px] text-slate-500">
                Applies to future downloads only — persists across restarts. Already-downloaded models stay where they are unless you move them manually.
              </p>
            </div>

            {modelsHub?.local_folder?.models?.length > 0 ? (
              <div className="divide-y divide-slate-800/80 bg-slate-900/50 rounded-xl border border-slate-800/80 p-2">
                {modelsHub.local_folder.models.map((m: any, idx: number) => (
                  <div key={idx} className="py-2 px-2 flex items-center justify-between">
                    <div>
                      <span className="font-bold text-white font-mono">{m.name}</span>
                      <span className="text-slate-500 text-[10px] ml-2">({m.type})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400 font-mono text-[10px]">{m.size_display}</span>
                      <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-1.5 py-0.5 rounded font-bold">
                        {m.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[11px] text-slate-500 bg-slate-900/40 p-3 rounded-xl border border-dashed border-slate-800 text-center">
                Folder is ready. Click "Open in Finder" and paste model folders like <code className="text-indigo-300">nllb-200-600m</code> or <code className="text-indigo-300">madlad400-7b</code> to enable them.
              </div>
            )}
          </div>

          {/* 2. Ollama & LM Studio Auto-Discovery Connections */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-white uppercase tracking-wider text-[11px] text-slate-400 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-emerald-400" />
                Local AI Server Links & Automated Discovery
              </h4>

              <button
                onClick={handleSaveServerUrls}
                disabled={updatingUrls}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
              >
                {updatingUrls ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                <span>Save & Test Connections</span>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Ollama Connection Card */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">Ollama Server Link</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                    modelsHub?.ollama?.is_connected ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {modelsHub?.ollama?.is_connected ? 'CONNECTED' : 'DISCONNECTED'}
                  </span>
                </div>

                <input
                  type="text"
                  value={ollamaUrlInput}
                  onChange={(e) => setOllamaUrlInput(e.target.value)}
                  placeholder="http://127.0.0.1:11434"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono"
                />

                <div>
                  <span className="text-[10px] text-slate-500 block mb-1">Auto-Detected Models ({modelsHub?.ollama?.model_count || 0}):</span>
                  {modelsHub?.ollama?.models?.length > 0 ? (
                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                      {modelsHub.ollama.models.map((m: any, idx: number) => (
                        <span key={idx} className="bg-slate-900 border border-slate-700 text-slate-300 px-2 py-0.5 rounded text-[10px] font-mono">
                          {m.name} <span className="text-slate-500">({m.size_display})</span>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-500 italic">No models found on Ollama daemon.</span>
                  )}
                </div>
              </div>

              {/* LM Studio Connection Card */}
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">LM Studio Server Link</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                    modelsHub?.lmstudio?.is_connected ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {modelsHub?.lmstudio?.is_connected ? 'CONNECTED' : 'DISCONNECTED'}
                  </span>
                </div>

                <input
                  type="text"
                  value={lmstudioUrlInput}
                  onChange={(e) => setLmstudioUrlInput(e.target.value)}
                  placeholder="http://127.0.0.1:1234/v1"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono"
                />

                <div>
                  <span className="text-[10px] text-slate-500 block mb-1">Auto-Detected Models ({modelsHub?.lmstudio?.model_count || 0}):</span>
                  {modelsHub?.lmstudio?.models?.length > 0 ? (
                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                      {modelsHub.lmstudio.models.map((m: any, idx: number) => (
                        <span key={idx} className="bg-slate-900 border border-slate-700 text-slate-300 px-2 py-0.5 rounded text-[10px] font-mono">
                          {m.id}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-500 italic">Start local server in LM Studio to connect.</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Section */}
          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
            <h4 className="font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Privacy & Local Processing Guarantee
            </h4>
            <p className="text-slate-400">
              When using local providers (MADLAD, NLLB, Qwen, Ollama, LM Studio), 100% of document text remains on this Mac. No telemetry, no accounts, and no data is transmitted.
            </p>
          </div>

          {/* All 5 Provider Categories */}
          <div className="space-y-3">
            <h4 className="font-bold text-white uppercase tracking-wider text-[11px] text-slate-400">All 5 Provider Categories & Backends</h4>
            
            {/* 1. Apple Translation */}
            <div className="bg-slate-950 p-4 rounded-xl border border-blue-900/40 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">Apple Native Translation</span>
                  <span className="text-blue-400 font-mono text-[10px] bg-blue-950 border border-blue-800 px-1.5 py-0.2 rounded">APPLE_LOCAL</span>
                </div>
                <p className="text-slate-400 mt-1">{providerStatus?.providers.apple_translation?.status_message || 'macOS 15+ On-Device Translation Framework'}</p>
              </div>
              <span className={`text-[10px] px-2.5 py-1 rounded font-bold ${
                providerStatus?.providers.apple_translation?.is_available ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'
              }`}>
                {providerStatus?.providers.apple_translation?.is_available ? 'AVAILABLE' : 'FRAMEWORK READY'}
              </span>
            </div>

            {/* 2. Argos Translate */}
            <div className="bg-slate-950 p-4 rounded-xl border border-emerald-900/40 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">Argos Translate (CTranslate2)</span>
                  <span className="text-emerald-400 font-mono text-[10px] bg-emerald-950 border border-emerald-800 px-1.5 py-0.2 rounded">LOCAL_MT</span>
                  <span className="text-cyan-300 font-mono text-[10px] bg-cyan-950 border border-cyan-800 px-1.5 py-0.2 rounded">Pivot: ar → en → ur</span>
                </div>
                <p className="text-slate-400 mt-1">{providerStatus?.providers.argos?.status_message || 'Local CTranslate2 Pivot Engine'}</p>
              </div>
              <span className="text-[10px] px-2.5 py-1 rounded font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                AVAILABLE
              </span>
            </div>

            {/* 3. Ollama */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">Ollama Local API</span>
                  <span className="text-purple-400 font-mono text-[10px] bg-purple-950 border border-purple-800 px-1.5 py-0.2 rounded">LOCAL_AI</span>
                  <span className="text-slate-500 font-mono text-[11px]">http://127.0.0.1:11434</span>
                </div>
                <p className="text-slate-400 mt-1">{providerStatus?.providers.ollama?.status_message || 'Ollama Daemon'}</p>
              </div>
              <span className={`text-[10px] px-2.5 py-1 rounded font-bold ${
                providerStatus?.providers.ollama?.is_available ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'
              }`}>
                {providerStatus?.providers.ollama?.is_available ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>

            {/* 4. LM Studio */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">LM Studio Local Server</span>
                  <span className="text-purple-400 font-mono text-[10px] bg-purple-950 border border-purple-800 px-1.5 py-0.2 rounded">LOCAL_AI</span>
                  <span className="text-slate-500 font-mono text-[11px]">http://127.0.0.1:1234/v1</span>
                </div>
                <p className="text-slate-400 mt-1">{providerStatus?.providers.lmstudio?.status_message || 'LM Studio OpenAI-Compatible Server'}</p>
              </div>
              <span className={`text-[10px] px-2.5 py-1 rounded font-bold ${
                providerStatus?.providers.lmstudio?.is_available ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'
              }`}>
                {providerStatus?.providers.lmstudio?.is_available ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>

            {/* 5. Public Web Translators */}
            <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/30 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">Public Web Endpoints (Google Web / Lingva / MyMemory)</span>
                  <span className="text-rose-400 font-mono text-[10px] bg-rose-950 border border-rose-800 px-1.5 py-0.2 rounded">PUBLIC_WEB</span>
                </div>
                <p className="text-slate-400 mt-1">Multi-tier public translation failover. Blocked under LOCAL_ONLY mode.</p>
              </div>
              <span className="text-[10px] px-2.5 py-1 rounded font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                AVAILABLE
              </span>
            </div>
          </div>

          {/* Cloud Provider (Gemini API) */}
          <div className="space-y-3 pt-2 border-t border-slate-800">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-white uppercase tracking-wider text-[11px] text-amber-400 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5" />
                Google Gemini API (Cloud Optional)
              </h4>
              <a
                href="https://ai.google.dev/"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-indigo-400 hover:underline flex items-center gap-1"
              >
                Google AI Studio <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Keychain Storage Status:</span>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                    providerStatus?.providers.gemini.is_available ? 'bg-emerald-950 text-emerald-300' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {providerStatus?.providers.gemini.is_available ? 'KEY CONFIGURED' : 'NOT CONFIGURED'}
                  </span>
                  {providerStatus?.providers.gemini.is_available && (
                    <button
                      onClick={handleDeleteGeminiKey}
                      className="text-rose-400 hover:text-rose-300 p-1 rounded hover:bg-slate-800"
                      title="Delete Key from Keychain"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {saveSuccessMsg && (
                <div className="bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 px-3 py-2 rounded-lg text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>{saveSuccessMsg}</span>
                </div>
              )}

              {/* Key Input */}
              <div className="flex items-center gap-2 pt-1">
                <Key className="w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  value={geminiKeyInput}
                  onChange={(e) => setGeminiKeyInput(e.target.value)}
                  placeholder="Enter or update Gemini API Key..."
                  className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500"
                />
                <button
                  onClick={handleSaveGeminiKey}
                  disabled={saving || !geminiKeyInput.trim()}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg font-bold"
                >
                  {saving ? 'Saving...' : 'Save to Keychain'}
                </button>
              </div>

              {/* Usage Stats */}
              {providerStatus && (
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80 text-[11px]">
                  <div>
                    <span className="text-slate-500 block">Today's Requests</span>
                    <span className="font-bold text-slate-200">{providerStatus.cloud_usage.today_requests}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Est. Input Tokens</span>
                    <span className="font-bold text-slate-200 font-mono">
                      {(providerStatus.cloud_usage.today_input_tokens / 1000).toFixed(1)}k
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Est. Output Tokens</span>
                    <span className="font-bold text-slate-200 font-mono">
                      {(providerStatus.cloud_usage.today_output_tokens / 1000).toFixed(1)}k
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="bg-slate-950 px-6 py-3 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Re-check Engines
          </button>

          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-lg"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
};
