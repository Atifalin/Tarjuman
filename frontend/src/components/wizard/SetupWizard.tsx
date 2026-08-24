import React, { useState, useEffect } from 'react';
import {
  Cpu,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ExternalLink,
  Key,
  RefreshCw,
  Zap,
  Check,
  Play,
  Download,
  Terminal,
  Server,
  Layers
} from 'lucide-react';
import { HardwareMetrics, ProvidersStatusResponse, ModelCapability, SystemDependenciesResponse, PyTorchVerifyResponse, ArgosVerifyResponse } from '../../types';
import { api } from '../../services/api';

interface SetupWizardProps {
  metrics: HardwareMetrics | null;
  providerStatus: ProvidersStatusResponse | null;
  models: ModelCapability[];
  onRefreshStatus: () => void;
  onClose: () => void;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({
  metrics,
  providerStatus,
  models,
  onRefreshStatus,
  onClose
}) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [deps, setDeps] = useState<SystemDependenciesResponse | null>(null);
  
  // PyTorch Install State
  const [installingTorch, setInstallingTorch] = useState(false);
  const [installLogs, setInstallLogs] = useState<string>('');
  const [showLogs, setShowLogs] = useState(false);
  const [verifyResult, setVerifyResult] = useState<PyTorchVerifyResponse | null>(null);
  const [verifyingTorch, setVerifyingTorch] = useState(false);

  // Argos Install State
  const [installingArgos, setInstallingArgos] = useState(false);
  const [verifyingArgos, setVerifyingArgos] = useState(false);
  const [argosVerifyResult, setArgosVerifyResult] = useState<ArgosVerifyResponse | null>(null);

  // NLLB-200 1.3B Install State
  const [installingNLLB, setInstallingNLLB] = useState(false);

  // Qari-OCR MLX Install State
  const [installingMLXOcr, setInstallingMLXOcr] = useState(false);
  const [startingMLXServer, setStartingMLXServer] = useState(false);
  const [mlxServerMsg, setMlxServerMsg] = useState<string | null>(null);

  // Ollama State
  const [startingOllama, setStartingOllama] = useState(false);
  const [pullingModel, setPullingModel] = useState(false);
  const [ollamaMsg, setOllamaMsg] = useState<string | null>(null);

  // Gemini State
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [geminiSaving, setGeminiSaving] = useState(false);
  const [wizardSaveMsg, setWizardSaveMsg] = useState<string | null>(null);

  // Step 4 Test State
  const [testSelection, setTestSelection] = useState('public_web|google-web-unofficial');
  const [testModelId, setTestModelId] = useState('google-web-unofficial');
  const [testProvider, setTestProvider] = useState('public_web');
  const [testRunning, setTestRunning] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  const fetchDependencies = async () => {
    try {
      const data = await api.getDependencies();
      setDeps(data);
      if (data.install_state.status === 'installing') {
        if (data.install_state.target === 'argos') setInstallingArgos(true);
        else if (data.install_state.target === 'nllb') setInstallingNLLB(true);
        else if (data.install_state.target === 'mlx_ocr') setInstallingMLXOcr(true);
        else setInstallingTorch(true);
        setInstallLogs(data.install_state.logs);
      }
    } catch (e) {
      console.debug('Failed to fetch dependencies:', e);
    }
  };

  useEffect(() => {
    fetchDependencies();
  }, []);

  // Poll install status if installing
  useEffect(() => {
    let interval: any;
    if (installingTorch || installingArgos || installingNLLB || installingMLXOcr) {
      interval = setInterval(async () => {
        try {
          const st = await api.getInstallStatus();
          setInstallLogs(st.logs || '');
          if (st.status === 'completed' || st.status === 'failed') {
            setInstallingTorch(false);
            setInstallingArgos(false);
            setInstallingNLLB(false);
            setInstallingMLXOcr(false);
            fetchDependencies();
            onRefreshStatus();
          }
        } catch (e) {
          console.debug(e);
        }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [installingTorch, installingArgos, installingNLLB, installingMLXOcr]);

  const handleInstallPyTorch = async () => {
    setInstallingTorch(true);
    setShowLogs(true);
    setInstallLogs('Initiating Apple Silicon PyTorch & Transformers installation...\n');
    try {
      await api.installPyTorch();
    } catch (e: any) {
      alert(`Install error: ${e.message}`);
      setInstallingTorch(false);
    }
  };

  const handleInstallArgos = async () => {
    setInstallingArgos(true);
    setShowLogs(true);
    setInstallLogs('Initiating Argos Translate & offline Arabic/Urdu models installation (~90 MB)...\n');
    try {
      await api.installArgos();
    } catch (e: any) {
      alert(`Install error: ${e.message}`);
      setInstallingArgos(false);
    }
  };

  const handleInstallNLLB = async () => {
    setInstallingNLLB(true);
    setShowLogs(true);
    setInstallLogs('Initiating NLLB-200 1.3B download & CTranslate2 int8 conversion (~2.6 GB)...\n');
    try {
      await api.installNLLB();
    } catch (e: any) {
      alert(`Install error: ${e.message}`);
      setInstallingNLLB(false);
    }
  };

  const handleInstallMLXOcr = async () => {
    setInstallingMLXOcr(true);
    setShowLogs(true);
    setInstallLogs('Initiating mlx / mlx-vlm install & Qari-OCR-0.4.0 MLX 4-bit conversion (~2.5 GB)...\n');
    try {
      await api.installMLXOcr();
    } catch (e: any) {
      alert(`Install error: ${e.message}`);
      setInstallingMLXOcr(false);
    }
  };

  const handleStartMLXServer = async () => {
    setStartingMLXServer(true);
    setMlxServerMsg(null);
    try {
      const res = await api.startMLXServer();
      setMlxServerMsg(res.message);
      await fetchDependencies();
      onRefreshStatus();
    } catch (e: any) {
      setMlxServerMsg(`Failed: ${e.message}`);
    } finally {
      setStartingMLXServer(false);
    }
  };

  const handleVerifyArgos = async () => {
    setVerifyingArgos(true);
    setArgosVerifyResult(null);
    try {
      const res = await api.verifyArgos();
      setArgosVerifyResult(res);
      await fetchDependencies();
      onRefreshStatus();
    } catch (e: any) {
      setArgosVerifyResult({ success: false, installed: false, packages_installed: false, message: e.message });
    } finally {
      setVerifyingArgos(false);
    }
  };

  const handleVerifyPyTorch = async () => {
    setVerifyingTorch(true);
    setVerifyResult(null);
    try {
      const res = await api.verifyPyTorch();
      setVerifyResult(res);
      await fetchDependencies();
      onRefreshStatus();
    } catch (e: any) {
      setVerifyResult({ success: false, installed: false, mps_available: false, message: e.message });
    } finally {
      setVerifyingTorch(false);
    }
  };

  const handleStartOllama = async () => {
    setStartingOllama(true);
    setOllamaMsg(null);
    try {
      const res = await api.startOllama();
      setOllamaMsg(res.message);
      await fetchDependencies();
      onRefreshStatus();
    } catch (e: any) {
      setOllamaMsg(`Failed: ${e.message}`);
    } finally {
      setStartingOllama(false);
    }
  };

  const handlePullQwen = async () => {
    setPullingModel(true);
    setOllamaMsg('Pulling Qwen3 8B in Ollama (this may take a few minutes)...');
    try {
      const res = await api.pullOllamaModel('qwen3:8b');
      setOllamaMsg(res.message);
      await fetchDependencies();
      onRefreshStatus();
    } catch (e: any) {
      setOllamaMsg(`Pull failed: ${e.message}`);
    } finally {
      setPullingModel(false);
    }
  };

  const handleSaveGeminiKey = async () => {
    if (!geminiKeyInput.trim()) return;
    setGeminiSaving(true);
    setWizardSaveMsg(null);
    try {
      const res = await api.configureGeminiKey(geminiKeyInput.trim());
      onRefreshStatus();
      await fetchDependencies();
      setGeminiKeyInput('');
      setWizardSaveMsg(res.message || 'Key saved successfully in Keychain!');
    } catch (e: any) {
      alert(`Error saving Gemini API Key: ${e.message}`);
    } finally {
      setGeminiSaving(false);
    }
  };

  const handleRunLiveTest = async () => {
    setTestRunning(true);
    setTestResult(null);
    try {
      const res = await api.testModel(testProvider, testModelId);
      setTestResult(res);
      onRefreshStatus();
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    } finally {
      setTestRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Wizard Header */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-xl">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Tarjuman Setup & Engine Wizard</h2>
              <p className="text-xs text-slate-400">Step {step} of 4: Environment & Engine Verification</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xs px-3 py-1.5 bg-slate-800 rounded-lg hover:bg-slate-700">
            Close
          </button>
        </div>

        {/* Wizard Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          
          {/* STEP 1: HARDWARE CHECK */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-indigo-400" />
                1. Mac Hardware & Unified Memory Profile
              </h3>
              <p className="text-xs text-slate-300">
                Tarjuman is built from the ground up for Apple Silicon unified memory (Metal / MPS).
              </p>

              {metrics && (
                <div className="grid grid-cols-2 gap-4 mt-3">
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
                    <span className="text-xs text-slate-400">Apple Silicon Processor</span>
                    <p className="text-sm font-semibold text-emerald-400">{metrics.chip_name}</p>
                    <span className="text-[11px] text-slate-500">
                      {metrics.is_apple_silicon ? '✓ Apple Silicon Architecture Detected' : 'Generic CPU'}
                    </span>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1">
                    <span className="text-xs text-slate-400">Unified Memory (RAM)</span>
                    <p className="text-sm font-semibold text-indigo-300">
                      {metrics.total_ram_gb} GB Unified RAM
                    </p>
                    <span className="text-[11px] text-slate-500 font-mono">
                      Profile: {metrics.hardware_profile.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              )}

              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-2">
                <div className="font-semibold text-slate-200">Adaptive Production Engine Routing & Dual-Bridge Architecture:</div>
                <p className="text-slate-400 leading-relaxed">
                  Tarjuman combines fast local MT, on-device intelligence, and scholarly human review:
                </p>
                <div className="grid grid-cols-2 gap-2 pt-1 text-[11px] font-mono">
                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1">
                    <span className="text-emerald-400 font-bold block">1. Arabic → Urdu Engines</span>
                    <span className="text-slate-400 block leading-tight">Argos Translate (CTranslate2), Qwen3 8B, Meta NLLB-200, or Google MADLAD-400</span>
                  </div>
                  <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1">
                    <span className="text-blue-400 font-bold block">2. Arabic → English Reference</span>
                    <span className="text-slate-400 block leading-tight">Apple Native Translation (100% On-Device macOS 15+ Neural Engine) & Qwen3 8B</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: 5-TIER PROVIDER TAXONOMY & ENGINE MANAGER */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <Server className="w-5 h-5 text-indigo-400" />
                  2. All 5 Translation Provider Categories
                </h3>
                <p className="text-xs text-slate-300 mt-0.5">
                  Verify your local engines, on-device Apple Translation, and optional cloud connectors.
                </p>
              </div>

              {/* 1. APPLE_LOCAL: Apple Translation Framework */}
              <div className="bg-slate-950 p-4 rounded-xl border border-blue-900/40 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">Apple Native Translation</span>
                      <span className="text-[10px] bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded font-bold">
                        APPLE_LOCAL (macOS 15+)
                      </span>
                      <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">
                        ✓ READY (ar → en Reference Bridge)
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      100% on-device Neural Engine translation for the <strong>English Reference panel</strong> in the Review Workstation. Zero cloud transmission, zero RAM overhead.
                    </p>
                  </div>
                </div>
              </div>

              {/* 2. LOCAL_MT: Argos Translate & PyTorch Seq2Seq */}
              <div className="bg-slate-950 p-4 rounded-xl border border-emerald-900/40 space-y-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-sm">Dedicated Machine Translation (Seq2Seq / CTranslate2)</span>
                    <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">
                      LOCAL_MT (100% Offline)
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Specialized sequence-to-sequence neural translation engines running locally on Apple Silicon.
                  </p>
                </div>

                {/* Argos Translate */}
                <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-200">Argos Translate (CTranslate2)</span>
                        <span className="text-[10px] text-cyan-300 font-mono bg-cyan-950/80 px-1.5 py-0.2 rounded border border-cyan-800">
                          Pivot: ar → en → ur
                        </span>
                        {deps?.argos?.installed && deps.argos.packages_installed ? (
                          <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold font-mono">
                            ✓ READY (OFFLINE)
                          </span>
                        ) : deps?.argos?.installed ? (
                          <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-bold font-mono">
                            📦 PACKAGES MISSING (~90 MB)
                          </span>
                        ) : (
                          <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded font-bold font-mono">
                            NOT INSTALLED (~90 MB)
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Fast, lightweight local OpenNMT models with intermediate English bridge recording. 100% offline.
                      </p>
                    </div>

                    <div>
                      {!(deps?.argos?.installed && deps.argos.packages_installed) ? (
                        <button
                          onClick={handleInstallArgos}
                          disabled={installingArgos}
                          className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs px-3.5 py-1.5 rounded-lg font-bold shadow-md transition-all"
                        >
                          {installingArgos ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                          <span>{installingArgos ? 'Downloading (~90MB)...' : 'Install Argos (~90 MB)'}</span>
                        </button>
                      ) : (
                        <button
                          onClick={handleVerifyArgos}
                          disabled={verifyingArgos}
                          className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 font-mono"
                        >
                          {verifyingArgos ? <RefreshCw className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3 text-emerald-400 inline mr-1" />}
                          Verify Argos
                        </button>
                      )}
                    </div>
                  </div>

                  {argosVerifyResult && (
                    <div className={`text-xs p-2 rounded-lg border ${argosVerifyResult.success ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' : 'bg-rose-950/40 border-rose-500/40 text-rose-300'}`}>
                      {argosVerifyResult.message}
                    </div>
                  )}
                </div>

                {/* Meta NLLB-200 1.3B (direct ar -> ur, CTranslate2 int8) */}
                <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-200">Meta NLLB-200 1.3B Distilled (CTranslate2)</span>
                        <span className="text-[10px] text-cyan-300 font-mono bg-cyan-950/80 px-1.5 py-0.2 rounded border border-cyan-800">
                          Direct: ar → ur
                        </span>
                        {deps?.readiness_matrix?.['nllb-200-distilled-1.3b']?.ready ? (
                          <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold font-mono">
                            ✓ READY (OFFLINE)
                          </span>
                        ) : (
                          <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded font-bold font-mono">
                            NOT INSTALLED (~2.6 GB)
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {deps?.readiness_matrix?.['nllb-200-distilled-1.3b']?.reason || 'Best accuracy/speed local direct Arabic → Urdu engine. Quantized int8, no accuracy loss vs. full precision, native Apple Silicon CPU.'}
                      </p>
                    </div>

                    <div>
                      {!deps?.readiness_matrix?.['nllb-200-distilled-1.3b']?.ready && (
                        <button
                          onClick={handleInstallNLLB}
                          disabled={installingNLLB}
                          className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs px-3.5 py-1.5 rounded-lg font-bold shadow-md transition-all"
                        >
                          {installingNLLB ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                          <span>{installingNLLB ? 'Downloading & Converting...' : 'Install NLLB-200 1.3B (~2.6 GB)'}</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* PyTorch & Transformers */}
                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-200">PyTorch & Transformers (MADLAD-400 / NLLB-200)</span>
                      {deps?.pytorch.installed ? (
                        <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">
                          ✓ INSTALLED ({deps.pytorch.torch_version})
                        </span>
                      ) : (
                        <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded font-bold">
                          NOT INSTALLED
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Required for <strong>MADLAD-400 7B MT</strong> (`&lt;2ur&gt;`) and <strong>Meta NLLB-200 3.3B</strong>.
                    </p>
                  </div>
                  <div>
                    {!deps?.pytorch.installed ? (
                      <button
                        onClick={handleInstallPyTorch}
                        disabled={installingTorch}
                        className="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg font-bold"
                      >
                        {installingTorch ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                        <span>{installingTorch ? 'Installing...' : 'Install PyTorch'}</span>
                      </button>
                    ) : (
                      <button
                        onClick={handleVerifyPyTorch}
                        disabled={verifyingTorch}
                        className="text-xs bg-slate-800 hover:bg-slate-750 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700 font-mono"
                      >
                        Verify MPS
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* 3. LOCAL_AI: Ollama & Qwen3 */}
              <div className="bg-slate-950 p-4 rounded-xl border border-purple-900/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">Local LLMs (Ollama / LM Studio)</span>
                      <span className="text-[10px] bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded font-bold">
                        LOCAL_AI (100% Offline)
                      </span>
                      {deps?.ollama.running ? (
                        <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">
                          ✓ CONNECTED (127.0.0.1:11434)
                        </span>
                      ) : (
                        <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded font-bold">
                          OLLAMA NOT RUNNING
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Runs <strong>Qwen3 8B</strong> for local Arabic review, translation, and English reference.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {!deps?.ollama.running ? (
                      <button
                        onClick={handleStartOllama}
                        disabled={startingOllama}
                        className="flex items-center gap-1 text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg font-bold shadow-md"
                      >
                        {startingOllama ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                        <span>Start Ollama</span>
                      </button>
                    ) : !deps.ollama.qwen3_installed ? (
                      <button
                        onClick={handlePullQwen}
                        disabled={pullingModel}
                        className="flex items-center gap-1 text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg font-bold shadow-md"
                      >
                        {pullingModel ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                        <span>Pull Qwen3 8B</span>
                      </button>
                    ) : (
                      <span className="text-[11px] text-emerald-400 font-mono font-bold bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded-lg">
                        ✓ Qwen3 8B Ready
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* LOCAL_AI: Qari-OCR-0.4.0 Native MLX Arabic OCR */}
              {(metrics?.is_apple_silicon && (metrics?.total_ram_gb ?? 0) >= 16) && (
                <div className="bg-slate-950 p-4 rounded-xl border border-purple-900/40 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white text-sm">Qari-OCR-0.4.0 (Native MLX Arabic OCR)</span>
                        <span className="text-[10px] bg-purple-950 text-purple-300 border border-purple-800 px-2 py-0.5 rounded font-bold">
                          LOCAL_AI · MLX
                        </span>
                        {deps?.readiness_matrix?.['qari-ocr-0.4.0-vl-4b']?.ready ? (
                          <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">
                            ✓ READY (127.0.0.1:8082)
                          </span>
                        ) : (
                          <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded font-bold">
                            NOT READY
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        {deps?.readiness_matrix?.['qari-ocr-0.4.0-vl-4b']?.reason || 'Best local Arabic manuscript/book OCR, fine-tuned for Islamic texts. Runs natively on Apple Silicon GPU via MLX — zero cloud, no Ollama dependency.'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      {deps?.mlx?.server_running ? (
                        <span className="text-[11px] text-emerald-400 font-mono font-bold bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded-lg">
                          ✓ Server Running
                        </span>
                      ) : deps?.mlx?.installed && deps?.mlx?.weights_exist ? (
                        <button
                          onClick={handleStartMLXServer}
                          disabled={startingMLXServer}
                          className="flex items-center gap-1 text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-3 py-1.5 rounded-lg font-bold shadow-md"
                        >
                          {startingMLXServer ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                          <span>Start MLX Server</span>
                        </button>
                      ) : (
                        <button
                          onClick={handleInstallMLXOcr}
                          disabled={installingMLXOcr}
                          className="flex items-center gap-1.5 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs px-3.5 py-1.5 rounded-lg font-bold shadow-md transition-all"
                        >
                          {installingMLXOcr ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                          <span>{installingMLXOcr ? 'Downloading & Converting...' : 'Install Qari-OCR MLX (~2.5 GB)'}</span>
                        </button>
                      )}
                    </div>
                  </div>
                  {mlxServerMsg && (
                    <div className="text-xs p-2 rounded-lg border bg-slate-900/60 border-slate-800 text-slate-300">
                      {mlxServerMsg}
                    </div>
                  )}
                </div>
              )}

              {/* 4. PUBLIC_WEB: Web Translation Endpoints */}
              <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/30 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">Public Web Translators (Google Web, Lingva, MyMemory)</span>
                      <span className="text-[10px] bg-rose-950 text-rose-300 border border-rose-800 px-2 py-0.5 rounded font-bold">
                        PUBLIC_WEB (Opt-In)
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Free public translation endpoints with rate-limit rotation. Blocked automatically in <code>LOCAL_ONLY</code> mode.
                    </p>
                  </div>
                  <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold font-mono">
                    ✓ AVAILABLE
                  </span>
                </div>
              </div>

              {/* 5. CLOUD_AI: Google Gemini */}
              <div className="bg-slate-950 p-4 rounded-xl border border-amber-900/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">Google Gemini Cloud (gemini-3.6-flash / pro)</span>
                      <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-bold">
                        CLOUD_AI (Opt-In)
                      </span>
                      {providerStatus?.providers.gemini?.is_available ? (
                        <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-2 py-0.5 rounded font-bold">
                          ✓ KEY CONFIGURED
                        </span>
                      ) : (
                        <span className="text-[10px] bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded font-bold">
                          KEY NOT SET
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Fast, scholarly Arabic → Urdu cloud translation (API key stored in macOS Keychain). Blocked in <code>LOCAL_ONLY</code> mode.
                    </p>
                  </div>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Get API Key
                  </a>
                </div>

                <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                  <Key className="w-4 h-4 text-slate-400" />
                  <input
                    type="password"
                    value={geminiKeyInput}
                    onChange={(e) => setGeminiKeyInput(e.target.value)}
                    placeholder="Paste Gemini API Key (generativelanguage.googleapis.com)..."
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    onClick={handleSaveGeminiKey}
                    disabled={geminiSaving || !geminiKeyInput.trim()}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg font-medium transition-colors"
                  >
                    {geminiSaving ? 'Saving...' : 'Save to Keychain'}
                  </button>
                </div>
              </div>

              {/* Live Installation Progress Terminal */}
              {(installingTorch || installingArgos || installingNLLB || installingMLXOcr || installLogs) && (
                <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-200 flex items-center gap-1.5">
                      <Terminal className="w-4 h-4 text-emerald-400" />
                      Live Installation & Download Logs
                    </span>
                    {(installingTorch || installingArgos || installingNLLB || installingMLXOcr) && (
                      <span className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px] font-bold">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> In Progress...
                      </span>
                    )}
                  </div>
                  <pre className="bg-slate-900 text-[11px] font-mono text-emerald-300 p-3 rounded-lg max-h-48 overflow-y-auto whitespace-pre-wrap border border-slate-800">
                    {installLogs || 'Connecting to package repository...'}
                  </pre>
                </div>
              )}

            </div>
          )}

          {/* STEP 3: MODEL READINESS MATRIX */}
          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                3. Live Model Readiness Matrix
              </h3>
              <p className="text-xs text-slate-300">
                Current operational readiness for each supported Arabic → Urdu model:
              </p>

              <div className="space-y-2.5 max-h-[350px] overflow-y-auto pr-1">
                {deps?.readiness_matrix && Object.entries(deps.readiness_matrix).map(([mId, item]) => {
                  const mInfo = models.find((m) => m.model_id === mId);
                  const displayName = mInfo?.display_name || (
                    mId === 'argos-translate' ? 'Argos Translate (CTranslate2 Pivot ar→en→ur)' :
                    mId === 'apple-native-translation' ? 'Apple Native Translation (ar → en Reference)' :
                    mId === 'madlad400-7b-mt' ? 'Google MADLAD-400 7B MT' :
                    mId === 'nllb-200-3.3b' ? 'Meta NLLB-200 3.3B Distilled' :
                    mId === 'qwen3:8b' ? 'Qwen3 8B Instruct' :
                    mId
                  );
                  const providerTag = mInfo?.provider_name?.toUpperCase() || (
                    mId === 'argos-translate' ? 'LOCAL_MT' :
                    mId === 'apple-native-translation' ? 'APPLE_LOCAL' :
                    'LOCAL'
                  );
                  return (
                    <div key={mId} className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs flex items-center justify-between">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100">{displayName}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold border ${
                            item.ready
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : 'bg-rose-950 text-rose-300 border-rose-800'
                          }`}>
                            {item.status}
                          </span>
                        </div>
                        <p className="text-slate-400 text-[11px]">
                          {item.ready ? '✓ All runtime dependencies verified.' : `❌ ${item.reason}`}
                        </p>
                      </div>

                      <span className="text-[10px] text-slate-500 font-mono">
                        {providerTag}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* STEP 4: LIVE ARABIC -> URDU TEST */}
          {step === 4 && (
            <div className="space-y-4">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                4. Live Arabic → Urdu Verification Test
              </h3>
              <p className="text-xs text-slate-300">
                Execute a single real translation test to verify that the connected model returns genuine Urdu text.
              </p>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <label className="text-xs text-slate-400 block mb-1">Select Engine to Test</label>
                    <select
                      value={testSelection}
                      onChange={(e) => {
                        const val = e.target.value;
                        setTestSelection(val);
                        const [p, m] = val.split('|');
                        setTestProvider(p);
                        setTestModelId(m);
                      }}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100"
                    >
                      <optgroup label="1. Offline Local Machine Translation (LOCAL_MT)">
                        <option value="argos|argos-translate">
                          Argos Translate (CTranslate2 Pivot ar→en→ur) — {providerStatus?.providers.argos?.is_available ? '✓ AVAILABLE' : 'NOT INSTALLED'}
                        </option>
                        <option value="transformers|nllb-200-distilled-1.3b">
                          Meta NLLB-200 1.3B ({deps?.readiness_matrix?.['nllb-200-distilled-1.3b']?.ready ? '✓ READY' : 'NOT INSTALLED'})
                        </option>
                        <option value="transformers|nllb-200-3.3b">
                          Meta NLLB-200 3.3B ({deps?.pytorch.installed ? '✓ INSTALLED' : 'PYTORCH MISSING'})
                        </option>
                        <option value="transformers|madlad400-7b-mt">
                          Google MADLAD-400 7B MT ({deps?.pytorch.installed ? '✓ INSTALLED' : 'PYTORCH MISSING'})
                        </option>
                      </optgroup>

                      <optgroup label="2. Apple Native Translation (APPLE_LOCAL)">
                        <option value="apple|apple-native-translation">
                          ✓ Apple Native Translation (On-Device ar→en Reference Bridge) — AVAILABLE
                        </option>
                      </optgroup>

                      <optgroup label="3. Public Web Translators (PUBLIC_WEB)">
                        <option value="public_web|google-web-unofficial">
                          ✓ Google Web Unofficial (Public Web) — AVAILABLE
                        </option>
                        <option value="public_web|lingva-public">
                          ✓ Lingva Translation (Public Web) — AVAILABLE
                        </option>
                        <option value="public_web|mymemory-public">
                          ✓ MyMemory Translation (Public Web) — AVAILABLE
                        </option>
                      </optgroup>

                      <optgroup label="4. Local AI & LLMs (LOCAL_AI)">
                        <option value="ollama|qwen3:8b">
                          Ollama Qwen3 8B ({deps?.ollama.running ? (deps.ollama.qwen3_installed ? '✓ READY' : 'PULL REQUIRED') : 'OLLAMA NOT RUNNING'})
                        </option>
                        <option value="lmstudio|qwen3-8b">
                          LM Studio Local Server ({providerStatus?.providers.lmstudio?.is_available ? '✓ CONNECTED' : 'DISCONNECTED'})
                        </option>
                      </optgroup>

                      <optgroup label="5. Google Gemini Cloud (CLOUD_AI)">
                        <option value="gemini|gemini-3.6-flash">
                          Google Gemini 3.6 Flash ({providerStatus?.providers.gemini?.is_available ? '✓ KEY CONFIGURED' : 'KEY NOT SET'})
                        </option>
                        <option value="gemini|gemini-3.6-pro">
                          Google Gemini 3.6 Pro ({providerStatus?.providers.gemini?.is_available ? '✓ KEY CONFIGURED' : 'KEY NOT SET'})
                        </option>
                      </optgroup>
                    </select>
                  </div>

                  <div className="w-48">
                    <label className="text-xs text-slate-400 block mb-1">Model Identifier</label>
                    <input
                      type="text"
                      value={testModelId}
                      onChange={(e) => setTestModelId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono"
                    />
                  </div>

                  <div className="pt-5">
                    <button
                      onClick={handleRunLiveTest}
                      disabled={testRunning}
                      className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs px-4 py-2 rounded-xl font-bold flex items-center gap-1.5 shadow-md"
                    >
                      {testRunning ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                      Test Model Now
                    </button>
                  </div>
                </div>

                {/* Sample phrase preview */}
                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-xs space-y-1">
                  <span className="text-slate-400">Test Input (Arabic):</span>
                  <p className="font-arabic-text text-base text-slate-100 font-bold">كيف حالك؟</p>
                </div>

                {/* Test Result Display */}
                {testResult && (
                  <div className={`p-4 rounded-xl border ${testResult.success ? 'bg-emerald-950/40 border-emerald-500/40' : 'bg-rose-950/40 border-rose-500/40'} space-y-2`}>
                    <div className="flex items-center gap-2">
                      {testResult.success ? (
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-rose-400" />
                      )}
                      <span className="font-bold text-sm text-white">
                        {testResult.success ? '✓ REAL MODEL VERIFIED' : 'Verification Failed'}
                      </span>
                    </div>

                    {testResult.success ? (
                      <div className="space-y-1 text-xs">
                        <p className="text-slate-300">
                          {testProvider === 'apple' ? 'Live English Reference Output (Apple Neural Engine):' : 'Live Urdu Translation Output:'}
                        </p>
                        <p className={`p-2.5 rounded-lg border border-slate-800 text-emerald-300 bg-slate-950 ${
                          testProvider === 'apple' ? 'font-sans text-sm font-semibold' : 'font-urdu-text text-lg'
                        }`}>
                          {testResult.output}
                        </p>
                        <div className="flex items-center gap-4 text-[11px] text-slate-400">
                          <span>Latency: {testResult.latency_ms} ms</span>
                          {testResult.route && <span>Route: {testResult.route}</span>}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-rose-300 font-mono">{testResult.error}</p>
                    )}
                  </div>
                )}

              </div>
            </div>
          )}

        </div>

        {/* Wizard Footer Nav */}
        <div className="bg-slate-950 px-6 py-4 border-t border-slate-800 flex items-center justify-between">
          <button
            onClick={() => setStep((s) => Math.max(1, s - 1) as any)}
            disabled={step === 1}
            className="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white bg-slate-800 disabled:opacity-30"
          >
            Back
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                fetchDependencies();
                onRefreshStatus();
              }}
              className="flex items-center gap-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Status
            </button>

            {step < 4 ? (
              <button
                onClick={() => setStep((s) => Math.min(4, s + 1) as any)}
                className="px-5 py-2 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors"
              >
                Next Step
              </button>
            ) : (
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors flex items-center gap-1.5"
              >
                <Check className="w-4 h-4" />
                Finish & Open Workstation
              </button>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
